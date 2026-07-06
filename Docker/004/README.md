# 前景互動模式:進到容器裡拿一個 shell
docker run -it --name box1 alpine sh

# ↓↓ 容器內確認環境後離開 ↓↓
hostname
exit

# 背景服務模式:丟到後面跑,回傳容器 ID
docker run -d --name web1 nginx:alpine

# 用完即丟模式:結束自動清屍體,最適合一次性指令
docker run --rm alpine echo "跑完就消失"

# 綜合驗證:box1 已停止、web1 執行中、echo 那個已不存在
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'