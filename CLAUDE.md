# CLAUDE.md

Claude Code 在本專案工作時的指引。**專案定位、硬性邊界、架構速覽、開發約定與驗證方向的唯一真相源是 [`AGENTS.md`](AGENTS.md)**——先讀它，本檔只補 Claude 專屬要點，不重複規則。

## 回覆要求

- 使用繁體中文，先講結論（改了什麼、驗證了什麼），細節後補。
- 不要把簡單任務寫成冗長架構分析。
- **完成必附驗證證據**：程式邏輯改動附 `python -m pytest tests/ -v` 或對應 `test_*.py` 的實際輸出；UI/熱鍵/錄音等行為改動，若無法在當前環境跑 Windows 實機測試，需明確說明未驗證範圍，不得聲稱「應該可以」。

## 高風險改動額外小心

- 動到 `main.py` 開頭的環境變數設定（`KMP_DUPLICATE_LIB_OK`、`MKL_THREADING_LAYER`、`TQDM_DISABLE` 等）或 `stt/__init__.py` 的 `get_stt()` 平台分流時，先重讀 `windows_cuda_qt_crash_postmortem.md`——PyQt6 與 CUDA 同行程載入順序錯誤會導致無訊息崩潰（Exit Code 1），且不會有例外訊息可供除錯。
- 動到 `setup_win.bat` / `build_win.py` / `release_win.ps1` / `voicetype_installer.iss` 打包鏈前，先確認任務是否明確要求；否則保持原樣。

## 文件同步

新增／改動功能後，同步對應文件（各主題單一真相源）：使用者說明 [`README.md`](README.md) / [`README.en.md`](README.en.md)、最新覆核 [`REVIEW.md`](REVIEW.md)、精簡對外變更摘要 [`CHANGELOG.md`](CHANGELOG.md)、逐版詳細紀錄 [`VERSIONS.md`](VERSIONS.md)、決策理由 [`docs/DECISIONS.md`](docs/DECISIONS.md)、開發環境與測試 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)、授權查證 [`NOTICE.md`](NOTICE.md)、AI agent 快速索引 [`SKILL.md`](SKILL.md)。

**修 bug 必回註 REVIEW.md**：規則本文見 [`AGENTS.md`](AGENTS.md)「開發約定」（適用所有 AI agent，非 Claude 專屬）。
