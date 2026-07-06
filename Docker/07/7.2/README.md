1. `FROM ... AS builder`：第一階段取名 builder，這個名字是後面 `COPY --from` 的門牌。
2. builder 裡放心裝 gcc——它是廠房，怎麼髒都不會進箱子。
3. `python -m venv /opt/venv`：把所有套件裝進一個**自包含的目錄**。venv 在這裡不是為了隔離開發環境，而是為了「打包成一個可以整坨搬走的資料夾」——過橋只搬 /opt/venv 一個路徑，乾淨俐落。
4. `ENV PATH="/opt/venv/bin:$PATH"`：讓 pip 與 python 都用 venv 裡的版本，兩個階段都要設，因為 ENV 不會跨階段繼承。
5. 第二個 FROM 開出全新的乾淨基底：**前一階段的任何東西都不會自動帶過來**，包含層、ENV、安裝的套件，全部歸零重來。
6. `COPY --from=builder /opt/venv /opt/venv`：整章的靈魂。從廠房精準吊運成品過橋，gcc、apt 快取、原始碼編譯的中間產物全數留在對岸等著被丟棄。
7. 之後就是第 06 章的標準收尾：非特權使用者、--chown、exec form。