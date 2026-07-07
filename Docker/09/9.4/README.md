## bind mount：開發模式的即改即生效

### 場景一：程式碼熱重載

沿用第 06 章的 webapp 專案，開發時不要每改一行就重建映像檔：

```bash
cd ~/webapp

# 把專案目錄 bind 進容器,配 uvicorn 的 --reload 熱重載
docker run -d --rm --name dev -p 8000:8000 \
  -v "$(pwd)":/app \
  webapp:dev

# 驗證第一版回應
curl -s http://localhost:8000/ 

# 直接在主機改程式碼:把訊息換掉
sed -i.bak 's/容器化成功/熱重載生效/' app.py

# 一兩秒後再打:不重建、不重啟,新程式碼已上線
sleep 2 && curl -s http://localhost:8000/
docker stop dev && mv app.py.bak app.py
```

- `-v "$(pwd)":/app`：來源含 `/`，走 bind mount 分流——主機目錄直接遮在容器的 /app 上（第 07 章 dev 目標映像檔裡 COPY 進去的程式碼被蓋住，改用你主機的即時版本）。
- webapp:dev 的 CMD 帶著 `--reload`（第 07 章三胞胎的設計），uvicorn 偵測檔案變動自動重載——「改檔、存檔、重整瀏覽器」的開發循環回來了，同時保有容器的環境一致性。
- 來源路徑必須是**絕對路徑**，所以用 `$(pwd)` 展開；相對路徑會被 `-v` 誤判成 volume 名稱，又是那個默默建新 volume 的坑。
- macOS 提醒（第 02 章差異速查的回收）：bind mount 跨越 VM 邊界，大量小檔案 I/O 明顯比 Ubuntu 慢；重 I/O 的資料（如資料庫）別用 bind，掛 volume 讓它留在 VM 內的原生檔案系統。

### 場景二：唯讀掛設定檔

```bash
# 準備一份自訂的 nginx 設定
mkdir -p ~/nginx-conf
cat > ~/nginx-conf/default.conf <<'EOF'
server {
    listen 80;
    location / { return 200 "由 bind mount 掛入的設定在服役\n"; }
}
EOF

# 以唯讀方式掛進容器:服務不該有能力改自己的設定
docker run -d --rm --name web -p 8080:80 \
  -v ~/nginx-conf/default.conf:/etc/nginx/conf.d/default.conf:ro \
  nginx:alpine

curl -s http://localhost:8080/
docker stop web
```

- bind mount 可以精準到**單一檔案**，不必整目錄搬進去。
- `:ro` 唯讀是設定檔掛載的標準姿勢：容器被入侵時，攻擊者連改設定檔持久化的機會都沒有。
- 地雷預告：bind 單一檔案時，主機端用「先刪再建」方式改檔（很多編輯器的原子存檔就是這樣）會讓容器內看到舊的 inode，改動不同步——整目錄掛載沒有這個問題，被咬過就知道要嘛掛目錄、要嘛重啟容器。

### 場景三：權限與擁有者——bind mount 的頭號客訴

非特權容器（第 06 章的 appuser）配 bind mount，九成會撞權限牆。現場重演與解法：

```bash
# 重演:主機目錄由你的使用者擁有,容器內的 appuser(UID 不同)寫入被拒
mkdir -p ~/bindperm && cd ~/bindperm
docker run --rm -v "$(pwd)":/work -w /work --user 1001:1001 alpine   sh -c 'echo 測試 > out.txt 2>&1 || echo "寫入被拒:UID 1001 對這個目錄沒有寫入權"'

# 解法一:啟動時把容器使用者對齊主機使用者的 UID/GID
docker run --rm -v "$(pwd)":/work -w /work --user $(id -u):$(id -g) alpine   sh -c 'echo 對齊後寫入成功 > out.txt && ls -l out.txt'

# 驗證:主機看到的檔案擁有者就是你自己,不是 root 也不是無名氏
ls -l out.txt && rm -f out.txt
```

權限說明：

- 病灶本質：**掛載不做任何身分轉換**——容器內行程的 UID 直接對到主機檔案系統的 UID。容器的 appuser 若是 UID 1001、主機目錄擁有者是 UID 1000，寫入自然被拒。
- `--user $(id -u):$(id -g)` 是開發機最通用的解法：容器行程以「你」的身分執行，讀寫 bind 目錄天經地義，產出的檔案也歸你——不會出現 root 擁有的檔案讓你主機上 rm 都要 sudo。
- 反向的經典慘案：以 root 跑的容器往 bind 目錄寫檔，主機上這些檔案的擁有者是 root，一般使用者刪不掉、CI 清理工作目錄直接失敗——這就是「為什麼 CI 產物目錄常常要 sudo 才清得掉」的謎底。
- 生產環境的正解仍是 volume：volume 的初始填充會連映像檔內容的擁有者資訊一起帶過去，權限問題比 bind 少一個數量級。