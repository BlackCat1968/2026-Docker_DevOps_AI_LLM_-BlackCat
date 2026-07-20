```
# 一:清單。自訂欄位輸出,只看重點
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# 二:日誌。-f 跟隨、--tail 只看尾巴、-t 附時間戳記
docker logs -f --tail 20 -t web2

# 三:即時資源儀表板(CPU、記憶體、網路、I/O)
docker stats --no-stream

# 四:容器內行程清單(不用進容器就能看)
docker top web2

# 五:完整身家調查,搭配 --format 精準取值
docker inspect web2 --format '狀態: {{.State.Status}} | IP: {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'

# 加碼:比對容器檔案系統與映像檔的差異(A 新增/C 修改/D 刪除)
docker diff web2 | head -10
```
