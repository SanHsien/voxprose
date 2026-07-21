# Changelog

本檔案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，是**對外快速掃描用的精簡摘要**，記錄從本 fork（SanHsien）建立開發鷹架起的變更。

完整的、逐版對照使用者需求與驗證證據的詳細歷史，見 [`VERSIONS.md`](VERSIONS.md)（本 fork 沿用上游既有格式，兩份文件並存、各司其職：`CHANGELOG.md` 給快速掃描，`VERSIONS.md` 給深入回溯）。版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

> **關於歷史 commit hash**：v3.1.0 發版時已把 fork 的開發歷史 squash 成單一 commit（`84d1b28`，見 `docs/UPSTREAM.md`）。本檔與 `docs/DECISIONS.md`、`REVIEW.md` 中引用的更早 hash（如 `04d82cc`、`aee3973` 等）屬 squash 前的開發過程紀錄，**已不存在於 git 歷史**，僅作為文件內的變更對照識別碼保留，無法 `git show`。

## [Unreleased]

### Added

- **上游更新自動檢查**：`tools/check_upstream_updates.py` ＋ `.github/workflows/upstream-check.yml`——每週一 02:00 UTC（另支援 `workflow_dispatch`）檢查上游 `jfamily4tw/voicetype4tw-mac` 的三個追蹤分支（`win-go-mask-202607`／`win-stable`／`main`）是否有新 commit，透過 GitHub compare API 比對 `docs/UPSTREAM.md` 新增的「同步狀態標記區塊」（`<!-- sync-points:start/end -->` 內的 JSON，唯一真相源）記錄的 `last_reviewed`（已審視過的最新上游 commit），只回報比它新的變更；有更新時開/更新「上游更新檢查」issue（比照既有 `dependency-freshness.yml` 的 search-or-create 邏輯）。每個分支同時記 `last_merged`（已實際併入本 fork 的上游 commit，等同 `git merge-base`）。新增「Skipped（審視後未採用）」表記錄審視後決定不採用的 commit 與理由，避免 `last_reviewed` 推進後這些決策消失在視野外。`AGENTS.md` 開發約定補一條處理流程；新增 `tests/test_upstream_check.py`（18 個測試，含真實 `docs/UPSTREAM.md` 解析、解析失敗防護、mock API 的報告產生，不打真網路）。

### Changed

- **`ui/settings_window.py` god file 拆分**（REVIEW.md #7）：原本 2164 行的單一設定視窗檔拆成 `ui/settings/` 子套件——七個分頁各一個 mixin 檔（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`）+ 共用元件與常數 `common.py`；`ui/settings_window.py` 收斂為 ~490 行薄殼，`SettingsWindow` 用多重繼承混入所有分頁 mixin，對外 `from ui.settings_window import SettingsWindow` 契約不變（`ui/app.py` 零 diff）。純機械搬移，無邏輯／UI 字串變動；唯一的例外是 `_run_self_check` 內用 `__file__` 反推 repo root 的路徑計算——檔案搬到更深一層目錄後補了一次 `os.path.dirname()`，否則會找錯 `self_check.py` 的路徑。`tests/test_stt_engine_dispatch.py` 的 `STT_ENGINES` 靜態原始碼解析目標同步從 `ui/settings_window.py` 改指向 `ui/settings/common.py`（常數搬去哪、測試就跟去哪，防護力不變）。
- **`requirements-win.txt`／`requirements-cuda-win.txt` 加主版本上限鎖定**（REVIEW.md #8）：每個套件宣告補上一個主版本上限（如 `PyQt6>=6.6.0,<7`），下限維持不變；基準版本取自 `tools/check_dependency_freshness.py` 查得的目前 PyPI 最新版（一般 semver 套件鎖「最新主版本 + 1」）。`pywin32` 無傳統 major.minor.patch 語意（單一遞增 build number，目前 312），改鎖 `<400` 作為寬鬆上限並加註說明；`certifi` 採日曆版本（YYYY.MM.DD），以年份鎖 `<2027`。`docs/DEVELOPMENT.md` 補一句依賴管理策略說明。

### Fixed

- **清理 pystray 技術債殘留**（REVIEW.md #23、24-2）：`ui/menu_bar.py:_get_sender_text` 移除兩處 pystray 時代死分支——一處與前一個 `if` 條件完全相同永遠不可達，一處用 `and False` 自我短路且註解自承 unused；`requirements-win.txt` 移除多餘的 `pystray>=0.19.5`（UI 已全面改用 `QSystemTrayIcon`）。全 repo grep `pystray` 確認零 import；`release_win.ps1` 與 `tools/check_dependency_freshness.py` 皆未引用 `pystray`，無需同步。

## [3.1.0] - 2026-07-20

以 `win-stable` 分支 v3.0.1（`win-go-mask`，`BUILD-3010-STABLE`）為基底，建立 fork 的開發鷹架（比照 `SanHsien/sticker-forge`、`SanHsien/gpt-ai-assistant` 的既有範本）。發版工程收尾：新增 `docs/UPSTREAM.md` 上游追蹤、`release_win.ps1` `-NoModel` 打包選項、`.github/workflows/release.yml` 與 `dependency-freshness.yml` 兩條 CI workflow、`tools/check_dependency_freshness.py` 依賴新鮮度檢查工具，版本推進至 3.1.0（`BUILD-3100-STABLE`）。

### Added

- `LICENSE`：初版為雙軌授權聲明——上游程式碼誠實揭露「無正式授權、著作權屬吉米丘/CC58TW」；SanHsien 在本 fork 新增的原創部分採 MIT License（© 2026）。2026-07-20 隨上游正式補齊 MIT 授權後改寫為全 MIT，見下方 2026-07-20 條目。
- `CLAUDE.md`：Claude Code 專屬薄補丁，指回 `AGENTS.md` 為單一真相源。
- `CHANGELOG.md`（本檔）：Keep a Changelog 格式的精簡對外摘要。
- `pyproject.toml`：套件 metadata（`requires-python = ">=3.10,<3.13"`）與 `[tool.pytest.ini_options]`（`testpaths`/`pythonpath`），不取代 `requirements-win.txt`/`requirements-cuda-win.txt` 的實際安裝鏈。
- `tests/test_smoke.py`：全 repo `py_compile` + 純邏輯模組匯入驗證（optional 依賴模組匯入失敗即跳過）。
- `tests/test_config.py`：從歷史（`git show 51094bf:test_save.py`）移植並改寫的 `config.py` 讀寫回圈測試，改用 `tmp_path`/`monkeypatch` 隔離，不再觸碰開發者真實的 `%APPDATA%\VoiceType4TW\`。
- `tests/manual/manual_qkey_check.py`：從歷史（`git show 51094bf:test_qkey.py`）移植的手動腳本（需可顯示視窗環境，不被 pytest 收集）。
- `.gitattributes`：`* text=auto eol=lf`，但 `.bat`/`.cmd`/`.ps1` 強制 `eol=crlf`（避免 Windows batch 腳本因 LF 換行出現解析地雷）。
- `.github/workflows/ci.yml`：GitHub Actions，`windows-latest` + Python 3.12，安裝 `requirements-win.txt`（不含 CUDA、不下載模型）後跑全 repo `py_compile` + `pytest tests/`。
- `docs/DECISIONS.md` 追加本次鷹架落地的決策記錄。
- **麥克風裝置選擇＋增益＋AGC**（比照 Mac 主線 v2.9.7，`docs/mac-mainline-absorption-analysis.md` 項目 7-1/7-2/7-3）：`audio/recorder.py` 新增 `device`/`gain`/`gain_auto` 參數，`sd.InputStream` 指定輸入裝置（裝置消失時 fallback 回系統預設）；手動增益（50~300%）為實際 PCM 放大（非純視覺）；AGC 用獨立 `_agc_factor`（0.1~8.0×）依近期峰值動態調整、不覆蓋手動 gain。純數學抽成 `audio/gain.py`（無 sounddevice 依賴，可獨立單元測試）。`config.py` 新增 `mic_device`/`mic_gain`/`mic_gain_auto`（機器特定，列入 `LOCAL_KEYS`）。`ui/settings_window.py` 新增裝置下拉選單（含 2 秒插拔輪詢）+ 增益 slider + AGC 勾選框。新增 `tests/test_audio_gain.py`。⚠️ UI/錄音接線未在 Windows 實機驗證（本機無 PyQt6/sounddevice）。
- **錄音靜音預檢跳過 STT**（比照 Mac 主線 v2.9.7，項目 7-4）：`audio/recorder.py:stop()` 計算整段錄音峰值 RMS，低於門檻 0.3%（`audio.gain.SILENCE_THRESHOLD`）即設 `is_silent = True`；`ui/app.py:_on_audio_complete` 據此跳過整段 STT 呼叫，與既有幻覺過濾互補。僅涵蓋 PTT/toggle 路徑，VAD 全時模式不受影響。
- **Whisper 抗幻覺轉錄參數**（比照 Mac 主線 v2.9.13，項目 13-2）：faster-whisper 的 `transcribe()` 呼叫（`stt/subprocess_whisper.py`、`stt/local_whisper.py`）加入 `no_speech_threshold=0.6` + `condition_on_previous_text=False`，從幻覺源頭抑制。新增 `tests/test_stt_transcribe_params.py`。
- **OpenRouter fallback 鏈＋預設模型更新**（比照 Mac 主線 v2.9.16，項目 16-4）：`llm/openrouter.py` 新增 `OPENROUTER_FALLBACK_MODELS` 依序重試機制（`_is_missing_model_error()` 判斷 400/404 模型不存在類回應才觸發）；預設模型由具下架風險的 `google/gemini-2.0-flash-001` 改為 `google/gemini-2.5-flash`。新增 `tests/test_openrouter_fallback.py`。
- **LLM system prompt 集中化**（比照 Mac 主線 v2.9.13，項目 13-1）：新增 `llm/prompts.py`（`SYSTEM_PROMPTS` zh/en/ja + `get_default_system_prompt()`），7 個引擎的 `refine()` 統一改用 `prompt or get_default_system_prompt(self.language)` 防禦性 fallback，避免空 prompt 直接送進 API。清掉 4 個引擎檔重複的硬編中文 `self.prompt` 死屬性。`refine()` 簽章與既有 payload 差異（temperature、指令前綴）不變。新增 `tests/test_llm_prompts.py`。
- **LLM 未啟用時的輕量版靈魂規則**（比照 Mac 主線 v2.9.7，項目 7-5）：新增 `utils/soul_rules.py`（純函式 `extract_filler_words`/`strip_filler_words`/`apply_basic_soul_rules`），`ui/app.py:_apply_basic_soul_rules` 在 LLM 未啟用（且非 showcase/action/demo）時動態解析 soul md 的「贅詞清除規則」區段清除贅詞，不需呼叫任何 LLM API。新增 `tests/test_soul_rules.py`。
- `soul/scenario/default.md` 贅詞清單補「所以說」「就是說」（比照 Mac 主線 v2.9.7，項目 7-6）。
- **Windows 診斷包匯出**（比照 Mac 主線 v2.9.11 崩潰診斷管道，項目 11-3）：新增 `utils/diagnostics.py`，一鍵打包 Windows 環境資訊（`platform.win32_ver()` + ctypes `GlobalMemoryStatusEx` 總 RAM）、音訊裝置清單、debug.log/keystrike.log/main_crash.log 尾段、脫敏設定摘要到桌面 zip。設定頁新增「📦 匯出診斷包」按鈕。新增 `tests/test_diagnostics.py`（13 個測試，在真實 Windows 開發機上對環境收集函式直接驗證）。
- `docs/UPSTREAM.md`：記錄雙上游祖先鏈（`win-stable`／`win-go-mask-202607`／Mac 主線 `main`）的同步狀態與檢查上游更新標準流程，供 squash 後的單一 commit 保留正確 merge base。
- `release_win.ps1` 新增 `-NoModel` 打包選項：保留 CUDA 加速函式庫，但不隨附 medium 模型（首次啟動線上下載），資料夾／ZIP 命名 `VoiceType4TW_Win_Portable_NoModel_V$Build`。
- `.github/workflows/release.yml`：push tag `v*` 觸發並發佈 Release（`workflow_dispatch` 手動觸發僅產生 artifact），建置 Lite 與 NoModel 兩版可攜 ZIP 並附 sha256 校驗檔。
- `tools/check_dependency_freshness.py` ＋ `.github/workflows/dependency-freshness.yml`：解析 `requirements-win.txt`／`requirements-cuda-win.txt`，用 PyPI JSON API 比對最新版，每月 1 日排程檢查，落後時自動開/更新維護提醒 issue。

### Changed

- **上游同步（2026-07-20）**：合併上游 `win-go-mask-202607` 分支新增的 3 個 commit（三步驟快速安裝、README 全面改寫、7 張新截圖）。`README.md` 保留本 fork 骨架，頂部整合上游「🚀 快速安裝（三步驟）」（下載連結改指向本 fork）並吸收「辨識與 AI 設定」畫面導覽段與「安裝失敗排除」章節，未引入下載販售/YouTube/贊助連結。7 張截圖與 `VERSIONS.md` 採上游版；`paths.py`／`voicetype_installer.iss` 未受影響。
- **LICENSE 全面改版為全 MIT（2026-07-20）**：上游正式補齊 MIT 授權（`jfamily4tw/voicetype4tw-mac` main 分支 commit `46346d3`）後，本 fork 的雙軌授權聲明失去存在理由，改寫為單一 MIT 授權文件（上游 MIT 全文＋本 fork 新增部分 © 2026 SanHsien 同採 MIT 條款的附加聲明）。`NOTICE.md` 授權狀態節、`README.md`／`README.en.md` 授權敘述行同步更新，`docs/DECISIONS.md` 新增決策條目記錄沿革。
- **文件全面改寫，統一稱謂（2026-07-20）**：`安裝下載教學.MD` 更名為 `安裝下載教學.md`（副檔名小寫，內容已是最新，未需配合三步驟安裝更新）；全 repo `.md` 檔逐檔檢討，移除舊有的擬人化維護者稱呼與 AI 助理自稱，統一改用中性用語（「維護者」、「Claude Code」或改寫句子），僅涉及稱謂與語氣、不動技術內容與決策語義。受影響檔案：`REVIEW.md`（Reviewer 欄與結論段落）、`docs/DECISIONS.md`、`docs/mac-mainline-absorption-analysis.md`。
- `README.md` / `README.en.md`：改寫為 Windows 專注版說明（fork 定位、安裝方式、設定欄位對照現行 `config.py`）。
- `AGENTS.md`：全面改寫——舊版內容是照「Mac 純化版 main」寫的（提及 `mlx_whisper.py`、`requirements.txt` 的 `pyobjc-*`、`pynput`、`.aicore` submodule、`openspec/`、`HANDOVER.md`/`AI_MEMORY.md` 等現已不存在的檔案/依賴），實際瀏覽現行 Windows-only 程式碼樹後重寫架構速覽、模組職責表、開發約定與硬性邊界。
- `SKILL.md`：同步更新為 Windows 版現況（怎麼跑、怎麼驗、快速定位路徑）。
- `docs/DEVELOPMENT.md`：修正大量與實際工作樹不符的殘留描述（MLX、`pynput`、`requirements.txt` 的 macOS 依賴段落、macOS 打包鏈仍需維護的說法），改為準確反映目前 Windows-only 工作樹的內容；新增「測試」章節（pytest 使用方式 + 舊測試腳本逐一處置紀錄）與目錄結構更新。
- `.gitignore`：追加 `.pytest_cache/`（新增 pytest 使用後的暫存目錄）。
- `vocab/manager.py`：本機常數 `VOCAB_DIR` 改名為 `_VOCAB_DATA_DIR`，避免與先前已移除、曾指向雲端同步目錄的死碼常數 `VOCAB_DIR`（`paths.py`）撞名混淆（REVIEW 提醒事項）。純改名不改行為。

### Fixed

- **API Key 不再進雲端同步資料夾**（`config.py`）：所有 `*_api_key` 欄位加入 `LOCAL_KEYS` 白名單，只存本機 `config_local.json`；`load_config()` 新增一次性遷移，偵測到既有使用者的 `config_global.json`（可能位於 iCloud/Google Drive/NAS 同步目錄）殘留金鑰時自動搬進本機並從全域檔移除，無感升級。設定視窗同步頁的警語文字同步修正。新增 `tests/test_config.py` 遷移與不洩漏測試。
- 網路逾時補齊：`llm/claude.py`（anthropic SDK）與 `stt/groq_whisper.py`（groq SDK）此前未設定 timeout，落回 SDK 預設 600 秒；補上統一常數 `net_config.CLOUD_REQUEST_TIMEOUT_SECONDS`（60s）。其餘 httpx/requests 呼叫點原本已各自帶合理 timeout，維持不動。新增 `tests/test_provider_timeouts.py`。
- PTT 與 VAD 全時模式互斥（`audio/mutex.py` + `ui/app.py`）：兩模式同時啟用時不再可能疊加兩路錄音——PTT 優先，按下 PTT 會捨棄進行中的 VAD 段落；PTT 錄音中的 VAD 觸發被忽略且對應音訊丟棄。新增 `tests/test_recording_mutex.py`。
- **智慧詞彙學習對本地辨識無效**（`stt/subprocess_whisper.py`）：子行程 worker 過去從未讀取 IPC 訊息的 `"prompt"` 欄位，永遠用硬編預設字串當 `initial_prompt`，詞彙庫學到的專有名詞從未真正餵進本地 Whisper。worker 迴圈改讀 `"prompt"` 欄位並轉交 `_run_transcribe()`（空/缺 fallback 回預設字串），比照 Mac 版語義（`build_vocab_prompt()` 結果取代而非串接預設 prompt）。`stt/local_whisper.py` 本來就正確接線，無需修改。新增 4 個回歸測試於 `tests/test_stt_transcribe_params.py`。
- 計算機移除 `eval()`（`actions/builtins.py`）：改用 `ast` 白名單解析（數字、`+ - * / ** % //`、括號、正負號），名稱/呼叫/屬性存取等節點一律拒絕，並限制次方指數上限；輸出格式不變，另支援 `^` 次方。新增 `tests/test_calculator.py`。
- `diagnose_mic.py` 從 macOS 空殼（Windows 上只印「Not macOS」）重寫為 Windows 實用診斷：列出輸入裝置與預設裝置、以 `audio/recorder.py` 同參數實測 0.5 秒音量、無 sounddevice 時給明確安裝指引。
- `ui/settings_window.py` 靈魂編輯區硬編碼 macOS 字型 `Monaco` 改為 Windows 內建等寬字型 `Consolas`。
- `llm/claude.py` 欄位名不一致：引擎讀 `claude_api_key`/`claude_model`，但 `DEFAULT_CONFIG` 與設定 UI 存的是 `anthropic_api_key`/`anthropic_model`——Claude 引擎因此永遠拿到空 key，`refine()` 靜默回傳原文、從未真的呼叫過 API。改以 config/UI 既有欄位名為準。已 grep 全部 LLM/STT provider 確認僅此一處同型問題，並新增 `tests/test_llm_config_keys.py`（AST 靜態掃描每個 provider 讀的 config 欄位名必須存在於 `DEFAULT_CONFIG`）防回歸。
- `AGENTS.md`/`SKILL.md` 過去宣稱「Claude Code 專屬補充見 `CLAUDE.md`」但該檔案不存在——現已補上。
- `voicetype_installer.iss`：移除引用不存在的 `platform_layer\*` 的 `Source:` 條目——Inno Setup 對缺失來源預設編譯失敗，此前打包鏈實際上是斷的；已寫檢查腳本核對其餘 12 條 `Source:` 引用全數存在。
- `stt/__init__.py`／`stt/gemini_stt.py`：STT 引擎下拉選單的「Gemini (雲端 API)」選項此前選了會靜默 fallback 成本地 Whisper（`get_stt()` 沒有對應分支）；補上分派分支，並修正 `GeminiSTT.transcribe()` 本身兩個會讓它「接上了也還是壞的」的簽章不符與 WAV bytes 重複編碼問題。新增 `tests/test_stt_engine_dispatch.py`／`tests/test_gemini_stt.py`。
- STT 幻覺過濾：win-stable 相對舊版 Mac 主線（`main`, `51094bf`）完全沒有 Whisper 常見幻覺句（「請訂閱」「感謝觀看」等 YouTube 結尾片語、長尾重複）的過濾，是功能倒退。移植出平台無關的 `stt/hallucination_filter.py`，接進 `ui/app.py:_process_audio` 的統一 STT 結果處理路徑，對本地與雲端引擎都生效。新增 `tests/test_stt_hallucination_filter.py`。
- `paths.py`：移除從未被實際使用、容易誤導的死碼常數 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`（宣告指向雲端同步目錄，但 `vocab/manager.py`/`memory/manager.py`/`stats/tracker.py` 實際上只寫本機 `APP_DATA_DIR`，兩者從未接線）。
- `stt/openrouter_stt.py`：修正與修復前 `GeminiSTT` 同型的兩個 bug——函式簽章與呼叫端 `ui/app.py` 不符（TypeError）、以及把完整 WAV bytes 用 `soundfile` 當裸 PCM 重新編碼（必定 `IndexError` 被吞掉，引擎永遠回傳空字串）。改為直接上傳原始 WAV bytes，簽章對齊 `BaseSTT`。新增 `tests/test_openrouter_stt.py`。
- STT 語言 hint 被翻譯目標語言污染：`ui/app.py:_process_audio` 此前把 `translation_lang` 直接餵給 `self.stt.transcribe(language=lang)`，使用者用過一次「翻譯成英文」後，之後所有中文錄音的 STT 語言 hint 都被污染成 `en`。比照 Mac 主線 v2.9.16（`51094bf:stt/language.py`）移植 `stt/language.py:get_transcription_language()`，STT 語言改回讀使用者實際設定的 `config["language"]`，翻譯只影響 LLM 輸出層，不干擾辨識。新增 `tests/test_stt_language_selection.py`。
- `ui/settings_window.py:_run_mic_test`：麥克風測試按鈕內有一段「非 macOS 一律拒絕」的假擋板（`if platform.system() != "Darwin": 彈窗「此診斷功能目前專為 macOS 設計」`），但擋板之後的實際測試邏輯（`sd.rec()` + numpy RMS）本來就是跨平台程式碼、錯誤訊息本來就是寫給 Windows 隱私權設定看的，擋板本身是誤植死碼——導致 Windows 使用者連按鈕都被藏起來，完全用不到一個其實能動的功能。已移除擋板並取消 Windows 隱藏。
- `paths.py`：移除從未被實際使用的死碼常數 `AI_PERMANENT_MEMORY_PATH`（指向雲端同步目錄，與先前已清掉的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 同一批，之前因不在指定範圍暫留）。

[Unreleased]: https://github.com/SanHsien/voicetype/compare/v3.1.0...HEAD
[3.1.0]: https://github.com/SanHsien/voicetype/compare/b694e40...v3.1.0
