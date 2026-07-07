## tmpfs：不落地的記憶體掛載

```bash
# 掛一塊 64MB 的 tmpfs 到 /scratch
docker run --rm \
  --tmpfs /scratch:rw,size=64m,mode=1777 \
  alpine sh -c 'df -h /scratch && dd if=/dev/zero of=/scratch/blob bs=1M count=10 status=none && ls -lh /scratch'
```

- `--tmpfs 路徑:選項`：size 限制上限（不設就能吃到主機記憶體的一半，務必要設）、mode 是目錄權限。
- 寫進 tmpfs 的資料只存在記憶體：容器一停止全數蒸發、主機磁碟從頭到尾沒有留下位元組——處理暫時性機密（解密後的憑證快取、session 檔）的正解。
- 限制兩條：tmpfs 只能單容器獨享（不能像 volume 掛給多容器）、Linux 限定（macOS 的容器跑在 VM 裡所以照常可用，Windows 容器不支援）。