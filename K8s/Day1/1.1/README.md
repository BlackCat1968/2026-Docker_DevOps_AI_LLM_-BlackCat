# 容器革命：為什麼雲端原生需要容器編排

容器編排（container orchestration）是一套自動化系統，負責在一群機器上決定「哪個容器該跑在哪台機器、跑幾份、掛了怎麼補、流量怎麼導」，讓你只需宣告「我要什麼結果」，而不必手動指揮每一個容器。換句話說，容器是一個個裝好貨的貨櫃，而編排系統就是整座港口的自動化調度中心——它盯著每一台起重機、每一艘船、每一個泊位，貨櫃掉了自己補、船滿了自己加，你只要在白板上寫下「這批貨要送到哪」，剩下的它包辦。

這一章玄貓要帶你先把「為什麼會有容器、為什麼容器還不夠、為什麼需要 Kubernetes」這條主線用手實際跑一遍。理論我講三句就好，剩下都讓你自己在終端機裡看到結果。

---

## 三種部署模型：從實體機到容器

應用程式的部署方式演化出三個世代，每一代都是為了解決上一代的痛：

- **傳統部署（實體機）**：應用程式直接跑在作業系統上，作業系統直接跑在硬體上。問題是一支吃資源的爛程式會把整台伺服器的記憶體與 CPU 吃光，餓死其他程式；要隔離就只能一台實體機跑一支應用，貴到爆。
- **虛擬化部署（VM）**：在一台實體機上用 hypervisor 切出多台虛擬機，每台虛擬機有自己的一份完整作業系統。隔離做到了，但每台 VM 都扛一份 OS，開機慢、映像檔肥、密度低。
- **容器化部署（Container）**：容器共用宿主機的作業系統核心，只把應用程式與它的相依性打包成映像檔。啟動快、映像檔小、一台機器塞得下的容器數量遠多於 VM。

**一句金句記起來：VM 是把整台電腦虛擬化，容器是把「行程」虛擬化。**

---

## 容器與虛擬機的分界線

差別不在「誰比較好」，而在「隔離的層級」不同：

- **隔離邊界**：VM 在硬體層隔離（各有一份 kernel）；容器在作業系統層隔離（共用同一份 kernel，用 Linux 的 namespace 與 cgroup 切開）。
- **啟動速度**：VM 要開機一份 OS，通常數十秒到分鐘級；容器只是啟動一個行程，通常毫秒到秒級。
- **映像檔大小**：VM 映像檔動輒數 GB；容器映像檔常在數十到數百 MB。
- **密度**：同一台機器上，容器能跑的數量通常是 VM 的數倍到數十倍。
- **代價**：容器共用 kernel，隔離強度天生比 VM 弱一階——**第 32 章談安全時，這個「共用 kernel」會變成攻擊面的關鍵**。

---

## 三場革命匯流成雲端原生

雲端原生（cloud native）不是單一技術，而是三場革命撞在一起的結果：

- **雲**：你不再「買一台電腦」，而是「買運算時間」。擴縮、維護、汰換都丟給雲端業者。
- **DevOps**：開發與維運不再是隔牆丟包的兩個部門，而是同一組人用自動化把「寫程式」到「上線營運」串成一條流水線。
- **容器**：把應用程式與環境一起封印，徹底解決「在我機器上明明會動」。

這三股力量匯流後，運算的未來就是「跑在雲上、容器化、分散式、由自動化動態管理」的系統。而**管理這個世界的作業系統，就叫 Kubernetes**。

---

## 為什麼一定要「編排」

容器解決了「打包」，但沒解決「大規模運行」。當你有幾十上百個容器散在十幾台機器上，你會立刻撞到這些問題，而這正是編排系統要自動化的職責：

- **排程（scheduling）**：這個容器該放到哪台還有空間的機器上？
- **自癒（self-healing）**：容器掛了、機器當了，誰負責把它在別處重開？
- **擴縮（scaling）**：流量高峰自動多開幾份，離峰自動收掉？
- **服務發現與負載平衡**：一份服務有五個副本，別人要怎麼找到它、流量怎麼平均分？
- **滾動更新與回滾**：換新版時怎麼不中斷服務、出包怎麼一鍵退回？

**手動做這些事就是災難的開始；Kubernetes 存在的理由，就是把上面每一條都變成「你宣告結果、它自動達成」。**

---

## 環境準備：macOS 與 Ubuntu 雙平台

後面所有範例都在 macOS 與 Ubuntu 上跑。先把 Docker 裝好。

**Ubuntu（安裝 Docker Engine）：**

```bash
# 更新套件索引並安裝相依性
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# 加入 Docker 官方 GPG 金鑰
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# 加入 Docker apt 來源
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安裝 Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# 把自己加進 docker 群組，免 sudo（要重新登入才生效）
sudo usermod -aG docker $USER
newgrp docker
```

**macOS（安裝 Docker Desktop）：**

```bash
# 用 Homebrew 安裝 Docker Desktop
brew install --cask docker

# 安裝後要手動開啟一次 Docker.app 讓背景服務啟動
open -a Docker
```

**兩平台共同驗證：**

```bash
docker version
docker run --rm hello-world
```

看到 `Hello from Docker!` 就代表引擎正常。