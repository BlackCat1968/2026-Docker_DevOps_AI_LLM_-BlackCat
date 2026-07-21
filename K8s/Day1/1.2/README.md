### 三十秒體驗 Kubernetes 自癒

最後，讓真正的編排器上場。用 kind（Kubernetes in Docker）在本機起一個叢集，部署三副本，然後殺一個 Pod 看它自己補回來——對照範例三你手寫的那一坨。

**Step 1**　安裝 kind 與 kubectl。

Ubuntu：

```bash
# 安裝 kind
# x86_64
[ "$(uname -m)" = "x86_64" ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.32.0/kind-linux-amd64
# ARM64
[ "$(uname -m)" = "aarch64" ] && curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.32.0/kind-linux-arm64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

# 安裝 kubectl
# x86_64
[ "$(uname -m)" = "x86_64" ] && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
# ARM64
[ "$(uname -m)" = "aarch64" ] && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/kubectl
```

macOS：

```bash
# 用 Homebrew 一次裝好 kind 與 kubectl
brew install kind kubectl
```

**Step 2**　建立一個本機叢集：

```bash
# 建立名為 demo 的 Kubernetes 叢集（背後其實是用 Docker 容器當節點）
kind create cluster --name demo

# 確認叢集節點就緒
kubectl get nodes
```

**Step 3**　用一行指令部署三個副本：

```bash
# 建立一個 Deployment，跑 3 份 nginx
kubectl create deployment web --image=nginx --replicas=3

# 看三個 Pod 都起來了
kubectl get pods
```

**Step 4**　模擬故障：手動刪掉其中一個 Pod，然後立刻再看一次：

```bash
# 撈出第一個 Pod 名稱並刪掉它
POD=$(kubectl get pods -l app=web -o jsonpath='{.items[0].metadata.name}')
kubectl delete pod "$POD"

# 幾秒內再看，總數依然維持 3 個——它自己補了一個新的
kubectl get pods
```

**Step 5**　體驗完收掉叢集：

```bash
# 刪掉整個 demo 叢集
kind delete cluster --name demo
```

**逐項詳解：**

- `kind create cluster --name demo`：kind 用 Docker 容器模擬 Kubernetes 節點，在本機幾分鐘內生出一個能動的叢集，**不需要任何雲端帳號**，是本書前半段的主力實驗場（第 11 章會深入）。
- `kubectl get nodes`：`kubectl` 是你跟叢集溝通的命令列工具（第 12 章專章拆解），這裡確認節點狀態為 `Ready`。
- `kubectl create deployment web --image=nginx --replicas=3`：一行就宣告「我要 3 份 nginx」。**注意你只講了『要什麼結果』，沒講『怎麼達成』**——這正是宣告式的精神。
- `kubectl get pods`：Pod 是 Kubernetes 的最小部署單元（第 13 章），這裡你會看到三個 `web-...` 的 Pod。
- `kubectl delete pod "$POD"`：手動殺掉一個 Pod，等同範例三的 `docker kill`。差別是——**你什麼監督腳本都沒寫，Kubernetes 的控制器就自動幫你補回第三個**，而且這套控制器本身是高可用的，不會像你的土炮腳本一樣自己掛掉就全盤皆輸。
- `-l app=web`：用標籤（label）選出屬於這個 Deployment 的 Pod，標籤是 Kubernetes 組織資源的核心機制，後面章節會反覆用到。

跑完你會有很直接的體感：**範例三你寫了幾十行還漏洞百出的事，Kubernetes 用一行 `create deployment` 就內建做到，而且做得更穩。** 這就是為什麼雲端原生的世界需要容器編排。