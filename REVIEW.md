# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）Review

- **日期**：2026-07-22
- **Review 對象**：`main` 分支 @ `a5c1898`（v3.3.0）
- **方法**：全樹靜態讀碼＋`python -m pytest tests/ -q` 實跑（**296 passed, 11 skipped**）＋前輪完整實機驗證（乾淨 venv 安裝、`self_check.py`／`diagnose_mic.py`／合成語音端到端 STT／`python main.py` 啟動／SettingsWindow 七分頁）＋**本輪新增**：真實 CUDA 加速驗證、可攜包建置與啟動實測，證據見 `scratchpad/cuda-and-package-verification-report.md`。

---

## 總評

**健康分數：8.7 / 10（原 8.3，+0.4）。**

前一版把分數定在 8.3，理由是「全部功能沒人真的跑過」這個最大缺口已解決，但仍有 5 項較窄的未驗證邊界（CUDA 實際加速、release 包實際安裝、真人語音、真 API key、系統匣圖示辨識）。本輪填掉其中兩項，且結果乾淨：裝 `requirements-cuda-win.txt` 後 `probe_cuda()` 回報 `accel_available=True`，STT worker 真的印出 `Model loaded successfully on cuda.`，同段音訊在 medium 模型上 GPU 0.55s vs CPU 8.57s（約 15.6 倍）；`release_win.ps1 -Lite` 端到端建置成功（616MB，launcher 現場編譯過），`opencc` 等依賴確認進 `.runtime`，用打包產物實際啟動無崩潰。兩項此前都只停在「機制正確但沒人跑過」，現在都有真實數據佐證。

未驗證邊界縮小為 3 項（真人對麥克風語音、雲端引擎真 API key、系統匣圖示像素辨識），範圍比先前更窄且性質不同（多數需要人類操作或真實金鑰，非 agent 能單方面驗證）。8.7 分反映「兩個具體、可驗證的未知數已解決」，不到 9 分是因為剩餘 3 項仍是誠實缺口，不該視為已解決。

---

## 問題總帳

> 狀態標記：✅ 已修｜⏳ 待修｜🚫 決定不做｜🔍 需實機驗證。編號延續舊版風險排序表 1-12，13 起為 CHANGELOG/DECISIONS 記載的後續發現，24-1～24-3 與 25-1～25-4 為 2026-07-20～22 review 輪次陸續發現的問題（原第 4/5 節，已併入本表）。squash 後 commit hash 多數已不在目前 `git log` 可達範圍，一律優先引用 CHANGELOG/DECISIONS 章節。

| # | 問題 | 嚴重度 | 狀態 | 備註 |
|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*` | 高（打包鏈斷裂） | ✅ 已修（`04d82cc`） | 全檔搜尋已無殘留 |
| 2 | STT 引擎選單「Gemini」無對應分派分支 | 中高 | ✅ 已修（`71f0cbe`） | `stt/__init__.py` 已有分支，測試通過 |
| 3 | 無 Whisper 幻覺過濾機制 | 中高 | ✅ 已修（`7bf8592`） | `stt/hallucination_filter.py` 接線；實機驗證「嗯」被過濾、完整句不被過濾 |
| 4 | API Key 明碼且會同步到雲端資料夾 | 高 | ✅ 已修（`cc1e2d1`） | `LOCAL_KEYS` 已收錄 `*_api_key` |
| 5 | 無 `test_*.py`，核心 pipeline 零測試覆蓋 | 中高 | ✅ 已修（`f8633de` 起） | `tests/` 現 20 檔，296 passed, 11 skipped |
| 6 | `paths.py` 雲端同步路徑常數是死碼 | 中 | ✅ 已修 | 四個常數已移除 |
| 7 | `ui/settings_window.py` god file | 中 | ✅ 已修（`1252a68`） | 拆為 7 分頁 mixin；實機驗證（含真 sounddevice）全數通過 |
| 8 | `requirements-win.txt` 無版本上限 | 中低 | ✅ 已修（`266280d`） | 實機驗證乾淨 venv 89 秒安裝成功、零衝突 |
| 9 | `diagnose_mic.py` Windows 上是死殼 | 低 | ✅ 已修（`0ee2730`） | 實機驗證列出 19 組真實裝置成功 |
| 10 | PTT／VAD 缺乏互斥檢查 | 低中 | ✅ 已修（`e33d479`） | `audio/mutex.py` 存在，測試通過 |
| 11 | `eval()` 用於語音計算機指令 | 低 | ✅ 已修（`3d2c215`） | 改 `ast.parse` 白名單解析 |
| 12 | 硬編碼 macOS 字型 `Monaco` | 低 | ✅ 已修（`2e52f87`） | 改 `QFont("Consolas", ...)` |
| 13 | OpenRouter STT 引擎自始壞掉 | 中高 | ✅ 已修（`75952fd`） | 測試通過 |
| 14 | Claude LLM 引擎自始壞掉（欄位名不一致） | 中高 | ✅ 已修（`9192ef6`） | AST 靜態掃描防回歸 |
| 15 | 網路請求逾時缺口 | 中 | ✅ 已修（`eb61819`） | `net_config.CLOUD_REQUEST_TIMEOUT_SECONDS` |
| 16 | STT 語言 hint 被翻譯目標語言污染 | 高 | ✅ 已修（`d99a326`） | `stt/language.py` 接線，測試通過 |
| 17 | 智慧詞彙學習對本地辨識無效 | 中高 | ✅ 已修（`aee3973`） | worker 已讀 IPC `prompt` 欄位，測試通過 |
| 18 | LLM system prompt 分散硬編 | 中 | ✅ 已修（`19017c8`） | `llm/prompts.py` 集中化 |
| 19 | LLM 未啟用時輸出無贅詞清理 | 中 | ✅ 已修（`da93f62`） | `utils/soul_rules.py` 已接線 |
| 20 | `soul/scenario/default.md` 贅詞清單缺項 | 低 | ✅ 已修（`1e53549`） | — |
| 21 | 無崩潰/環境診斷匯出管道 | 中 | ✅ 已修（`7bc3b0f`） | `utils/diagnostics.py` 存在；一個既有測試斷言脆弱性見 25-4 |
| 22 | `vocab/manager.py` 常數命名撞名 | 低 | ✅ 已修（`27d93c8`） | 已改名 `_VOCAB_DATA_DIR` |
| 23 | `requirements-win.txt` 多餘 `pystray` 依賴 | 低 | ✅ 已修（`aa1e220`） | 死分支併入 24-2 一併清理 |
| 24-1 | squash 後 commit hash 多數已不在 `git log` 可達範圍 | 中（文件治理） | ✅ 已處理（`4278ff8`） | `CHANGELOG.md`/`docs/DECISIONS.md` 已補免責聲明，僅作文件識別碼保留 |
| 24-2 | `ui/menu_bar.py` 殘留 pystray 死分支 | 低 | ✅ 已修（`aa1e220`） | 兩處不可達/自我短路分支已清 |
| 24-3 | 極短口語詞（「嗯」）落入幻覺過濾黑名單 | 低中 | ✅ 已驗證 | 直接函式呼叫確認過濾邏輯正確；完整句音訊往返驗證通過；單獨「嗯」因 TTS 音色限制未能重現，非程式缺陷 |
| 25-1 | 啟動/自檢日誌 `BUILD_ID`／`VERSION_NAME` 疊字重複 | 低 | ✅ 已修（`fe25423`） | 移除多餘疊加輸出 |
| 25-2 | 設定視窗署名鏈框架錯誤且不完整 | 中 | ✅ 已修（`e8b0f91`） | 補齊四層署名（原創／上游 Win 版／本 fork／協助） |
| 25-3 | CUDA Dashboard 文案與 worker 實際降級行為矛盾 | 中偏高 | ✅ 已修（`e8b0f91`） | 抽出 `stt/cuda_check.py` 共用真相源；**本輪**已在裝有 `requirements-cuda-win.txt` 的機器上驗證加速確實生效（GPU 0.55s vs CPU 8.57s） |
| 25-4 | `test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗 | 低 | ✅ 已修（`49c29ae`） | `git stash` 確認為既有缺陷，與改動無關 |
| 26-1 | 全 repo 43 處 broad except 靜默吞噬，涵蓋設定檔/記憶/統計損毀無痕跡、LLM prompt 三處注入失敗靜默、`build_vocab_prompt()` 失敗靜默退回預設 prompt（與 17 號同一類歷史風險） | 中 | ✅ 已修（2026-07-23） | 只補 log／收窄型別，不改 fallback 行為；詳見 `docs/DECISIONS.md` 2026-07-23 條目與分類統計表 |
| 26-2 | `utils/permissions.py:ensure_all_permissions()` 被 `ui/app.py` import 卻從未被呼叫（死碼），`check_microphone()` 永遠回傳 `True` | 低中 | ✅ 已修（2026-07-23） | 改讀 Windows 隱私權登錄檔，並在 `ui/app.py.__init__()` 實際呼叫；新增 `tests/test_permissions.py` |
| 26-3 | `debug.log`／`worker_debug.log` 無大小上限，長期執行無限增長 | 低中 | ✅ 已修（2026-07-23） | 新增 `utils/log_rotation.py`（5MB×2 備份）；`keystrike.log` 因目前無任何 handler 寫入暫不適用，見 26-4 |
| 26-4 | `keystrike.log`：`separate_keystrike_log` 設定開關是死碼（無程式碼讀取），檔案永遠是空 touch 占位 | 低 | 🚫 決定不做 | 隱私審查確認無疑慮（見 `docs/DECISIONS.md` 2026-07-23 一）；死碼留給未來真的要做「熱鍵事件獨立記錄」時一併處理，本次不擴大範圍 |
| 26-5 | `.github/workflows/ci.yml` 只測 Python 3.12，未涵蓋 `pyproject.toml` 宣告的 3.10/3.11 | 低 | ✅ 已修（2026-07-23） | 改 `strategy.matrix` 涵蓋 3.10/3.11/3.12；新增 `tests/test_ci_workflow.py` |

**統計**：已修/已驗證 34 項、待修 0 項、決定不做 1 項（26-4；歷史「不吸收」項目屬功能吸收分析範圍，見 `docs/mac-mainline-absorption-analysis.md`）。

---

## 未驗證邊界（誠實聲明）

- **真人語音音量**：麥克風裝置列舉/開串流/讀樣本機制層已驗證無例外，但 agent 無法對著實體麥克風真的發聲，未證明「收到有意義音量的真人語音」這一步。
- **真 API key 雲端引擎**：Groq／Gemini／OpenRouter／Claude／OpenAI／Qwen／DeepSeek 七個 provider 仍只有 mock 測試覆蓋，未用真實 API key 打過一次真實請求。
- **系統匣圖示的像素級辨識**：`TrayManager` 建構無例外，但受限測試機工作列圖示過多，未能用截圖肉眼百分之百指認對應圖示。

---

## 下一步建議

1. 在有真實各雲端 API key 的環境跑一次端到端整合測試（七個 provider 從未被真實請求驗證過）。
2. 補一次真人對麥克風說話的錄音驗證（需要人類操作，非 agent 可完成）。
3. 系統匣圖示做一次人工目視確認（低優先，機制層已驗證正確）。

---

## 維護慣例

- **REVIEW.md 採 latest-only**：只放最新一次覆核於根目錄，不逐版累積歷史。
- **修 bug 必回註本檔問題總帳的狀態欄**：規則見 [`AGENTS.md`](AGENTS.md)「開發約定」，適用所有 AI agent。
- **修復回註優先引用 `CHANGELOG.md`/`docs/DECISIONS.md` 的章節與日期**，不依賴 commit hash（squash 後會失效）。

---

*本 review 為對 `main` 分支（`a5c1898`，v3.3.0）的 review，`python -m pytest tests/ -q` 已實跑（296 passed, 11 skipped）。工作樹本身未做任何修改，僅新增/改寫本檔案（`REVIEW.md`）。*
