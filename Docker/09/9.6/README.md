## 容器間共享：同一箱資料多人用

### 正規做法：同一個 volume 掛多個容器

```bash
# 生產者:每秒往共享 volume 寫一行記錄
docker volume create shared
docker run -d --rm --name producer -v shared:/out alpine \
  sh -c 'i=0; while true; do i=$((i+1)); echo "第 $i 筆" >> /out/feed.log; sleep 1; done'

# 消費者:唯讀掛同一箱,即時跟讀
docker run -d --rm --name consumer -v shared:/in:ro alpine \
  sh -c 'tail -f /in/feed.log'

# 觀察消費者的輸出:生產者寫的內容即時流過來
sleep 3 && docker logs --tail 3 consumer
docker stop producer consumer
```

- 一箱多掛是共享的正規解：生產者可寫、消費者 `:ro` 唯讀，權責分明。
- 典型應用：應用容器寫日誌、旁邊的收集容器唯讀撈走（第 20 章日誌管線的雛形）；Web 容器產靜態檔、nginx 容器唯讀供應。
- 同時寫入的併發控制是應用層的責任——兩個容器同時寫同一個檔案，volume 不會幫你排隊，設計時就要避開（各寫各檔、或單一寫入者）。