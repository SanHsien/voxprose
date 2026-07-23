# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）Review

- **日期**：2026-07-23
- **Review 對象**：`main` 分支、release ZIP 修補 commit `a9ac6de`、正式發佈 `v3.4.1`（tag commit `db1bea9`）
- **方法**：重新 fetch 並核對基線、全樹差異覆核、Python 3.14.6 執行 `python -m pytest tests/ -q`（**403 passed, 10 skipped**）、GitHub 五版本 CI、Release workflow、正式資產 SHA-256、ZIP 中央目錄 filename/UTF-8 flag、兩包全檔 CRC、Windows `Expand-Archive` round-trip與正式 Lite runtime imports。真人語音、真 API key 與前景情境 LLM 端到端仍依 `docs/RELEASE_VERIFICATION.md` 標為 `BLOCKED`／待驗證，未用自動化結果代替。

---

## 總評

**健康分數：8.5 / 10（v3.4.0 事故覆核時為 8.2，修正版發佈後 +0.3）。**

v3.4.0 的功能程式與測試基線整體穩定，但「Release workflow 成功」曾被過早等同「使用者可用」。正式 Lite 資產在 Windows `Expand-Archive` 直接失敗；中央目錄確認 7 個中文檔名已在英文 runner 壓縮時變成 literal `?`，包含 4 個情境模板。該資產仍保留為事故證據，不覆寫舊 tag。

v3.4.1 已改用 .NET `ZipArchive` UTF-8 entry names，並新增上傳前 validator。GitHub runner 的兩包均通過 gate；重新下載後，Lite SHA-256 `5ed67c8c…aeade`、NoModel `f9d37058…bb94a` 與 sidecar／GitHub digest 一致，兩包全檔 CRC 與中文資源檢查通過，正式 Lite 也完成 Windows 解壓及 runtime imports。Silero/RMS 真人音訊、真雲端 API、前景視窗實際套用 LLM prompt 與系統匣目視仍未完成，不得轉為 ✅。

---

## 問題總帳

> 狀態標記：✅ 已修｜⏳ 待修｜🚫 決定不做｜🔍 需實機驗證。編號延續舊版風險排序表 1-12，13 起為 CHANGELOG/DECISIONS 記載的後續發現，24-1～24-3 與 25-1～25-4 為 2026-07-20～22 review 輪次陸續發現的問題（原第 4/5 節，已併入本表）。squash 後 commit hash 多數已不在目前 `git log` 可達範圍，一律優先引用 CHANGELOG/DECISIONS 章節。

| # | 問題 | 嚴重度 | 狀態 | 備註 |
|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*` | 高（打包鏈斷裂） | ✅ 已修（`04d82cc`） | 全檔搜尋已無殘留 |
| 2 | STT 引擎選單「Gemini」無對應分派分支 | 中高 | ✅ 已修（`71f0cbe`） | `stt/__init__.py` 已有分支，測試通過 |
| 3 | 無 Whisper 幻覺過濾機制 | 中高 | ✅ 已修（`7bf8592`） | `stt/hallucination_filter.py` 接線；實機驗證「嗯」被過濾、完整句不被過濾 |
| 4 | API Key 明碼且會同步到雲端資料夾 | 高 | ✅ 已修（`cc1e2d1`） | `LOCAL_KEYS` 已收錄 `*_api_key` |
| 5 | 無 `test_*.py`，核心 pipeline 零測試覆蓋 | 中高 | ✅ 已修（`f8633de` 起） | `tests/` 現有 32 個 `test_*.py`，403 passed, 10 skipped（Python 3.14.6，2026-07-23 本輪） |
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
| 26-4 | `keystrike.log`：`separate_keystrike_log` 設定開關是死碼（無程式碼讀取），檔案永遠是空 touch 占位 | 低 | ✅ 已修（2026-07-23） | 原判定 🚫 決定不做（隱私審查確認無疑慮，見 `docs/DECISIONS.md` 2026-07-23 一）；主人 2026-07-23 明示改為指示清除，已移除 `paths.KEYSTRIKE_LOG_PATH`／`touch()` 佔位、`config.py` 的 `separate_keystrike_log` 開關、UI 勾選框與「檢視熱鍵紀錄」按鈕、`utils/diagnostics.py` 收集項；全 repo grep `keystrike` 程式碼零殘留，僅留文件歷史紀錄 |
| 26-5 | `.github/workflows/ci.yml` 只測 Python 3.12，未涵蓋 `pyproject.toml` 宣告的 3.10/3.11 | 低 | ✅ 已修（2026-07-23） | 改 `strategy.matrix` 涵蓋 3.10/3.11/3.12；新增 `tests/test_ci_workflow.py` |
| 27-1 | 新增 Silero VAD 全時模式引擎（`audio/vad/`，`vad_engine="silero"`，見 `docs/REFERENCES.md` 調研條目） | — | 🔍 需實機驗證 | 介面抽象＋RMS 行為位元級不變＋真模型／合成音訊測試均通過；本輪修正版 Lite runtime 已確認內含 onnxruntime 1.27.0，UI 實際列出 RMS／Silero 且 Silero 顯示「✅ 可用」。麥克風 Logi C615 可開串流但取樣峰值 `0.000`；**未驗證**：真人說話、咳嗽／呼吸／雜音對照、真 STT 貼字。 |
| 27-2 | 新增前景視窗感知的情境模板自動切換（`utils/foreground.py`＋`auto_scenario_enabled`/`auto_scenario_rules`，見 `docs/REFERENCES.md` Wispr Flow 調研條目） | — | 🔍 需實機驗證 | 純 ctypes 與規則測試通過；本輪負向操作在未切換視窗時如預期抓到設定頁 `pythonw.exe`。Computer Use 單次 click 阻塞完整倒數，無法在 3 秒內另送合規切窗 action，因此「切到記事本後是否抓對」仍是 `BLOCKED`，不能把負向結果誤列產品 FAIL；真 API/LLM 情境命中與 fallback 同樣未驗證。 |
| 28-1 | v3.4.0 Windows Release ZIP 的 7 個中文檔名在英文 runner 被 `tar.exe` 轉成 literal `?`，導致 `Expand-Archive` 失敗且情境模板缺失 | 高（正式產物不可正常解壓） | ✅ 已修並以 v3.4.1 重發（`a9ac6de`，2026-07-23） | 改 .NET `ZipArchive` UTF-8；新增 `tools/verify_release_zip.py`、10 項回歸測試與 workflow 上傳前 gate。正式 v3.4.1 Lite／NoModel 的 SHA、CRC、UTF-8 資源均實證通過，Lite 完成 Windows 解壓與 runtime imports；既有 v3.4.0 資產保留為壞包事故紀錄。 |
| 28-2 | `_sync_preload_models()` 把非同步 subprocess warmup 當成同步完成，worker 尚未 ready 就設 `_models_ready=True` 並顯示設定 UI | 中（啟動狀態與真實 readiness 不一致） | ⏳ 待修 | `ui/app.py:185-187` 呼叫後立即設 ready；`SubprocessWhisperSTT.warmup()` 明寫「不阻塞等待」。實機 log 20:46:59 已記 `All models ready`，worker 到 20:47:42 才 `Model loaded`／`Warmup done`，與 AGENTS/註解宣稱的阻塞式預載不符。 |
| 28-3 | Computer Use/UIA 操作封裝 UI 時，app 兩度以 Windows fatal exception `0x8001010d` 消失 | 中（需重現歸因） | 🔍 真人環境重驗 | `main_crash.log` 兩次都停在 `ui/app.py:173 app_inst.exec()`，無正常 shutdown；可能是 UIA/COM 輸入同步互動誘發，現有證據不足以歸咎一般使用者操作或 STT warmup。需不用 UI 自動化的真人點擊重驗。 |

**統計**：已修/已驗證 36 項、待修 1 項（28-2）、決定不做 0 項、需實機驗證 3 項（27-1／27-2／28-3）。

---

## 未驗證邊界（誠實聲明）

- **真人語音音量**：麥克風裝置列舉/開串流/讀樣本機制層已驗證無例外，但 agent 無法對著實體麥克風真的發聲，未證明「收到有意義音量的真人語音」這一步。
- **真 API key 雲端引擎**：Groq／Gemini／OpenRouter／Claude／OpenAI／Qwen／DeepSeek 七個 provider 仍只有 mock 測試覆蓋，未用真實 API key 打過一次真實請求。
- **系統匣圖示的像素級辨識**：`TrayManager` 建構無例外，但受限測試機工作列圖示過多，未能用截圖肉眼百分之百指認對應圖示。
- **v3.4.0 正式資產**：Lite／NoModel ZIP 仍是失敗產物，請改用已驗證的 v3.4.1；舊 tag 不覆寫。
- **UIA crash 歸因**：自動化操作可重現兩次 `0x8001010d`，但需真人、不掛 UI Automation 的環境確認是否為一般產品路徑。

---

## 下一步建議

1. 修正或重新設計 subprocess worker readiness：只在 worker 回報 ready 且 warmup 完成後更新 `_models_ready`，並補啟動時序測試。
2. 在有真實 API key 與真人麥克風、且不掛 UI Automation 的環境完成 crash、Silero/RMS、基本貼字與前景情境端到端驗證。
3. 系統匣圖示做一次人工目視確認（低優先，機制層已驗證正確）。

---

## 維護慣例

- **REVIEW.md 採 latest-only**：只放最新一次覆核於根目錄，不逐版累積歷史。
- **修 bug 必回註本檔問題總帳的狀態欄**：規則見 [`AGENTS.md`](AGENTS.md)「開發約定」，適用所有 AI agent。
- **修復回註優先引用 `CHANGELOG.md`/`docs/DECISIONS.md` 的章節與日期**，不依賴 commit hash（squash 後會失效）。

---

*本 review 為對 release ZIP 修補 `a9ac6de` 與正式 v3.4.1 發佈的覆核；`python -m pytest tests/ -q` 已實跑（403 passed, 10 skipped），五版本 CI 與正式資產重下載驗證通過。既有 GitHub v3.4.0 資產仍不得視為通過。*
