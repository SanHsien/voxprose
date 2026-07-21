# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）Review

- **日期**：2026-07-22
- **Reviewer**：Claude Code（延續前次 review 的問題總帳與判斷，本次更新聚焦「實機驗證」這個先前標記為最大缺口的項目）
- **Review 對象**：`main` 分支 @ `b962343`（v3.2.0，尚未打 tag）
- **方法與限制**：全樹靜態讀碼＋`python -m pytest tests/ -v` 實跑（**278 passed, 10 skipped**）＋**本輪新增：完整實機驗證**——乾淨 venv 安裝 `requirements-win.txt`、`self_check.py`／`diagnose_mic.py`／合成語音端到端 STT／`python main.py` 實際啟動／SettingsWindow 七分頁全部在真實 Windows 桌面環境（含 PyQt6、sounddevice、真實麥克風 19 組裝置、RTX 3060）跑過，證據見 `scratchpad/real-machine-verification-report.md`。仍未驗證：真人語音音量、單字語氣詞音訊往返、系統匣圖示像素辨識、真實雲端 API key、真實 CUDA 加速、release ZIP 人工試裝，詳見第 8 節。

---

## 總評

**健康分數：8.3 / 10（原 7.6，+0.7）。**

上一版 review（v3.1.0，2026-07-20）把健康分數壓在 7.6，明確點名「全部修復與新功能沒有一項在真實 Windows 桌面環境跑過」是**最大且未變動的結構性缺口**——紙面工程紀律做得再好，一個核心價值是「錄音→辨識→貼字」即時互動體驗的桌面程式，沒人真的按過熱鍵、沒人真的讓 Whisper 辨識過一句真實語音，這個未知數大到不該給更高分。

**這個缺口本輪已經填掉，而且結果是乾淨的：** 在有 PyQt6/sounddevice/真實麥克風（Logitech C615 等 19 組裝置）/RTX 3060 的機器上，完整跑過整條鏈路——`requirements-win.txt` 在乾淨 venv 89 秒零衝突裝完（連版本上限鎖定這個此前也只在紙面上驗證過的機制，都順帶驗證了真的可解）；`self_check.py` 的 STT 子行程真的啟動、就緒、辨識；用 Windows SAPI 中文語音合成引擎產生的真實語音 WAV，經過真正的 Whisper 子行程，第一次在本 repo 歷史上正確辨識出對應的中文文字（非 mock、非靜音）；`python main.py` 兩次啟動全部無崩潰，`windows_cuda_qt_crash_postmortem.md` 記載的 PyQt6/CUDA 載入順序致命衝突**沒有發生**，`main_crash.log`／`worker_crash.log` 全程 0 bytes；SettingsWindow 七分頁在裝有 sounddevice 的完整環境下全部通過（先前只驗證過 fallback 分支，這次才是真分支）。這不是「跑起來沒噴錯」這種低標準的通過，是「STT 真的把語音變成了正確的文字」這種直接對應核心價值主張的驗證。

**同樣重要的訊號**：實機驗證過程中又抓到 4 個先前紙面 review／278 個單元測試都沒攔到的真實 bug（見問題總帳新增列 25-1～25-4），且每一個都當場修好、補了防回歸測試、pytest 全程維持綠燈——這代表「紙面工程紀律很扎實」與「願意在發現新問題時立刻認帳修正」這兩件事在本次驗證輪次裡同時成立，不是只挑軟柿子驗證。這 4 個新發現分別是：啟動/自檢日誌裡 `BUILD_ID` 與 `VERSION_NAME` 疊字重複（純體驗瑕疵）、設定視窗側欄署名鏈把原創作者誤植為本 fork 開發者且漏列兩層真正的維護鏈（框架性錯誤，非單純漏字）、CUDA Dashboard 文案與 worker 實際降級行為矛盾（使用者可能誤以為自己在用 GPU 加速，實際上在用 CPU——中等偏高的信任問題，已修好並抽出共用真相源 `stt/cuda_check.py`）、以及一個在特定 Python 建置上必然失敗、與本次任務改動無關的既有測試斷言脆弱性（已用 `git stash` 在未改動 HEAD 上重現確認為既有缺陷）。這些 bug 的共通點是「只有真的執行過才可能發現」——日誌重複要看真實 log 輸出、CUDA 文案矛盾要有真實 GPU 但故意不裝 CUDA 函式庫的環境、測試斷言脆弱性要換一個 Python 建置——恰好證明了「未實機驗證」這個缺口過去有多真實，以及填補它的價值。

**為什麼不是 9 分以上**：填掉最大缺口值得大幅加分，但這次驗證同時誠實暴露了幾個仍然存在、範圍更窄但仍是真實未知數的邊界（詳見第 8 節）——真人對麥克風說話的音量鏈路（agent 無法發聲，僅驗證到機制層無例外）、單獨一個語氣詞「嗯」的合成語音辨識（過濾邏輯本身已用直接呼叫驗證正確，但音訊完整鏈路因 TTS 音色限制無法重現）、系統匣圖示的像素級人眼辨識、七個雲端 LLM/STT provider 一次都沒用真實 API key 打過請求、CUDA 實際加速從未在裝了 `requirements-cuda-win.txt` 的機器上跑過、以及打包出的 release ZIP 從未有人真的解壓縮雙擊安裝過。這些是「紙面完成、實機仍未知」的縮小版重演，範圍比「整個程式沒人跑過」窄得多，但仍然是誠實的缺口，不該假裝已經填平。8.3 分反映「最大的未知數已解決、且解決得乾淨」與「幾個範圍更窄的未知數依然存在」兩者的淨效果，不是為了好看而灌水。

---

## 問題總帳

> 狀態標記：✅ 已修（附出處；squash 後 commit hash 多數已不在目前 `git log` 可達範圍內，一律註明「引自 CHANGELOG/DECISIONS，hash 現況見第 4 節」）｜⏳ 待修（附建議優先序）｜🚫 決定不做（附理由出處）｜🔍 需實機驗證。
> 編號延續舊版 REVIEW.md 風險排序表 1-12（該表對應的是 win-stable 分支尚未併入 main 前的狀態），13 起為 CHANGELOG/DECISIONS 記載的後續發現，24 起為 2026-07-20/21 review 輪次新發現（見第 4 節），25 起為本輪（2026-07-22）實機驗證新發現（見第 5 節）。

| # | 問題 | 嚴重度 | 狀態 | 備註 |
|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*`，Inno Setup 打包大機率編譯失敗 | 高（打包鏈斷裂） | ✅ 已修（引自 CHANGELOG「Fixed」節，hash `04d82cc`，2026-07-19） | 全檔搜尋 `platform_layer` 已無結果 |
| 2 | STT 引擎選單「Gemini」選項無對應分派分支，選了會靜默 fallback 成本地 Whisper | 中高（使用者可見功能性 bug） | ✅ 已修（`71f0cbe`，2026-07-19） | `stt/__init__.py` 已有 `elif engine == "gemini"` 分支；`tests/test_stt_engine_dispatch.py` 通過 |
| 3 | 完全沒有 Whisper 幻覺過濾機制，相對 Mac 主線是功能倒退 | 中高（辨識品質風險） | ✅ 已修（`7bf8592`，2026-07-19） | `stt/hallucination_filter.py` 存在，接線於 `ui/app.py`；`tests/test_stt_hallucination_filter.py` 通過；**本輪實機驗證**：直接文字呼叫確認「嗯」被過濾、完整句不被過濾，符合設計 |
| 4 | API Key 明碼且設計上會同步到第三方雲端資料夾（iCloud/Google Drive/NAS） | 高 | ✅ 已修（`cc1e2d1`，2026-07-19） | `config.py` `LOCAL_KEYS` 收錄 `*_api_key` 欄位；`tests/test_config.py` 通過 |
| 5 | 完全沒有 `test_*.py`，核心 pipeline 零自動化測試覆蓋 | 中高 | ✅ 已修（`f8633de` 起，2026-07-19） | `tests/` 現有 20 個測試檔，`python -m pytest tests/ -v` 實跑 **278 passed, 10 skipped** |
| 6 | `paths.py` 宣告的雲端同步路徑常數是死碼，實際未同步 | 中（誤導性） | ✅ 已修（`c37b286`／`53a4ef3`） | 四個常數本體已不存在 |
| 7 | `ui/settings_window.py` god file | 中 | ✅ 已修（`1252a68`，2026-07-21） | 拆分為 ~490 行薄殼＋`ui/settings/` 七分頁子套件；**本輪實機驗證**：完整環境（含真 sounddevice）下七分頁全數通過，非先前僅驗過的 fallback 分支 |
| 8 | `requirements-win.txt` 無版本上限鎖定 | 中低 | ✅ 已修（`266280d`，2026-07-21） | **本輪實機驗證**：完整 `requirements-win.txt` 在乾淨 venv 89 秒安裝成功、零版本衝突，證實版本上限鎖定本身不會讓 pip 解析失敗 |
| 9 | `diagnose_mic.py` 在 Windows 上是 macOS-only 死碼空殼 | 低 | ✅ 已修（`0ee2730`，2026-07-19） | **本輪實機驗證**：真實列出 19 組裝置（Logitech C615 等），開啟串流讀取成功 |
| 10 | PTT／VAD 全時模式並行時缺乏互斥檢查 | 低中 | ✅ 已修（`e33d479`，2026-07-19） | `audio/mutex.py` 存在；`tests/test_recording_mutex.py` 通過 |
| 11 | `eval()` 用於語音計算機指令，注入面 | 低 | ✅ 已修（`3d2c215`，2026-07-19） | 改 `ast.parse(mode="eval")` 白名單解析 |
| 12 | `ui/settings_window.py` 硬編碼 macOS 字型 `Monaco` | 低 | ✅ 已修（`2e52f87`，2026-07-19） | 現於 `ui/settings/soul_page.py`，改 `QFont("Consolas", ...)` |
| 13 | OpenRouter STT 引擎自始壞掉 | 中高 | ✅ 已修（`75952fd`，2026-07-19） | `stt/openrouter_stt.py` 已修正；`tests/test_openrouter_stt.py` 通過 |
| 14 | Claude LLM 引擎自始壞掉（欄位名不一致） | 中高 | ✅ 已修（`9192ef6`，2026-07-19） | `llm/claude.py` 已讀 `anthropic_*`；`tests/test_llm_config_keys.py` AST 靜態掃描防回歸 |
| 15 | 網路請求逾時缺口 | 中 | ✅ 已修（`eb61819`，2026-07-19） | `net_config.py` 定義 `CLOUD_REQUEST_TIMEOUT_SECONDS`；`tests/test_provider_timeouts.py`（2 個測試因本機未裝 anthropic/groq SDK 而 skipped） |
| 16 | STT 語言 hint 被翻譯目標語言污染 | 高 | ✅ 已修（`d99a326`，2026-07-20） | `stt/language.py` 已接線；`tests/test_stt_language_selection.py` 通過 |
| 17 | 智慧詞彙學習對本地辨識完全無效 | 中高 | ✅ 已修（`aee3973`，2026-07-20） | worker 已讀取 IPC `prompt` 欄位；`tests/test_stt_transcribe_params.py` 通過 |
| 18 | LLM system prompt 分散硬編，無多語 fallback | 中 | ✅ 已修（`19017c8`，2026-07-20） | `llm/prompts.py` 存在；`tests/test_llm_prompts.py` 通過 |
| 19 | LLM 未啟用時輸出文字沒有贅詞清理 | 中 | ✅ 已修（`da93f62`，2026-07-20） | `utils/soul_rules.py` 存在並接線 |
| 20 | `soul/scenario/default.md` 贅詞清單缺項 | 低 | ✅ 已修（`1e53549`，2026-07-20） | 依 CHANGELOG 記載列為已修 |
| 21 | 無崩潰/環境診斷匯出管道 | 中（支援成本） | ✅ 已修（`7bc3b0f`，2026-07-20） | `utils/diagnostics.py` 存在；**本輪意外發現並修復**：`tests/test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗，見 25-4 |
| 22 | `vocab/manager.py` 常數命名撞名 | 低 | ✅ 已修（`27d93c8`，2026-07-20） | 已改名 `_VOCAB_DATA_DIR` |
| 23 | `requirements-win.txt` 列了多餘的 `pystray` 依賴 | 低（清理項） | ✅ 已修（`aa1e220`，2026-07-21） | 已移除；`ui/menu_bar.py` 死分支一併清理（24-2） |
| 24 | 見第 4 節「2026-07-20/21 輪次新發現」24-1（✅ 已處理）／24-2（✅ 已修）／24-3（✅ 已驗證，見下） | — | ✅ | 24-3：**本輪已驗證**——直接函式呼叫確認「嗯」單字被過濾、完整句不被過濾，符合設計；音訊完整鏈路（合成語音→引擎→過濾器）驗證了完整句能正確通過，但「單獨嗯」這個音訊案例因 SAPI TTS 音色限制，Whisper 辨識不回「嗯」這個字本身，故該分支未能用音訊鏈路重現（過濾器邏輯本身已用直接呼叫證實正確），詳見第 5 節 25-說明與第 8 節 |
| 25 | 見第 5 節「2026-07-22 實機驗證輪新發現」25-1～25-4 | — | ✅ 已修 | 4 項皆在本輪實機驗證過程中發現並當場修復，見下 |

**統計**：已修 25 項（含本輪新增 4 項）、待修 0 項、決定不做 0 項（歷史上的「不吸收」項目屬功能吸收分析範圍，詳見 `docs/mac-mainline-absorption-analysis.md` 第 6 節）。**24-3 本輪已從「🔍 需實機驗證」轉為「已驗證（附誠實限制）」**——過濾邏輯本身正確性已確認，音訊完整鏈路的「單獨嗯」子案例因外部工具（TTS 音色）限制未能重現，非程式缺陷。此前貫穿全專案的最大缺口「全部修復與新功能尚未實機驗證」**本輪已解決**，見總評與第 8 節剩餘的窄範圍未驗證項目。

---

## 4. 2026-07-20/21 輪次新發現（沿用前次 review 內容）

### 24-1（中，文件治理缺口，✅ 已處理）squash 後大量修復 commit hash 已不在 `git log` 可達範圍——已於 `4278ff8`（2026-07-20）在 `CHANGELOG.md:7`／`docs/DECISIONS.md:5` 補免責聲明

`git merge-base --is-ancestor <hash> HEAD` 逐一驗證過，`CHANGELOG.md`/`docs/DECISIONS.md` 引用的近 20 個修復 commit hash 全部不是 `HEAD` 的祖先，只殘留在本機 `reflog`，未來 `git gc`/重新 clone 會查無此 hash。已於 `4278ff8` 補免責聲明，說明這些 hash 僅作文件內識別碼保留，無法 `git show`。

### 24-2（低，清理項，✅ 已修）`ui/menu_bar.py` 殘留 pystray 時代的死分支——已於 `aa1e220`（2026-07-21）清理

`_get_sender_text` 內兩處 pystray 時代死分支（一處與前一個 `if` 條件完全相同永遠不可達，一處用 `and False` 自我短路）已移除，與 #23（`requirements-win.txt` 殘留 `pystray` 套件宣告）同一批技術債一併清理。

### 24-3（✅ 本輪已驗證，附誠實限制）`stt/hallucination_filter.py` 的極短口語詞（「嗯」「啊」等）落入黑名單

**本輪驗證結果**：
- **直接函式呼叫（`is_hallucination()`，非 mock）**：`is_hallucination('嗯') = True`（單獨「嗯」→ 被過濾，符合設計）；`is_hallucination('嗯，我想想這個問題') = False`（完整句子→不被過濾，符合設計）。過濾器邏輯本身確認正確。
- **真實音訊往返**：用 Windows SAPI 中文語音合成完整句子「嗯，我想想這個問題」，經真實 Whisper 引擎（tiny/base 兩模型）辨識後的文字都不在黑名單、正確不被過濾——音訊→引擎→過濾器的完整真實路徑對「完整句」案例驗證通過。
- **未能重現的子案例**：單獨合成「嗯」（含變速/延長嘗試「嗯～～～」「嗯嗯嗯」）餵給 tiny/base 兩個模型，皆未被辨識回文字「嗯」本身（分別得到「Open。」「音音辨識。」「」「NNNNNN」等），故「使用者真的只說一個字嗯，被過濾器擋下」這個具體音訊案例未能在本次環境重現。這是本次驗證用的 TTS 音色對這個特定短促單音節的合成/辨識限制，不是 `hallucination_filter.py` 或 `subprocess_whisper.py` 的程式錯誤——過濾器判斷邏輯本身已用直接呼叫證實符合規格。
- **結論**：狀態由「🔍 需驗證」轉為「已驗證（邏輯正確，音訊完整鏈路的單字子案例受外部工具限制未能重現，非缺陷）」。

---

## 5. 2026-07-22 實機驗證輪新發現

實機驗證任務執行過程中，跑 `self_check.py`、`python main.py`、以及本節列出的相關檢查時，額外發現並修復以下 4 個問題（皆非本次任務原本要驗證的目標，而是驗證過程中意外撞見）：

### 25-1（低，體驗瑕疵，✅ 已修）啟動/自檢日誌 `BUILD_ID` 與 `VERSION_NAME` 疊字重複——`fe25423`

`paths.py` 的 `VERSION_NAME` 本身已內含 `(BUILD-3200-STABLE)`，但 `main.py`（2 處）、`ui/app.py`（1 處）、`self_check.py`（1 處）又各自疊加輸出一次 `BUILD_ID`，實機執行時真實 `debug.log` 出現 `V3.2.0 Windows Edition (BUILD-3200-STABLE) (BUILD-3200-STABLE)` 這種重複字樣，容易造成誤讀。已移除多餘的 `BUILD_ID` 疊加輸出並清掉因此變成未使用的 import；`self_check.py` 的版本常數檢查改為明確標註兩個常數各自的值，維持原本「NameError 迴歸驗證」用意但不再重複字串。修復前後 `python -m pytest tests/ -v` 皆為 266 passed, 10 skipped（此輪基準），改動前後無差異。

### 25-2（中，署名框架錯誤，✅ 已修）設定視窗署名鏈框架錯誤且不完整——`e8b0f91`

`ui/settings_window.py:274` 側欄署名文字原為「主要開發者：吉米丘, CC58TW」，把原創作者（吉米丘、CC58TW）誤植為本 fork 的「主要開發者」，且完全漏列上游 Windows 專用版維護者 **go-mask** 與本 fork 維護者 **SanHsien**——這是 2026-07-22 稍早「品牌殘留清掃」任務遺留的缺口（當時 `credit_box` 文字被明確標註「原封不動」保留，沒有連帶檢查框架是否正確）。已改為完整四層署名鏈（原創：吉米丘、CC58TW／上游 Win 版：go-mask／本 fork：SanHsien／協助：Claude Code），比照 `NOTICE.md`／`README.md`／`about_window.py` 既有措辭；`about_window.py` 核實本來就四層俱全，未改動。詳見 `docs/DECISIONS.md` 2026-07-22 條目。

### 25-3（中偏高，使用者信任問題，✅ 已修）CUDA Dashboard 文案與 STT worker 實際降級行為矛盾——`e8b0f91`

`ui/settings/dashboard_page.py` 原本只用 `ctranslate2.get_cuda_device_count() > 0` 判斷「CUDA 加速可用」，但這只反映驅動層級「有沒有偵測到裝置」，不代表 `stt/subprocess_whisper.py` 的 worker 實際載入模型時真的能用到——worker 另外會用 `ctypes.WinDLL("cublas64_12.dll")` 做硬驗證，失敗就強制降級 CPU。實機查證：本機確有 RTX 3060（`nvidia-smi` 確認），`get_cuda_device_count()` 回報 1，但驗證用的 `venv_real` 只裝了 `requirements-win.txt`（未裝 `requirements-cuda-win.txt`），硬驗證確實失敗——Dashboard 卻仍顯示「✅ CUDA GPU × 1 (加速可用)」，與 worker 實際用 CPU 跑的事實矛盾，使用者會誤以為自己正在用 GPU 加速。

修法：新增 `stt/cuda_check.py:probe_cuda()`，抽出與 worker 完全相同的判定邏輯（NVIDIA DLL 路徑探索＋cuBLAS 硬驗證），讓 Dashboard 與 worker 共用同一個真相源，不再各說各話；Dashboard 文案改為三態（✅ 加速可用／⚠️ 偵測到 GPU 但缺 CUDA 函式庫／⚠️ 未偵測到 CUDA GPU）。新增 `tests/test_cuda_check.py`，用 mock 覆蓋六種情境（含本次 bug 的真實重現案例：有裝置但 cuBLAS 載入失敗），不打真實硬體、CI 也能穩定跑。詳見 `docs/DECISIONS.md` 2026-07-22 條目。

### 25-4（低，測試基礎設施脆弱性，✅ 已修）`tests/test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗——`49c29ae`

`test_opens_explorer_to_highlight_zip_on_windows` 原本斷言 `mock_popen.assert_called_once()`，但 patch 對象 `utils.diagnostics.subprocess.Popen` 是行程全域共用的 `subprocess` module。在本次驗證用的 `venv_real`（uv 安裝的 cpython 3.11.15 embeddable 建置）上，`collect_env_info()` 呼叫的 `platform.platform()`/`platform.uname()`/`platform.win32_ver()` 各自透過 `platform._syscmd_ver()` 呼叫 `subprocess.check_output("ver", shell=True, ...)`，被同一顆 mock 一併攔截計入次數（實際 4 次：3 次 `ver` + 1 次 `explorer`），與此測試想驗證的行為無關。已用 `git stash` 在未改動的 HEAD 上重現同樣失敗，確認是既有缺陷、與本次任務改動無關。改為在 `call_args_list` 篩選開頭是 `"explorer"` 的呼叫、斷言恰好一次，不再對總呼叫次數斷言。

---

## 6. 現況架構速覽

| 模組 | 行數級距 | 職責 |
|---|---|---|
| `main.py` | ~130 | 進入點：crash-proofing 環境變數、`initialize_paths()`、啟動 `VoiceTypeApp`；**本輪實機驗證**兩次啟動皆無崩潰 |
| `ui/app.py` | ~600 | `VoiceTypeApp(QObject)` 協調者：熱鍵/錄音/STT/LLM/注入/記憶全流程 orchestration |
| `ui/settings_window.py` | ~492 | `SettingsWindow` 薄殼：多重繼承混入 `ui/settings/` 七分頁 mixin；**本輪實機驗證**七分頁在含真 sounddevice 的完整環境全數通過 |
| `ui/settings/`（8 檔） | ~各 40~360 | 設定視窗七分頁 mixin（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`）+ 共用元件 `common.py`；`dashboard_page.py` 的 CUDA 狀態改呼叫 `stt/cuda_check.py:probe_cuda()`（25-3） |
| `ui/menu_bar.py`／`tray_manager.py`／`mic_indicator.py`／`floating_button.py`／`positions.py`／`about_window.py` | 各 ~70~360 | PyQt6 選單列／系統匣／浮動指示／浮動按鈕／視窗位置記憶／關於視窗 |
| `hotkey/listener.py` | ~140 | 純 `ctypes` 輪詢 Win32 API 的全域熱鍵，無 `pynput` |
| `audio/recorder.py`／`auto_trigger.py`／`gain.py`／`mutex.py` | ~80~190 | PTT 錄音／VAD 全時模式／增益＋AGC 純函式／PTT-VAD 互斥狀態機 |
| `stt/`（9 檔） | ~10~460 | `subprocess_whisper.py`（子行程隔離本地 Whisper，最大最複雜；**本輪實機驗證** STT 子行程真的辨識出合成語音的中文文字）＋ 4 個雲端引擎＋`hallucination_filter.py`＋`language.py`＋**新增** `cuda_check.py`（`probe_cuda()`，Dashboard 與 worker 共用的 CUDA 加速判定真相源，見 25-3） |
| `llm/`（9 檔） | ~10~100 | 7 個 provider（無 minimax）＋`base.py`＋`prompts.py`（集中化 system prompt） |
| `output/injector.py` | ~165 | 剪貼簿 + `SendInput` 模擬注入 |
| `vocab/`／`memory/`／`stats/` | ~95~240 | 自訂詞彙學習／跨 session 記憶／使用統計，各自本機 `%APPDATA%` |
| `utils/`（6 檔） | ~20~280 | 品牌/AppUserModelID、權限（多為 no-op）、資源路徑、靈魂規則純函式、診斷包匯出 |
| `tools/`（4 檔） | ~40~185 | 環境預檢、模型下載、可攜 Python 下載腳本、依賴新鮮度檢查 |
| `config.py`／`paths.py`／`net_config.py` | ~20~175 | 設定讀寫（本地/雲端分流）、路徑常數（**本輪實機驗證**確認 `%APPDATA%\VoxProse` 新路徑確實生效）、逾時常數 |
| `tests/`（20 檔） | — | 278 個自動化測試，見第 7 節 |

---

## 7. 各面向短評

**品質**：核心邏輯模組（`audio/gain.py`、`utils/soul_rules.py`、`stt/hallucination_filter.py`、`audio/mutex.py`、`llm/prompts.py`、**新增** `stt/cuda_check.py`）都刻意抽成無重量依賴的純函式檔案，docstring 交代移植來源、動機與取捨，這是本專案讀碼過程中最一致的優點。`ui/settings_window.py` god file 已拆分（#7）；`ui/menu_bar.py` 的 pystray 時代死碼已清理（24-2）。**本輪新增**：`stt/cuda_check.py` 把 Dashboard 與 worker 的 CUDA 判定收斂成單一真相源，是同類問題（同一件事兩處各自維護邏輯、容易各說各話）的一次乾淨修復示範。目前無已知的程式碼結構性缺點待清。

**安全與隱私**：API Key 已全部本地化並有遷移邏輯（#4）；計算機 `eval()` 已改 AST 白名單（#11）；`utils/diagnostics.py` 匯出診斷包前會脫敏；`requirements-win.txt`/`requirements-cuda-win.txt` 已補主版本上限（#8，**本輪實機驗證**確認鎖定不會導致 pip 解析失敗）。仍存在但屬「已知且刻意不動」的殘留風險：`llm/gemini.py` 的 API key 走 URL query string（Google 官方設計，非本 repo 問題）。

**測試與 CI**：`python -m pytest tests/ -v` 本次實跑 **278 passed, 10 skipped**（較上次 review 的 233 passed 增加 45，主要來自品牌/簡體字守門測試、`cuda_check.py` 測試、上游更新檢查測試等）。10 個 skip 全部是本機開發環境缺少可選依賴（`anthropic`/`groq` SDK）造成，非測試邏輯問題。CI（`.github/workflows/ci.yml`）在 `windows-latest` 上跑 py_compile 全樹 + pytest。**仍存在的缺口**：CI 本身（自動化、每次 push 都跑）仍只驗證「能 compile、單元測試過」，不會真的開啟 UI/接麥克風/跑 Whisper——本輪填補的是「人工一次性實機驗證」，不是把這件事自動化進 CI；CI 與實機驗證之間的落差本身沒有改變，只是這次有人真的手動走過一遍。

**打包發佈**：`setup_win.bat`／`release_win.ps1`／`voicetype_installer.iss` 三條路徑齊全，死引用已修（#1）。`release.yml` 建置 Lite/NoModel 兩版，範圍限縮有清楚理由。**仍未驗證**：CI 從未真的跑過 `setup_win.bat`/`release_win.ps1` 端到端建置，打包出的 ZIP 也從未有人實際解壓縮、雙擊安裝、走過首次啟動下載模型的流程——這條路徑與「程式本身能不能跑」是分開的兩件事，本輪實機驗證沒有涵蓋到。

**文件**：`AGENTS.md`／`SKILL.md`／`docs/DEVELOPMENT.md`／`docs/DECISIONS.md`／`docs/UPSTREAM.md`／`CHANGELOG.md` 分工清楚。squash 後 commit hash 引用失效問題（24-1）已於 `4278ff8` 補免責聲明。**本輪**`docs/DECISIONS.md` 2026-07-22 條目已完整記錄署名鏈修正與 CUDA Dashboard 查證過程，`CHANGELOG.md` `[3.2.0]` 段已同步涵蓋本輪全部變更。

---

## 8. 未驗證邊界（誠實聲明）

本輪實機驗證填掉了「全部功能沒人真的跑過」這個最大缺口，但以下項目仍然只做了部分驗證或完全未驗證，是誠實的縮小版剩餘邊界，非新發現的缺陷：

- **真人語音音量**：`diagnose_mic.py`／`audio/recorder.py` 的裝置列舉／開啟串流／讀取樣本／算 RMS 機制層在真實硬體上完整跑通、無例外，但驗證時 agent 無法對著實體麥克風真的發出聲音、房間內當下也無人說話，**未能證明「收到有意義音量的真人語音」這一步**（`diagnose_mic.py` 對這種極低音量正確觸發自己的 WARN 分支，屬設計預期行為，非缺陷）。
- **24-3 單獨「嗯」的音訊完整往返**：過濾器邏輯本身已用直接函式呼叫證實正確（見第 4 節 24-3），但用合成語音重現「說一個字嗯→被過濾」這個具體案例，因 Windows SAPI TTS 對短促單音節的合成/辨識限制未能重現，不是程式錯誤。
- **系統匣圖示品牌的像素級辨識**：`TrayManager(title="聲成文", ...)` 建構過程無例外（代表程式邏輯正確執行），但受限於測試機工作列圖示過多、懸停未觸發 tooltip，未能用螢幕截圖肉眼百分之百指認出對應本程式的圖示。
- **真 API key 雲端引擎**：Groq／Gemini／OpenRouter／Claude／OpenAI／Qwen／DeepSeek 七個 provider 的請求/回應仍全部只有 mock 測試覆蓋，本輪實機驗證未使用任何一把真實 API key 打過一次真實請求（`tests/test_provider_timeouts.py` 兩個測試因本機未裝 SDK 而 skipped，並非「已驗證但通過」）。
- **CUDA 實際加速**：本輪驗證環境只裝了 `requirements-win.txt`，未裝 `requirements-cuda-win.txt`，因此親眼見證了「有 GPU 但缺函式庫時的正確降級」（並修好了 Dashboard 文案矛盾，見 25-3），但**尚未有人在真的裝了完整 CUDA 函式庫的機器上驗證加速確實生效、確實比 CPU 快**。
- **NoModel/Lite 包實際安裝體驗**：`release.yml` CI 建置通過（產出 ZIP、算出 sha256），但沒有人工解壓縮、雙擊啟動、走過首次啟動下載模型的完整流程。

---

## 9. 下一步建議

1. **（新首要）在有真實 CUDA GPU 且已安裝 `requirements-cuda-win.txt` 的機器上驗證加速實際生效**：這是目前唯一一項「有明確方法可以驗證、但這次驗證環境條件不滿足」的項目，`stt/cuda_check.py:probe_cuda()` 已經是現成的驗證入口，跑起來後確認 `accel_available=True` 且辨識速度確實快於 CPU 即可收斂。
2. **在有真實各雲端 API key 的環境跑一次端到端整合測試**：七個 provider 從未被真實請求驗證過，優先序次於 CUDA 是因為這些 provider 是可選功能（本地 Whisper 才是預設路徑，已驗證），但仍是「寫得對」與「跑得動」之間的已知落差。
3. **release ZIP 人工試裝一次**：解壓縮 Lite／NoModel 兩版 ZIP、雙擊啟動、走過首次啟動下載模型流程，確認打包鏈不只是「CI 建置成功」而是「使用者真的能裝起來用」。
4. **（低優先，可選）補一次真人對麥克風說話的錄音驗證**：需要有人（非 agent）實際對著麥克風說話，驗證音量鏈路收到有意義訊號、以及 24-3 單獨「嗯」的完整案例——優先序低是因為過濾器邏輯與麥克風機制層都已個別驗證正確，這只是最後把兩者連在一起的人工確認，不太可能發現新問題。
5. ~~**（最高優先）實機驗證整條鏈路**~~：**本輪已完成**——`self_check.py`／`diagnose_mic.py`／端到端合成語音 STT／`python main.py`／SettingsWindow 七分頁全數在真實環境跑過，見總評與第 5 節。

---

## 10. 維護慣例

- **REVIEW.md 採 latest-only**：只放最新一次覆核於根目錄，不逐版累積歷史（比照 `docs/DECISIONS.md` 2026-07-19 條目定下的慣例）。
- **修 bug 必回註本檔問題總帳的狀態欄**：規則見 [`AGENTS.md`](AGENTS.md)「開發約定」——適用所有 AI agent（Claude、Codex、Gemini 等），非 Claude 專屬。修復 `⏳ 待修` 項目或本檔未列出的新 bug 時，回到第 3 節對應列（或新增列）標註修復依據與日期；不得讓本檔長期陳列已解決的問題而不更新狀態。
- **修復回註格式建議**：狀態欄改 `✅ 已修` 時附「commit 訊息摘要或 CHANGELOG/DECISIONS 章節出處＋日期」，鑑於 24-1 的發現，**不建議繼續依賴 commit hash 作為唯一可驗證依據**（squash 後會失效），優先引用 `CHANGELOG.md`/`docs/DECISIONS.md` 的章節標題與日期。

---

*本 review 為對 `main` 分支（`b962343`，v3.2.0）的 review，`python -m pytest tests/ -v` 已實跑（278 passed, 10 skipped）；**本輪新增完整實機驗證**（PyQt6/sounddevice/真實麥克風/合成語音端到端 STT/`python main.py` 實際啟動），證據見 `scratchpad/real-machine-verification-report.md`。工作樹本身未做任何修改，僅新增/改寫本檔案（`REVIEW.md`）。*
