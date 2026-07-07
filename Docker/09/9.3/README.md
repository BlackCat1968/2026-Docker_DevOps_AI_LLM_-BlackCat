## 真實戰場：資料庫容器的資料保衛戰

用 PostgreSQL 走一遍「容器升級、資料不動」的完整劇本——這是 volume 最重要的生產劇目：

```bash
# 開一台 PostgreSQL 16,資料掛進具名 volume
docker run -d --name db --restart=unless-stopped \
  -e POSTGRES_PASSWORD=devpass \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

# 等它就緒後寫入一筆業務資料
sleep 5
docker exec db psql -U postgres -c \
  "CREATE TABLE orders(id serial, item text); INSERT INTO orders(item) VALUES ('玄貓的訂單');"

# 模擬升級:把整個容器砍掉,換 16 系列較新映像檔重開,掛同一個 volume
docker rm -f db
docker run -d --name db --restart=unless-stopped \
  -e POSTGRES_PASSWORD=devpass \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16

# 驗證:容器換了一整代,訂單一筆不少
sleep 5
docker exec db psql -U postgres -c "SELECT * FROM orders;"
```

劇本逐項說明：

- `/var/lib/postgresql/data` 是 PostgreSQL 映像檔宣告的資料目錄（映像檔文件會寫明，多數資料庫映像檔都有對應路徑），資料掛在這裡，容器就徹底變成「可拋棄的執行外殼」。
- 升級流程就是「砍容器、換映像檔、掛同一個 volume」三步——第 04 章說過容器該是隨時可重建的，資料外掛之後這句話才真正成立。
- 跨大版本升級（16 → 17）另有資料格式遷移程序，屬資料庫自身的守備範圍；容器層面的功課就是本節這一套。
- 補一刀反面教材：如果當初忘了掛 volume，`docker rm -f db` 的瞬間，所有訂單隨可寫層蒸發——第 04 章 diff 照妖鏡照出來的病，這裡就是死因。