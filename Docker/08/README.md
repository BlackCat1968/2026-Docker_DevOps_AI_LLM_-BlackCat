## 8.3 自架私有 Registry：十秒開一間自己的物流中心

公司內網、離線環境、不想付訂閱費——自架 registry 全部有解，而且它本身就是一個容器：

### 步驟一：開站

```bash
# 用官方 registry 映像檔開一間,資料掛 volume 確保重啟不蒸發
docker run -d --name registry --restart=unless-stopped \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \
  registry:3

# 確認物流中心開門營業
curl -s http://localhost:5000/v2/ && echo "registry API 回應正常"
```

- `registry:3` 是 CNCF Distribution 專案的官方實作，整個 Docker Hub 的核心引擎開源版。
- `-v registry-data:/var/lib/registry`：映像檔資料落在具名 volume，容器重建資料還在——volume 的完整戲份在第 09 章，這裡先體驗它保命的價值。
- `--restart=unless-stopped`：第 04 章的重啟策略學以致用，物流中心不能主機一重開就消失。
- `/v2/` 是 distribution-spec 的版本檢查端點，回 200 就代表 API 活著。

**Tips and Tricks（秘訣）**

> registry:2 自己也是一個容器，記得幫它掛 volume 存放資料，否則容器一刪，倉庫裡所有映像檔陪葬。

### 步驟二：推貨與提貨

```bash
# 貼上私有物流中心的門牌(主機:連接埠/儲存庫:標籤)
docker tag webapp:slim localhost:5000/webapp:1.0.0

# 推貨:不需要 login,本機 localhost 預設放行
docker push localhost:5000/webapp:1.0.0

# 用 API 盤點貨架:有哪些儲存庫、每個儲存庫有哪些標籤
curl -s http://localhost:5000/v2/_catalog | python3 -m json.tool
curl -s http://localhost:5000/v2/webapp/tags/list | python3 -m json.tool

# 提貨演練:刪掉本機的再拉回來
docker rmi localhost:5000/webapp:1.0.0
docker pull localhost:5000/webapp:1.0.0
```

- 映像檔名的第一段有冒號或點（`localhost:5000`、`registry.mycorp.com`）時，Docker 就把它當 Registry 位址而不是 Docker Hub 帳號——命名解剖（第 05 章）的規則在此發威。
- `_catalog` 與 `tags/list` 是 distribution-spec 的標準盤點端點，寫腳本盤點自家貨架就靠這兩條。

**Tips and Tricks（秘訣）**

> 推自架 registry 前必須先 docker tag 成 <registry位址>/<映像名> 的完整名稱。沒有位址前綴的推送一律會跑去 Docker Hub，這是最常見的推錯地方事故。

### 步驟三：讓其他機器也能來提貨

其他主機來連時就不是 localhost 了，而 Docker 預設**拒絕走 HTTP 的遠端 registry**。實驗環境的放行法（正式環境請看步驟四）：

```bash
# 在「要來提貨的那台機器」的 daemon.json 加入白名單(IP 換成 registry 主機的)
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" },
  "live-restore": true,
  "insecure-registries": ["192.168.64.10:5000"]
}
EOF

sudo systemctl restart docker

# 驗證白名單生效
docker info --format '{{.RegistryConfig.IndexConfigs}}' 2>/dev/null; docker info | grep -A2 "Insecure Registries"
```

- `insecure-registries` 的語意是「允許對這個位址走無加密 HTTP」——名字就在警告你了，**只准用在隔離的實驗網段**。
- 這是「每台要存取的機器」都要設的白名單，不是 registry 端的設定，方向別搞反。

**Tips and Tricks（秘訣）**

> 其他機器連不上自架 registry 時，先用 curl http://<位址>/v2/ 測連通性，再檢查 insecure-registries 設定。分清楚是網路問題還是信任問題，除錯就快一半。

### 步驟四：正式環境的兩道門——TLS 與帳密

```bash
# 準備憑證與帳密目錄
mkdir -p ~/registry/{certs,auth} && cd ~/registry

# 產生自簽憑證(正式環境改用內部 CA 或 Let's Encrypt 簽發)
openssl req -newkey rsa:4096 -nodes -sha256 \
  -keyout certs/registry.key -x509 -days 365 -out certs/registry.crt \
  -subj "/CN=registry.mycorp.com" \
  -addext "subjectAltName=DNS:registry.mycorp.com"

# 產生帳密檔(bcrypt 格式,借 httpd 映像檔的 htpasswd 工具,不必在主機裝 apache)
docker run --rm httpd:2.4 htpasswd -Bbn deployer 'S3cretPass' > auth/htpasswd

# 重開一間有鎖的物流中心
docker rm -f registry
docker run -d --name registry --restart=unless-stopped \
  -p 443:5000 \
  -v registry-data:/var/lib/registry \
  -v $(pwd)/certs:/certs:ro \
  -v $(pwd)/auth:/auth:ro \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/registry.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/registry.key \
  -e REGISTRY_AUTH=htpasswd \
  -e REGISTRY_AUTH_HTPASSWD_REALM="Registry Realm" \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd \
  registry:3

# 之後的存取流程:先登入,再照常推拉
docker login registry.mycorp.com -u deployer
```

兩道門逐項說明：

- 自簽憑證的 `subjectAltName` 必填——現代的憑證驗證只認 SAN，只寫 CN 會被拒收。用自簽憑證的機器要把 `registry.crt` 放到 `/etc/docker/certs.d/registry.mycorp.com/ca.crt` 讓 daemon 信任。
- `htpasswd -Bbn`：`-B` 用 bcrypt 雜湊（registry 只認這種）、`-n` 輸出到標準輸出。借 httpd 容器跑工具這招，本身就是容器的日常用法——工具用完即走，主機零污染。
- registry 的所有設定都能用 `REGISTRY_` 開頭的環境變數覆寫，對應它設定檔的巢狀結構，容器化部署最順手的設定方式。
- 掛 certs 與 auth 用 `:ro` 唯讀——registry 沒有任何理由改動憑證與帳密檔，最小權限從掛載做起。

**Tips and Tricks（秘訣）**

> insecure-registries 只該出現在隔離的實驗環境。任何有多人使用或跨網段存取的 registry，TLS 與帳密是底線，不是加分題。

### 步驟五：下架與磁碟回收——完整走一遍

Tips 提過的「只進不出」問題，直接實作解法：

```bash
# 重開一間允許刪除的物流中心
docker rm -f registry
docker run -d --name registry --restart=unless-stopped   -p 5000:5000   -v registry-data:/var/lib/registry   -e REGISTRY_STORAGE_DELETE_ENABLED=true   registry:3

# 推一個待下架的犧牲品
docker tag alpine localhost:5000/victim:1.0 && docker push localhost:5000/victim:1.0

# 下架三步之一:先取得 manifest 的 digest(注意 Accept 標頭是必要的)
DIGEST=$(curl -sI -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json"   http://localhost:5000/v2/victim/manifests/1.0 | grep -i docker-content-digest | tr -d '
' | awk '{print $2}')
echo "待下架: $DIGEST"

# 下架三步之二:用 DELETE 方法刪除 manifest(標籤隨之消失)
curl -s -X DELETE http://localhost:5000/v2/victim/manifests/$DIGEST -w "HTTP %{http_code}
"

# 下架三步之三:垃圾回收,把無人引用的 blob 真正從磁碟清掉
docker exec registry registry garbage-collect /etc/distribution/config.yml 2>/dev/null | tail -3 || docker exec registry registry garbage-collect /etc/docker/registry/config.yml | tail -3
```

下架流程逐項說明：

- 取 digest 那條的 `Accept` 標頭不能省：不聲明接受的 manifest 格式，registry 回的 digest 可能對不上實際儲存的版本，DELETE 會 404——這是本節最經典的地雷。
- DELETE 打的是 digest 不是標籤：distribution-spec 的刪除單位是 manifest，回 202 代表下架受理。
- garbage-collect 要在 registry 容器裡執行、吃它的設定檔（registry:3 的路徑在 /etc/distribution/，舊版在 /etc/docker/registry/，指令做了雙路徑容錯）；生產環境建議在離峰時段跑，並考慮先暫停推貨避免競態。
- 回收後可以再 push 同一個映像檔驗證倉庫功能一切正常——下架的是貨，不是貨架。

**Tips and Tricks（秘訣）**

> 自架 registry 記得排磁碟監控。它的貨只進不出（刪標籤預設不回收 blob），要開 `REGISTRY_STORAGE_DELETE_ENABLED=true` 並定期在容器裡跑 `registry garbage-collect` 才會真正釋放空間。

---

## 8.4 pull-through 快取：幫 Docker Hub 開一間在地分店

幾十台主機天天跟 Docker Hub 拉同樣的基底映像檔，既慢又容易撞速率限制。registry 可以開成「代理快取」模式：

```bash
# 開一間 Docker Hub 的在地分店(唯讀快取,聽 5001)
docker run -d --name hub-mirror --restart=unless-stopped \
  -p 5001:5000 \
  -v mirror-data:/var/lib/registry \
  -e REGISTRY_PROXY_REMOTEURL=https://registry-1.docker.io \
  registry:3

# 每台主機的 daemon.json 加上 registry-mirrors,拉貨先問分店
sudo python3 - <<'EOF'
import json
path = "/etc/docker/daemon.json"
cfg = json.load(open(path))
cfg["registry-mirrors"] = ["http://localhost:5001"]
json.dump(cfg, open(path, "w"), indent=2, ensure_ascii=False)
EOF
sudo systemctl restart docker

# 實測:先清掉本機的 alpine,拉兩次比速度
docker rmi alpine 2>/dev/null; time docker pull alpine
docker rmi alpine; time docker pull alpine
```

- `REGISTRY_PROXY_REMOTEURL`：分店背後的總店位址。第一次有人來提貨，分店去總店調貨並留一份；之後同樣的貨直接出，內網速度、零速率限制消耗。
- `registry-mirrors` 是 daemon 層級的設定：所有「沒寫明 registry 的拉取」（也就是 Docker Hub 的貨）自動先問分店。改 daemon.json 用了一小段 Python 做 JSON 合併——比 sed 硬改 JSON 安全，設定檔弄壞 daemon 起不來（第 02 章的教訓）。
- 兩次計時的差距就是分店的價值：第一次走總店（蓄水），第二次直接內網出貨。
- 分店是唯讀的——你自家的映像檔照樣推去 8.3 節那間正店，一間管快取、一間管出貨，分工明確。

分店的三個維運要點，開站前先知道：

- **快取有壽命**：代理模式預設會定期淘汰久未使用的快取項目，冷門映像檔可能要重新回總店調貨，屬正常現象不是故障。
- **登入資訊可下放**：分店可以配置 Docker Hub 的帳號憑證（REGISTRY_PROXY_USERNAME／PASSWORD），讓整個內網共享一份付費帳號的速率額度，各主機不必人人登入。
- **分店掛了要能降級**：registry-mirrors 拉不到時 daemon 會自動退回直連總店，所以分店故障不會斷炊，只是變慢——這個內建韌性讓分店可以大膽上線。

---

## 8.5 簽章：從 Content Trust 到 Cosign

### 先交代歷史：DCT 為什麼進了博物館

DCA 教材花了一整章講 Docker Content Trust（`DOCKER_CONTENT_TRUST=1` 配 Notary v1）。玄貓必須直說：**這套已經被業界淘汰**——Notary v1 停止發展、Docker Hub 之外的支援稀落、金鑰管理體驗糟糕。它的歷史地位保留在附錄 A，考古用；實務上的現役標準是 CNCF 的 **Cosign**（Sigstore 專案），Kubernetes 生態全面採用。

**Tips and Tricks（秘訣）**

> 看到教學文章還在教 docker trust 或 Notary v1 就可以直接關掉了——內容已經過時。判斷教材新舊，「簽章用什麼工具」是很好的試金石。

### 步驟一：安裝 Cosign

```bash
# Ubuntu:抓官方發行的 deb 安裝
LATEST=$(curl -s https://api.github.com/repos/sigstore/cosign/releases/latest | grep tag_name | cut -d '"' -f4)
curl -fsSL "https://github.com/sigstore/cosign/releases/download/${LATEST}/cosign_${LATEST#v}_amd64.deb" -o /tmp/cosign.deb
sudo apt install -y /tmp/cosign.deb

# macOS
brew install cosign

# 驗證安裝
cosign version | head -2
```

**Tips and Tricks（秘訣）**

> Cosign 是單一靜態執行檔，CI 環境裡直接下載二進位檔比裝套件管理器更快，也方便鎖定版本確保管線可重現。

### 步驟二：產生金鑰對並簽章

```bash
# 產生金鑰對:會要你設一組保護私鑰的密語(cosign.key 私鑰 / cosign.pub 公鑰)
cd ~/webapp && cosign generate-key-pair

# 簽章必須簽 digest 而不是 tag(tag 會漂移,封條要蓋在不可變的指紋上)
DIGEST=$(docker inspect localhost:5000/webapp:1.0.0 --format '{{index .RepoDigests 0}}')
echo "簽章標的: $DIGEST"

# 蓋封條:簽章本身也會存進 registry,跟映像檔放在一起
cosign sign --key cosign.key $DIGEST
```

- `generate-key-pair` 的私鑰密語等於封條印章的保險箱密碼——私鑰外洩，任何人都能冒你的名出貨，保管等級比照生產密碼。
- **簽 digest 是鐵律**：tag 是便利貼、隨時會被重貼，封條蓋在便利貼上毫無意義。`RepoDigests` 就是 push 時抄下來的那枚指紋。
- 簽章以 OCI 產物的形式存放在 registry 裡、緊鄰映像檔——提貨的人不需要另一套基礎設施就能驗封條。

**Tips and Tricks（秘訣）**

> 私鑰的密語（passphrase）在 CI 裡透過 COSIGN_PASSWORD 環境變數提供，記得放進 secrets 管理而不是寫死在管線設定檔，簽章的安全性取決於私鑰的保管。

### 步驟三：驗章——部署前的守門動作

```bash
# 驗章:公鑰對得上、內容沒被動過才放行
cosign verify --key cosign.pub $DIGEST | python3 -m json.tool | head -12

# 反面實驗:拿一個沒簽過的映像檔驗,必定失敗
docker tag alpine localhost:5000/unsigned:1.0 && docker push localhost:5000/unsigned:1.0
UNSIGNED=$(docker inspect localhost:5000/unsigned:1.0 --format '{{index .RepoDigests 0}}')
cosign verify --key cosign.pub $UNSIGNED 2>&1 | tail -2
```

- verify 成功時輸出一份 JSON：簽章對應的 digest、簽署者資訊——這份輸出就是部署腳本的放行依據，驗不過就中止部署，第 16 章會把它做成 CI 閘門、第 19 章談完整供應鏈。
- 反面實驗必做：守門員要先確認「壞人真的進不來」，no matching signatures 這行錯誤訊息就是門有鎖上的證據。
- Cosign 另有免金鑰模式（keyless，走 OIDC 身分與透明日誌），CI 環境很流行，第 19 章再展開；自管金鑰模式是理解簽章本質的最佳起點。

**Tips and Tricks（秘訣）**

> 驗章要指定「摘要」而不是「標籤」才有完整意義——標籤可以被移動，摘要不行。部署腳本裡固定使用 @sha256: 形式引用映像檔是進階但值得的紀律。

### 補充半步：keyless 模式一瞥

免金鑰模式先給個最小體感（完整戰法在第 19 章）：

```bash
# keyless 簽章:不用自管私鑰,以 OIDC 身分(瀏覽器登入)換取短效憑證簽署
COSIGN_YES=true cosign sign $DIGEST

# keyless 驗章:驗的是「誰(哪個身分)簽的」,而不是「哪把鑰匙簽的」
cosign verify   --certificate-identity-regexp '.*@mycorp\.com'   --certificate-oidc-issuer https://accounts.google.com   $DIGEST | head -5
```

- 簽署時會開瀏覽器走一次 OIDC 登入，Sigstore 簽發一張綁定你身分的短效憑證完成簽章，簽署事件同步寫入公開透明日誌（Rekor）——私鑰保管這個千古難題直接被繞開。
- 驗章條件從「公鑰」變成「身分規則」：上例只放行 mycorp.com 網域的簽署者。CI 環境更漂亮——以 CI 平台的工作身分簽章，驗章規則鎖定「只信我們家流水線簽的貨」。
- 自管金鑰與 keyless 不衝突：離線環境用前者、雲端 CI 用後者，本章你兩把都摸過了。

**Tips and Tricks（秘訣）**

> keyless 模式免管私鑰但依賴 OIDC 身分與透明日誌（Rekor），適合開源專案。企業內網若不能連外部服務，還是乖乖用金鑰對模式。

### 封條放在哪？親眼看一次

簽章「存進 registry、緊鄰映像檔」不是修辭，用兩條指令看見它：

```bash
# cosign 的關聯產物總覽:映像檔底下掛了哪些簽章與附件
cosign tree $DIGEST

# 貨架盤點:簽章以特殊標籤(sha256-<digest>.sig)的形式住在同一個儲存庫
curl -s http://localhost:5000/v2/webapp/tags/list | python3 -m json.tool
```

- `cosign tree` 畫出映像檔與其簽章、附件的樹狀關係——之後第 19 章掛上 SBOM（軟體物料清單）與建置證明（attestation）時，全都會長在這棵樹上，Cosign 是整串供應鏈證據的掛勾。
- tags/list 裡多出的 `sha256-....sig` 標籤就是簽章本體：它就是一個小小的 OCI 產物，跟著映像檔同進同退——搬 registry、做離線交付，簽章一起打包，驗章能力不落地。
- 換金鑰或撤簽的管理動作：`cosign clean $DIGEST` 可移除簽章附件；金鑰輪替則是新私鑰重簽、部署端換新公鑰驗，舊簽章自然失效。

**Tips and Tricks（秘訣）**

> 簽章流程要長在 CI 裡而不是工程師手上——「建置 → 推貨 → 簽章」三連發自動執行，私鑰放 CI 的祕密管理，人手永遠碰不到私鑰，才是可長可久的做法。

### 收官檢核：出貨能力盤點

離開本章前逐項自測：

- 說出「名字決定路由」的四條規則，秒判一個 denied 的成因。
- 用權杖與 --password-stdin 完成登入，說出憑證落在哪個檔案。
- 對 Docker Hub 與私有 registry 各完成一次推、拉、隔空驗貨。
- 開出一間帶 TLS 與帳密的 registry，並讓另一台機器信任自簽憑證後成功提貨。
- 走完「取 digest → DELETE → garbage-collect」的下架回收全流程。
- 架好 pull-through 分店並用兩次計時證明其效益。
- 用 Cosign 完成產鑰、簽 digest、驗章、看 cosign tree 四連發，並說出簽 tag 為什麼無效。