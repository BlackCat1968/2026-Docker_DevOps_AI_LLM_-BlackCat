## volume 的備份、還原與搬家

volume 沒有內建備份指令，業界標準手法是「借一個工具容器打 tar」：

```bash
# 備份:同時掛「要備份的 volume(唯讀)」與「主機的備份目錄(bind)」
mkdir -p ~/backups
docker run --rm \
  -v pgdata:/source:ro \
  -v ~/backups:/backup \
  alpine tar -czf /backup/pgdata-$(date +%Y%m%d).tar.gz -C /source .

ls -lh ~/backups/

# 還原:反向操作,把 tar 攤回一個(通常是全新的)volume
docker volume create pgdata-restore
docker run --rm \
  -v pgdata-restore:/target \
  -v ~/backups:/backup:ro \
  alpine sh -c 'tar -xzf /backup/pgdata-*.tar.gz -C /target && ls /target | head -5'
```

手法逐項說明：

- 工具容器的雙掛載是精髓：資料箱唯讀掛 /source、目的地 bind 掛 /backup，alpine 裡的 tar 當搬運工，用完即走、主機不裝任何東西——第 08 章借 httpd 跑 htpasswd 是同一招。
- `-C /source .`：進到來源目錄再打包「目前目錄的內容」，攤開時路徑乾淨、不會多包一層目錄。
- 資料庫類 volume 的備份紀律：**先停寫再備份**（stop 容器或用資料庫自己的備份指令如 pg_dump），對運行中的資料檔打 tar 可能拿到不一致的快照。
- 跨主機搬家 = 備份 tar → scp 到對面 → 還原進新 volume，三步完成；要常態共享則改掛網路儲存驅動：

```bash
# local 驅動掛 NFS 的寫法(示意:IP 與匯出路徑換成你環境的)
docker volume create --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.64.20,rw,nfsvers=4 \
  --opt device=:/exports/appdata \
  nfs-appdata
```

- 建出來的 volume 用法與本機 volume 完全相同，資料實體在 NFS 伺服器上——多台主機掛同一箱的常態方案，也是第 23 章 Swarm 跨節點資料的伏筆。