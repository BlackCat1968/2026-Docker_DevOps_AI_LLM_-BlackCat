# Scheduler：Pod 如何被排到節點上

kube-scheduler 是控制平面裡專門負責「決定一個還沒有落點的 Pod 該跑到哪個節點」的元件；它不親自啟動容器，只做決策，把選好的節點名寫回 Pod，剩下的交給那個節點的 kubelet。換句話說，Scheduler 像航空公司的座位分配系統：它不負責讓你上飛機（那是 kubelet 的事），它只根據「這個座位裝不裝得下你（過濾）」和「哪個座位對你最好（評分）」把你分配到某個位子，一旦劃位完成，登機門那邊自然會處理後續。

這一章玄貓帶你把排程決策「逼出來看」——看 Pod 為什麼排到 A 不排到 B、為什麼有時排不上去卡在 Pending、以及怎麼干預它的決定。**第 07 章時序圖裡那個「Scheduler 決定節點並綁定」的步驟，這一章拆給你看它腦袋裡在算什麼。**

---

## 排程器在做什麼

- **它監看「沒有落點的 Pod」**：也就是 `nodeName` 還是空的 Pod。
- **它為每個這種 Pod 選一個最合適的節點**，然後把節點名綁上去（設定 `nodeName`）。
- **綁定後它就不管了**：那個節點的 kubelet 監看到「有 Pod 指派給我」，才真的呼叫容器執行期把容器跑起來（第 07 章）。

---

## 兩階段決策：過濾與評分

排程器對每個待排的 Pod 走兩個階段：

- **過濾（filtering，舊稱 predicates）**：**硬條件**，是非題。這個節點「裝不裝得下、符不符合要求」——記憶體夠不夠、CPU 夠不夠、`nodeSelector` 標籤符不符、有沒有不能容忍的污點。不通過的節點直接淘汰。
- **評分（scoring，舊稱 priorities）**：**軟偏好**，打分數。在通過過濾的節點裡，哪個「比較好」——例如映像檔已經拉過的節點分數較高（啟動更快）、把同一個 Service 的副本分散到不同節點的**分散（spreading）**函式，降低單機故障拖垮整個服務的機率。

最後把分數加總，選最高分的節點。

```mermaid
flowchart LR
    A[待排程 Pod] --> B[過濾 filtering<br/>淘汰裝不下/不符合的節點]
    B --> C[評分 scoring<br/>對可行節點打分]
    C --> D[選最高分節點]
    D --> E[綁定 nodeName]
    E --> F[kubelet 執行]
```

---

## 繞過排程器：直接指定 `nodeName`

你可以在 Pod 上自己寫死 `nodeName`，**跳過整個排程流程**，直接指定節點。DaemonSet（第 18 章）就是靠這招把 Pod 塞到每個節點。但**一般情況別這樣做**——寫死節點會讓應用變脆（那台掛了就沒了）、叢集變沒效率。多數時候該信任排程器，就像你信任作業系統會幫你的程式找到 CPU 核心一樣。

---

## 動手實作

以下範例用 kind 多節點叢集，macOS 與 Ubuntu 皆可。先起叢集：

```bash
cat > sched.yaml <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
  - role: worker
  - role: worker
EOF
kind create cluster --name sched --config sched.yaml
```

---

### 範例一：觀察一次排程決策

先看排程器把 Pod 排到哪、以及它留下的決策足跡。

**Step 1**　建一個 Pod 並看它落在哪個節點：

```bash
kubectl run p1 --image=nginx

# -o wide 會多顯示 NODE 欄，看它被排到哪台
kubectl get pod p1 -o wide
```

**Step 2**　看排程器留下的事件：

```bash
# Events 裡的 Scheduled 就是排程器的決策紀錄
kubectl describe pod p1 | grep -A2 Events
```

**Step 3**　連建多個 Pod，觀察分佈：

```bash
for i in 1 2 3 4 5 6; do kubectl run spread-$i --image=nginx; done

# 看每個 Pod 落在哪個節點，觀察分佈是否平均
kubectl get pods -o wide --selector="run" 2>/dev/null | awk '{print $1, $7}' | sort -k2
```

**逐項詳解：**

- `-o wide`：多印 `NODE` 欄，讓你看到落點。
- `describe` 裡的 `Scheduled` 事件寫著「Successfully assigned default/p1 to sched-worker...」——**這就是 Scheduler 綁定節點的證據**。
- 多個 Pod 傾向被分散到不同節點，因為評分階段偏好平均分佈（配合負載與分散函式）。

---

### 範例二：用資源請求影響排程（把 Pod 逼進 Pending）

過濾階段最常見的硬條件就是資源。我們故意要求超過節點能給的量。

**Step 1**　看節點大約有多少可配置資源：

```bash
# 看每個節點的 CPU / 記憶體容量
kubectl describe nodes | grep -A5 "Allocatable" | head
```

**Step 2**　建一個索求「誇張記憶體」的 Pod：

```bash
cat > greedy.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: greedy
spec:
  containers:
    - name: box
      image: nginx
      resources:
        requests:
          memory: "900Gi"    # 故意要求遠超節點能給的記憶體
EOF
kubectl apply -f greedy.yaml
```

**Step 3**　它會卡在 Pending，看原因：

```bash
kubectl get pod greedy          # STATUS 是 Pending
kubectl describe pod greedy | grep -A3 Events
```

**逐項詳解：**

- `requests.memory: "900Gi"`：**請求（request）是排程器用來過濾節點的依據**——它會找「保證能撥出這麼多記憶體」的節點。沒有節點給得出 900Gi，全部節點在過濾階段被淘汰。
- 結果 Pod 卡 `Pending`，Events 出現 `FailedScheduling`，訊息類似「Insufficient memory」。
- **這是資源請求最重要的作用：它是排程決策的輸入，不是限制**（限制 limits 是另一回事，第 29 章專章）。


---

### 範例三：`nodeSelector` 把 Pod 釘到特定節點

用標籤把 Pod 限定只能排到某些節點。

**Step 1**　給一個節點貼標籤：

```bash
# 挑一個 worker 節點貼上自訂標籤
NODE=$(kubectl get nodes -o jsonpath='{.items[1].metadata.name}')
kubectl label node "$NODE" disktype=ssd
echo "已標記 $NODE"
```

**Step 2**　建一個要求 `disktype=ssd` 的 Pod：

```bash
cat > pinned.yaml <<'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: pinned
spec:
  nodeSelector:
    disktype: ssd          # 只排到帶此標籤的節點
  containers:
    - name: box
      image: nginx
EOF
kubectl apply -f pinned.yaml
```

**Step 3**　驗證它真的排到那台：

```bash
kubectl get pod pinned -o wide     # NODE 欄應為剛剛貼標籤的節點
```

**逐項詳解：**

- `kubectl label node`：給節點加標籤，是把節點分類（哪些有 SSD、哪些在特定機房）的標準做法。
- `nodeSelector: {disktype: ssd}`：**這是一個過濾階段的硬條件**——沒有這個標籤的節點全被淘汰，Pod 只可能排到帶標籤的那台。
- 若沒有任何節點符合，Pod 一樣會卡 Pending。


---

### 範例四：直接指定 `nodeName` 繞過排程器

證明你可以跳過排程器自己劃位。

**Step 1**　直接寫死 `nodeName`：

```bash
NODE=$(kubectl get nodes -o jsonpath='{.items[2].metadata.name}')

cat > direct.yaml <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: direct
spec:
  nodeName: $NODE           # 直接指定節點，跳過 scheduler
  containers:
    - name: box
      image: nginx
EOF
kubectl apply -f direct.yaml
```

**Step 2**　驗證它落在指定節點、且沒有走排程：

```bash
kubectl get pod direct -o wide

# 注意：這個 Pod 的 Events 裡不會有 Scheduler 的 Scheduled 記錄
kubectl describe pod direct | grep -A3 Events
```

**逐項詳解：**

- `nodeName: <節點>`：**Pod 一建立就已經有落點，排程器根本不會碰它**——kubelet 直接監看到「這個 Pod 指派給我」就啟動。
- 因此 Events 裡通常**看不到** `Scheduled`（那是排程器的動作），這反過來證明它繞過了排程。
- **DaemonSet 就是這樣把 Pod 塞到每個節點**（第 18 章）。但一般應用別這樣寫死——那台節點掛了 Pod 不會被自動搬走。

---

### 範例五：`cordon` 節點——標為不可排程，看 Pod 避開

維運時常要把某節點「封鎖」不再接新 Pod（例如準備維護）。

**Step 1**　封鎖一個節點：

```bash
NODE=$(kubectl get nodes -o jsonpath='{.items[1].metadata.name}')

# cordon 把節點標為 SchedulingDisabled，不再接受新 Pod
kubectl cordon "$NODE"
kubectl get nodes         # 那台會顯示 SchedulingDisabled
```

**Step 2**　建一批 Pod，觀察它們全都避開被封鎖的節點：

```bash
for i in 1 2 3 4; do kubectl run avoid-$i --image=nginx; done
sleep 3
kubectl get pods -o wide | grep avoid    # NODE 欄不會出現被 cordon 的節點
```

**Step 3**　解除封鎖：

```bash
# uncordon 讓節點恢復可排程
kubectl uncordon "$NODE"
kubectl get nodes
```

**逐項詳解：**

- `kubectl cordon`：把節點標為 `SchedulingDisabled`。**它是過濾階段的一個硬條件**——被 cordon 的節點在過濾時就被排除，新 Pod 不會排上去。
- 注意 `cordon` **只擋新 Pod，不會趕走已在上面跑的 Pod**；要連舊 Pod 一起搬走得用 `kubectl drain`（第 44 章維運會做）。
- `uncordon` 解除封鎖，恢復正常。


---

### 範例六：spreading——同服務多副本自然分散

驗證評分階段的分散函式：同一組工作負載的副本傾向散在不同節點。

**Step 1**　先解除所有封鎖，確保節點都可用：

```bash
kubectl uncordon --all 2>/dev/null || true
```

**Step 2**　建一個多副本 Deployment，看副本分佈：

```bash
kubectl create deployment spreadapp --image=nginx --replicas=6

sleep 5
# 統計每個節點上有幾個 spreadapp 的 Pod
kubectl get pods -l app=spreadapp -o wide | awk 'NR>1{print $7}' | sort | uniq -c
```

**Step 3**　清理整個實驗叢集：

```bash
kind delete cluster --name sched
```

**逐項詳解：**

- 你會看到 6 個副本大致平均散在多個 worker 節點上，而不是全擠在同一台。
- **這來自評分階段的分散偏好**：把同一組（同 Service / 同 workload）的 Pod 排到不同節點，可降低「單一節點故障就整組陣亡」的風險，是排程器內建的可靠性設計。
- 想強制更嚴格的分散規則（例如「每個可用區至多一個」），用第 30 章的拓撲分散限制（topology spread constraints）。