## 清理與治理：volume 的斷捨離

```bash
# 盤點:哪些 volume 沒有任何容器在用(懸空)
docker volume ls --filter dangling=true

# 全域磁碟帳本:volume 那一列的 RECLAIMABLE 就是可回收量
docker system df

# 只清懸空 volume(比 image prune 更要小心:volume 裝的是資料!)
docker volume prune -f

# 刪容器順手刪它的匿名 volume
docker run -d --name anon -v /data alpine sleep 300
docker rm -f -v anon

# 指名刪除單一 volume(有容器掛著會被擋下)
docker volume rm appdata webroot shared pgdata-restore 2>/dev/null; docker volume ls
```

- `-v /data` 沒給名字就是**匿名 volume**：一串亂數當名字，容器刪掉後變成無主孤魂——懸空 volume 的最大來源。`docker rm -v` 的 `-v` 就是「連匿名 volume 一起收屍」。
- `volume prune` 與 image prune 的風險等級完全不同：映像檔刪了可以重拉，**volume 刪了資料就是沒了**。生產主機跑 prune 前先盤點清單，最好搭配 `--filter label=` 只清打過「可拋棄」標籤的。
- 治理建議：volume 一律具名並貼 label（`docker volume create --label team=backend --label ttl=short cache1`），第 04 章的標籤治理擴張到儲存層，清理腳本才有安全的篩選依據。

各 volume 到底佔多少空間，兩條指令量出來：

```bash
# 全域帳本的詳細版:每個 volume 的大小與被幾個容器引用
docker system df -v | sed -n '/VOLUME NAME/,/^$/p' | head -8

# 精準量測單一 volume:又是借工具容器的老招
docker run --rm -v pgdata:/x:ro alpine du -sh /x
```

- `system df -v` 的 LINKS 欄位是引用計數：0 就是懸空候選人，但記得懸空不等於可刪——夜間批次用的箱子白天看起來也是 0。
- 借 alpine 跑 du 的手法適用任何 volume，磁碟告警時逐箱點名找肥貓，比瞎猜快得多。

### 收官檢核：資料掌控力盤點

離開本章前逐項自測：

- 說出三種掛載的定位與選擇口訣，各給一個實例。
- 完成三代同堂實驗，解釋 volume 生命週期與容器脫鉤的意義。
- 說出初始填充的觸發條件，以及 volume 與 bind 在此的相反行為。
- 走完資料庫「砍容器換版保資料」劇本與反面教材。
- 建好 bind mount 熱重載開發環境，並排除一次 UID 權限問題。
- 用工具容器完成一輪備份與還原，說出停寫的理由。
- 分辨匿名與具名 volume，示範 rm -v 與逐箱開箱找資料。
- 說明 --volumes-from 為何降級、正規共享怎麼做。