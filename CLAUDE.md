# CLAUDE.md

Claude Code 在本 repo 工作時先讀 [`AGENTS.md`](AGENTS.md)。**專案定位、硬性邊界、驗證、文件責任與 REVIEW 規則都以 AGENTS.md 為準**；本檔只補 Claude 專屬提醒。

## 回覆與驗證

- 使用繁體中文，先講改了什麼、驗證了什麼，再補細節。
- 簡單任務不要擴寫成架構論文。
- 程式邏輯改動至少附對應 pytest 結果；UI、熱鍵、錄音、CUDA、STT 或焦點貼字若沒有 Windows 實機證據，要明確標記未驗證範圍。

## 高風險區

- 修改 `main.py`、`stt/__init__.py` 或 STT 啟動順序前，先讀 `docs/DEVELOPMENT.md` 的 Windows 已知地雷；不要把本機 Whisper 改回與 PyQt6 同行程載入。
- `setup_win.bat`、`build_win.py`、`release_win.ps1`、`voicetype_installer.iss` 等打包鏈，除非任務明確涉及安裝／發行，否則保持原樣。

## 文件同步

只更新與本次變更直接相關的單一真相源：

- 使用者行為：`README.md` / `README.en.md`
- 版本內容：`CHANGELOG.md`
- 長期設計理由：`docs/DECISIONS.md`
- 開發／測試／打包：`docs/DEVELOPMENT.md`
- 來源署名：`NOTICE.md`
- 上游同步：`docs/UPSTREAM.md`
- Review 風險狀態：`REVIEW.md`（僅依 AGENTS.md 規定的兩種情況更新）

不要為單純文件修改或一般 bug 額外製造 REVIEW／DECISION／postmortem 紀錄。
