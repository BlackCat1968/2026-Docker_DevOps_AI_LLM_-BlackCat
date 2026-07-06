# 環境變數:-e 單發、--env-file 整批
echo "APP_ENV=production
DB_HOST=db.internal" > app.env
docker run --rm -e DEBUG=1 --env-file app.env alpine env | grep -E "DEBUG|APP_ENV|DB_HOST"

# 標籤:給容器貼分類貼紙,之後用過濾器批次操作
docker run -d --name svc-a -l team=backend -l env=dev nginx:alpine
docker run -d --name svc-b -l team=backend -l env=prod nginx:alpine

# 用標籤過濾:只列 backend 團隊的 dev 環境容器
docker ps --filter label=team=backend --filter label=env=dev --format '{{.Names}}'

# 批次停止某標籤的所有容器(過濾器 + -q 只吐 ID,再餵給 stop)
docker stop $(docker ps -q --filter label=team=backend)

# 清理三連:磁碟盤點 → 刪除所有停止的容器 → 驗收
docker system df
docker container prune -f
docker system df