# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）Review

- **日期**：2026-07-23
- **Review 對象**：`main` 分支、正式發佈 `v3.4.3`（tag commit `d672a02`）
- **方法**：重新 fetch 並核對基線、全樹差異覆核、Python 3.14.6 執行 `python -m pytest tests/ -q`（**423 passed, 10 skipped**）、GitHub Python 3.10–3.14 五版本 CI、Release workflow、兩個正式資產重新下載與 SHA-256、ZIP 中央目錄 filename/UTF-8 flag、全檔 CRC、Windows `Expand-Archive` round-trip，以及由正式 Lite 解壓目錄與包內 Python 執行的 Settings／About callback、原生 widget 截圖與 `QSystemTrayIcon` live object 驗證。真人有效音量、真 API key 與前景情境 LLM 端到端仍依 `docs/RELEASE_VERIFICATION.md` 標為 `BLOCKED`／待驗證，未用自動化結果代替。

---

## 總評

**健康分數：8.7 / 10（v3.4.0 事故覆核時為 8.2；修正版發佈與 readiness 修復後 +0.5）。**

v3.4.0 的功能程式與測試基線整體穩定，但「Release workflow 成功」曾被過早等同「使用者可用」。正式 Lite 資產在 Windows `Expand-Archive` 直接失敗；中央目錄確認 7 個中文檔名已在英文 runner 壓縮時變成 literal `?`，包含 4 個情境模板。該資產仍保留為事故證據，不覆寫舊 tag。

v3.4.1 已修正 ZIP 中文檔名，v3.4.2 再補上 STT readiness 契約與 fail-closed 驗證流程；v3.4.3 修正遺漏啟動 tray、選單 callback 與視窗喚回問題，並更新品牌圖示與 About 版面。v3.4.3 GitHub runner 兩包均通過 gate；重新下載後，Lite SHA-256 `d7b7616b…28d78c`、NoModel `953bf9a8…14f5de` 與 sidecar／GitHub digest 一致，兩包全檔 CRC 與中文資源檢查通過。正式 Lite 另完成 Windows 解壓，包內 Settings 1200×840、About 680×720 均 visible／非 minimized，原生截圖無裁切重疊；tray live object 為 `visible=True`、tooltip「聲成文」、icon 非空。麥克風取樣仍為 `0.000`；Silero/RMS 真人音訊、真雲端 API、前景視窗實際套用 LLM prompt 與系統匣像素級目視仍未完成，不得轉為 ✅。

---

## 問題總帳

> 狀態標記：✅ 已修｜⏳ 待修｜🚫 決定不做｜🔍 需實機驗證。編號延續舊版風險排序表 1-12，13 起為 CHANGELOG/DECISIONS 記載的後續發現，24-1～24-3 與 25-1～25-4 為 2026-07-20～22 review 輪次陸續發現的問題（原第 4/5 節，已併入本表）。squash 後 commit hash 多數已不在目前 `git log` 可達範圍，一律優先引用 CHANGELOG/DECISIONS 章節。

| # | 問題 | 嚴重度 | 狀態 | 備註 |
|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*` | 高（打包鏈斷裂） | ✅ 已修（`04d82cc`） | 全檔搜尋已無殘留 |
| 2 | STT 引擎選單「Gemini」無對應分派分支 | 中高 | ✅ 已修（`71f0cbe`） | `stt/__init__.py` 已有分支，測試通過 |
| 3 | 無 Whisper 幻覺過濾機制 | 中高 | ✅ 已修（`7bf8592`） | `stt/hallucination_filter.py` 接線；實機驗證「嗯」被過濾、完整句不被過濾 |
| 4 | API Key 明碼且會同步到雲端資料夾 | 高 | ✅ 已修（`cc1e2d1`） | `LOCAL_KEYS` 已收錄 `*_api_key` |
| 5 | 無 `test_*.py`，核心 pipeline 零測試覆蓋 | 中高 | ✅ 已修（`f8633de` 起） | `tests/` 現有 36 個 `test_*.py`，423 passed, 10 skipped（Python 3.14.6，2026-07-23 本輪） |
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
| 27-1 | 新增 Silero VAD 全時模式引擎（`audio/vad/`，`vad_engine="silero"`，見 `docs/REFERENCES.md` 調研條目） | — | 🔍 需實機驗證 | 介面抽象＋RMS 行為位元級不變＋真模型／合成音訊測試均通過；本輪修正版 Lite runtime 已確認內含 onnxruntime 1.27.0，UI 實際列出 RMS／Silero 且顯示「✅ 可用」。麥克風 Logi C615 可開串流但取樣峰值 `0.000`。已新增真人驗證器（`6961d66`，2026-07-24）：四種聲音各只錄一次、同一 PCM 公平比較兩引擎，反查 release module 來源並輸出 JSON／Markdown；**仍未執行**真人說話、咳嗽／呼吸／雜音及真 STT 貼字，故維持 🔍。 |
| 27-2 | 新增前景視窗感知的情境模板自動切換（`utils/foreground.py`＋`auto_scenario_enabled`/`auto_scenario_rules`，見 `docs/REFERENCES.md` Wispr Flow 調研條目） | — | 🔍 真 API/LLM 端到端待驗；倒數兩階段修復（`c93b37f`、`e34e7a8`，2026-07-24） | `c93b37f` 先把阻塞 GUI 的 `time.sleep()` 改成 `QTimer`；真機覆核再發現 modal `QProgressDialog` 於更新時會搶回前景：Computer Use 切到 LINE、當下函式讀到 `LINE.exe`，三秒 callback 卻兩次得到 `python.exe`。`e34e7a8` 改用原按鈕文字倒數、不建立頂層 dialog；同一流程 callback 實際 PASS `LINE.exe`，規則命中「社群貼文」、未命中回 `None`。驗證器反查 source root；仍待真 API/LLM 輸出情境與 fallback 端到端驗證，故維持 🔍。 |
| 28-1 | v3.4.0 Windows Release ZIP 的 7 個中文檔名在英文 runner 被 `tar.exe` 轉成 literal `?`，導致 `Expand-Archive` 失敗且情境模板缺失 | 高（正式產物不可正常解壓） | ✅ 已修並自 v3.4.1 重發（`a9ac6de`，2026-07-23） | 改 .NET `ZipArchive` UTF-8；新增 `tools/verify_release_zip.py`、10 項回歸測試與 workflow 上傳前 gate。正式 v3.4.2 Lite／NoModel 的 SHA、CRC、UTF-8 資源均再次實證通過，Lite 完成 Windows 解壓與 runtime imports；既有 v3.4.0 資產保留為壞包事故紀錄。 |
| 28-2 | `_sync_preload_models()` 把非同步 subprocess warmup 當成同步完成，worker 尚未 ready 就設 `_models_ready=True` 並顯示設定 UI | 中（啟動狀態與真實 readiness 不一致） | ✅ 已修（`7778e13`，2026-07-23） | `warmup()` 現等待 worker 的 `ready`＋帶成功狀態的 `warmup_done`；error、程序死亡、pipe 關閉或 reader 失敗均撤銷 ready 並拋錯。首次模型下載不設絕對 timeout，避免慢網路超時後永久卡住。8 項回歸測試；Windows 真 worker tiny CPU int8 首次 11.12 秒、快取後 1.52 秒；正式 v3.4.2 Lite 解壓目錄 warmup 2.14 秒，皆只在完成後 PASS。 |
| 28-3 | Computer Use/UIA 操作封裝 UI 時，app 兩度以 Windows fatal exception `0x8001010d` 消失 | 中（需重現歸因） | 🔍 真人環境重驗 | `main_crash.log` 兩次都停在 `ui/app.py:173 app_inst.exec()`，無正常 shutdown；可能是 UIA/COM 輸入同步互動誘發，現有證據不足以歸咎一般使用者操作或 STT warmup。需不用 UI 自動化的真人點擊重驗。 |
| 28-4 | `manual_stt_warmup_check.py` 的來源 override 指錯時仍可能從 cwd 匯入 repo，讓「正式包 PASS」測到原始碼 | 高（驗證可產生假陽性） | ✅ 已修（`119836a`，2026-07-23） | override 先驗 `stt/subprocess_whisper.py` 存在，import 後再要求模組 `__file__` 位於指定 root。不存在路徑實測 exit 1；正式 v3.4.2 解壓目錄實測列出正確 module path 並 PASS。 |
| 28-5 | 暫存清理範例只用 `StartsWith($TempBase)`，會把 `%TEMP%` 本身也判為可遞迴刪除 | 高（可能誤刪整個暫存根目錄） | ✅ 已修（`119836a`，2026-07-23） | `docs/RELEASE_VERIFICATION.md` 現拒絕空白、明確拒絕 target 等於 temp root，並要求 canonical target 以 temp child prefix 開頭；.NET fallback 沿用同一 guard。負向／合法子目錄案例均實測通過。 |
| 28-6 | `9f95aa1` 把 `self.tray.run()` 換成 `app_inst.exec()` 時漏掉隱含的 `tray.start()`，Windows 系統匣從未建立 | 中高（基本 UI 功能缺失） | ✅ 已修（`d672a02`，2026-07-23） | `run()` 現在模型／全時模式準備後先啟動 tray，再啟動 hotkey。新增 AST 順序回歸測試；正式 v3.4.3 Lite 包內 Qt live object 回讀 `visible=True`、`tooltip=聲成文`、icon 非空。 |
| 28-7 | tray 品牌列沒有 callback；Settings／About 在 QAction callback 內搶前景，且 modal About 會阻塞其他 app 視窗 | 中（使用者點擊像沒反應） | ✅ 已修（`d672a02`，2026-07-23） | 品牌列與偏好設定均開 Settings；視窗顯示後延遲到 menu 關閉再 activate，About 改保留單一 modeless instance。正式 v3.4.3 Lite 包內 Qt callback 驗證 Settings 1200×840 與 About 680×720 同時 visible、非 minimized；widget 原生截圖確認 About 無裁切／重疊。 |
| 28-8 | 舊龍圖含不可讀文字，About 固定 320×430 導致版本與完整署名裁切／重疊 | 中低（品牌與可讀性） | ✅ 已修（`d672a02`，2026-07-23） | 新增透明語音泡泡＋麥克風＋波形標誌，更新 PNG／tray PNG／多尺寸 ICO；About 改可縮放、可捲動的 680×720 版面並保留完整署名鏈。正式 v3.4.3 Lite 截圖確認無鮮綠底、裁切或重疊。 |
| 28-9 | v3.4.3 CI／Release workflow 成功但 GitHub 標註所用 action 仍以已淘汰的 Node.js 20 為目標，目前由 runner 強制改用 Node.js 24 | 低（CI 維護性） | ✅ 已修（`02bd6b5`，2026-07-24） | 全部 workflow 升級至 `actions/checkout@v7`、`actions/setup-python@v7`、`actions/upload-artifact@v7`、`softprops/action-gh-release@v3`；逐一核對官方 `action.yml` 均使用 Node 24 且既有 inputs 相容，新增防降級測試。 |
| 29-1 | tray menu callback 在迴圈中晚綁定 `action`，所有 callback 可能收到最後一個 QAction；`stop()` 呼叫不存在的 `QSystemTrayIcon.stop()` | 中（選單動作可能錯置、退出清理例外） | ✅ 已修（`81ce7a7`，2026-07-24） | handler 現將各 QAction 綁為預設參數；stop 改為 hide、deleteLater 並清除引用。新增真 PyQt menu trigger 與 tray lifecycle 回歸測試。 |
| 29-2 | 基底靈魂檔寫入失敗被 `except: pass` 吞掉，UI 仍顯示「設定已儲存」 | 中（設定遺失且假成功） | ✅ 已修（`788fcc5`，2026-07-24） | 抽出 `_save_soul_prompt()`；OSError 現記錄路徑與錯誤、顯示失敗訊息並中止其他設定儲存。成功與缺目錄失敗路徑皆有回歸測試。 |
| 29-3 | 設定頁麥克風測試在 GUI thread 以 `time.sleep()` 阻塞 3 秒，錄音期間整個視窗像當機 | 中（真人驗證 UX 與 UI Automation 穩定性） | ✅ 已修（`894a101`，2026-07-24） | `sd.rec` 保持非同步，倒數改由 `QTimer` 驅動；完成後才 `sd.wait()`／計算 RMS，成功、靜音、例外均清除 timer/progress/recording。真人只需回答準備提示並發聲；2 項回歸測試通過。 |
| 29-4 | `main.py` 緊急 crash log 仍有最後一個 bare `except:`，可能連 `KeyboardInterrupt`／`SystemExit` 一併吞掉 | 低（錯誤處理一致性） | ✅ 已修（`e0b690d`，2026-07-24） | 收窄為 `except Exception`，新增 AST 全 repo guard；任何新 bare-except 都會讓 pytest 失敗。 |

**統計**：已修/已驗證 47 項、待修 0 項、決定不做 0 項、需實機驗證 3 項（27-1／27-2／28-3）。

---

## 未驗證邊界（誠實聲明）

- **真人語音音量**：麥克風裝置列舉/開串流/讀樣本機制層已驗證無例外，但 agent 無法對著實體麥克風真的發聲，未證明「收到有意義音量的真人語音」這一步。
- **真 API key 雲端引擎**：Groq／Gemini／OpenRouter／Claude／OpenAI／Qwen／DeepSeek 七個 provider 仍只有 mock 測試覆蓋，未用真實 API key 打過一次真實請求。
- **系統匣圖示的像素級辨識**：修復後已實證 `QSystemTrayIcon` 顯示成功，Qt live object 為 visible、tooltip「聲成文」、icon 非空；但受限測試機工作列圖示過多，仍未用截圖肉眼百分之百指認對應像素。
- **v3.4.0 正式資產**：Lite／NoModel ZIP 仍是失敗產物，請改用已驗證的 v3.4.3；舊 tag 不覆寫。
- **UIA crash 歸因**：自動化操作可重現兩次 `0x8001010d`，但需真人、不掛 UI Automation 的環境確認是否為一般產品路徑。

---

## 下一步建議

1. 在有真實 API key 與真人麥克風、且不掛 UI Automation 的環境完成 crash、Silero/RMS、基本貼字與前景情境端到端驗證。
2. 系統匣圖示做一次人工目視確認（低優先，啟動、visible、tooltip 與 icon 物件已實證正確）。
3. GitHub Actions 已升級至 Node 24 世代；確認下一輪 main CI 與 tag Release workflow 不再產生 Node 20 淘汰註記。

---

## 維護慣例

- **REVIEW.md 採 latest-only**：只放最新一次覆核於根目錄，不逐版累積歷史。
- **修 bug 必回註本檔問題總帳的狀態欄**：規則見 [`AGENTS.md`](AGENTS.md)「開發約定」，適用所有 AI agent。
- **修復回註優先引用 `CHANGELOG.md`/`docs/DECISIONS.md` 的章節與日期**，不依賴 commit hash（squash 後會失效）。

---

*本 review 為對 release ZIP 修補 `a9ac6de`、STT readiness 修補 `7778e13` 與正式 v3.4.3 發佈（`d672a02`）的覆核；`python -m pytest tests/ -q` 已實跑（423 passed, 10 skipped），五版本 CI、正式資產重下載、Windows 解壓、正式包 tray 與視窗 callback 驗證通過。既有 GitHub v3.4.0 資產仍不得視為通過。*
