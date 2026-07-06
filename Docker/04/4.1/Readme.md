# 開一個每秒報數的容器
docker run -d --name counter alpine sh -c 'i=0; while true; do i=$((i+1)); echo "第 $i 秒"; sleep 1; done'

# 跟著日誌看它報數,幾秒後 Ctrl-C 離開(logs 的 Ctrl-C 只離開觀看,不影響容器)
docker logs -f counter

# 冷凍:行程被 freezer 凍在原地
docker pause counter

# 冷凍期間日誌完全靜止,狀態顯示 Paused
docker ps --format 'table {{.Names}}	{{.Status}}'

# 解凍:從凍住的那一秒繼續數,不會從頭來過
docker unpause counter
docker logs --tail 5 counter
docker rm -f counter