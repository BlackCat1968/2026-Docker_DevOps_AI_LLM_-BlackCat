## 玄貓考考你

**Q1：`docker run -d --rm` 的容器結束後，還能用 `docker logs` 驗屍嗎？為什麼？** 

**Q2：stop 與 kill 的差異？結束碼 143 與 137 各代表什麼？** 

**Q3：為什麼有些容器 stop 一定要等滿 10 秒？兩種解法是什麼？** 

**Q4：exec 與 attach 進容器的本質差異？為什麼 attach 裡按 Ctrl-C 很危險？** 

**Q5：always 與 unless-stopped 差在哪個情境？生產環境選哪個？** 

**Q6：`--memory=200m` 但沒設 `--memory-swap`，容器實際能用多少「記憶體加 swap」？會有什麼症狀？** 

**Q7：docker update 能對執行中容器調整哪類設定？哪類不行？** 

**Q8：pause 與 stop 都讓服務停擺，本質差異是什麼？各適合什麼場合？** 

**Q9：`docker diff` 輸出一大串 A 與 C，對維運的警訊是什麼？** 