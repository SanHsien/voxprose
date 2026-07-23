# Changelog

本檔案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，是對外快速掃描用的精簡摘要，記錄從本 fork（SanHsien）建立開發鷹架起的變更。

完整的逐版對照使用者需求與驗證證據的詳細歷史，見 [`VERSIONS.md`](VERSIONS.md)。版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

> **關於歷史 commit hash**：v3.1.0 發版時已把 fork 開發歷史 squash 成單一 commit（`84d1b28`，見 `docs/UPSTREAM.md`）。本檔與 `docs/DECISIONS.md`、`REVIEW.md` 引用的更早 hash 屬 squash 前紀錄，已不存在於 git 歷史，僅作文件內識別碼保留。

## [Unreleased]

隱私與加固審查（實機驗證前的靜態修 bug 輪）。

### Added

- **`utils/log_rotation.py`**：`debug.log`／`worker_debug.log` 改用 `RotatingFileHandler`（5MB×2 備份），修正原本無上限附加寫入會無限增長的問題。新增 `tests/test_log_rotation.py`。
- **`utils/permissions.py` 麥克風權限真實檢查**：`check_microphone()` 改讀 Windows 隱私權登錄檔，`ensure_all_permissions()` 補上啟動時的實際呼叫（過去 import 了卻從未被呼叫，是死碼）。新增 `tests/test_permissions.py`。
- **CI Python 版本矩陣**：`.github/workflows/ci.yml` 改測 3.10/3.11/3.12（比照 `pyproject.toml` 宣告範圍），過去只測 3.12。新增 `tests/test_ci_workflow.py`。

### Changed

- **正式支援 Python 3.13/3.14**：`pyproject.toml` 的 `requires-python` 由 `>=3.10,<3.13` 放寬為 `>=3.10,<3.15`；CI matrix 同步擴充為 3.10–3.14（PyPI 實查 `PyQt6`/`faster-whisper`/`ctranslate2`/`sounddevice`/`opencc-python-reimplemented` 等關鍵依賴在 Windows 上皆有 3.13/3.14 wheel）；`setup_win.bat` 的 py-launcher 偵測鏈擴充為 `3.14→3.13→3.12→3.11→3.10`。可攜包內嵌式 Python（`tools/get_portable_python.ps1`）維持 3.12 不動。本機系統 Python 3.14.6 實跑 `pytest` 全綠（326 passed, 11 skipped）作為相容性證據。詳見 `docs/DECISIONS.md`。

### Fixed

- **broad except 靜默吞噬清查**：全 repo 掃描後修正 43 處會隱藏真實錯誤的 `except`（補 log 或收窄型別），涵蓋設定檔/記憶/統計損毀時完全靜默、LLM prompt 注入失敗無痕跡等與歷史「引擎自始壞掉」同類的風險點；不改變任何 fallback 行為語義。詳見 `docs/DECISIONS.md`。新增 `tests/test_broad_except_logging.py`。

### Removed

- **keystrike 死碼清除**：移除 `paths.KEYSTRIKE_LOG_PATH`／`touch()` 佔位、`config.py` 的 `separate_keystrike_log` 死開關、`main.py` 啟動記錄、`ui/settings/general_page.py` 的勾選框與「檢視熱鍵紀錄」按鈕、`utils/diagnostics.py` 的 `keystrike.log` 收集項。推翻 `REVIEW.md` 26-4 原「決定不做」判定（主人 2026-07-23 明示指示清除），詳見 `docs/DECISIONS.md`。

### Investigated (no change)

- **keystrike.log 隱私審查**：確認 `hotkey/listener.py` 只監控使用者自訂的三個熱鍵 VK 碼、且目前無任何 handler 實際寫入 `keystrike.log`（檔案永遠是空的 touch 占位），診斷包因此不會打包到任何按鍵資料；`separate_keystrike_log` 設定開關本身也是死碼（見 `docs/DECISIONS.md`）。無隱私疑慮，未修改行為。
- **`utils/permissions.py` Windows 化**：確認早於 `b4094b7`（v2.9.6）已移除全部 macOS 專屬邏輯；本輪只補強麥克風檢查的實質功能（見上方 Added），未發現需要移除的殘留。

## [3.3.0] - 2026-07-22

上游 `jfamily4tw/voicetype4tw-mac` `main` 分支新 commit `805b007`（v2.9.18）審視完成：Apple Foundation Models 整套 macOS 專屬功能不適用（詳見 `docs/UPSTREAM.md` Skipped 表），吸收其中 3 項平台無關修正，詳見 `docs/DECISIONS.md` 2026-07-22 條目。**本輪新增驗證**：裝 `requirements-cuda-win.txt` 後 CUDA 加速確實生效（GPU 0.55s vs CPU 8.57s，約 15.6 倍），`release_win.ps1 -Lite` 端到端建置與啟動實測成功。

### Added

- **STT 後簡體→繁體轉換**：新增 `utils/zh_convert.py`，用 OpenCC `s2t` 修正 Whisper 偶爾把中文誤判成簡體輸出的問題（概念吸收自上游 `805b007` 的 `llm/apple_local.py:_to_traditional()`，獨立成不依賴 macOS 的通用後處理步驟）。新設定開關 `zh_convert_enabled`（預設 `True`）、新依賴 `opencc-python-reimplemented`，未安裝時優雅降級。新增 `tests/test_zh_convert.py`。

### Fixed

- **`vocab/manager.py` 模糊比對誤改短 ASCII 縮寫**：4 字以下純 ASCII 縮寫（STT/PTT/API）不再做模糊修正，移植自上游 `805b007` 的守衛條件。新增 `tests/test_vocab_manager.py`。

### Changed

- **`vocab/manager.py:load_all_learned_words()` 排序穩定化**：排序 key 改為 `(-count, word.casefold(), word)`，次數相同時不再依賴 dict 插入順序。移植自上游 `805b007`。

## [3.2.0] - 2026-07-22

品牌改名：中文品牌「聲成文」／英文品牌「VoxProse」，標語「自然開口，清楚成文。」同時補齊過去遺漏的署名鏈：原創作者吉米丘（Jimmy）／CC58TW → 上游 Windows 專用版維護 go-mask → 本 fork（Windows）維護 SanHsien。

**實機驗證（2026-07-21～22）**：本版是本 fork 第一次在真實 Windows 桌面環境完整跑過整條鏈路——乾淨 venv 安裝、`self_check.py` 子行程實際辨識、`diagnose_mic.py` 列出 19 個真實裝置、Windows SAPI 合成語音經真實 Whisper 引擎正確辨識出中文文字、`python main.py` 兩次啟動皆無崩潰、SettingsWindow 七分頁全數通過。過程中發現並修復 4 個真實 bug（見下方 Fixed）。

### Added

- **上游更新自動檢查**：`tools/check_upstream_updates.py` ＋ `.github/workflows/upstream-check.yml`，每週檢查上游三個追蹤分支是否有新 commit，透過 `docs/UPSTREAM.md` 的同步狀態標記區塊（JSON）記錄 `last_reviewed`/`last_merged`，有更新時開/更新 issue。新增 `tests/test_upstream_check.py`（18 個測試）。
- `docs/BRANDING.md`：記錄品牌規格與資料路徑遷移規劃。
- **`tests/test_brand_and_charset_guard.py`**：三個守門測試，防止舊品牌名稱／簡體字／原作者個人網址回流。
- **`stt/cuda_check.py`**：新增 `probe_cuda()` 共用 CUDA 加速判定函式，供 Dashboard 與 STT worker 共用同一真相源。新增 `tests/test_cuda_check.py`。

### Changed

- **資料路徑正名**：`%APPDATA%\VoiceType4TW` → `%APPDATA%\VoxProse`、`Documents\VoiceType4TW_Sync` → `Documents\VoxProse_Sync`。維護者確認本機從未有真實使用資料，不寫任何遷移/備份/fallback 邏輯，直接改常數與字面量；打包鏈與診斷 log 全部落點同步更新，實機驗證確認新路徑生效。
- **`voicetype_installer.iss` 補齊安裝版品牌**：`MyAppName`（→`VoxProse`）與 `AppId`（換發新 GUID）一併改名，等同視為新程式（本專案無既有安裝基礎，可接受）。
- **`AGENTS.md`／`SKILL.md` 雙軌授權敘述過時修正**：改為指向現況（全 MIT）。
- **視窗標題／系統匣／About 視窗／桌面捷徑品牌字串**：全面改為「聲成文」／「VoxProse」，署名鏈同步更新。
- **Windows AppUserModelID**：改為 `tw.sanhsien.VoxProse.windows`。
- **Release ZIP／安裝檔命名改用新品牌**：版本號改自 `pyproject.toml` 動態解析，不寫死。
- **版本推進 3.2.0**：`paths.py`／`pyproject.toml`／`voicetype_installer.iss` 版本號同步。
- **`main.py` 路徑重複定義消除**（純重構）：改為直接引用 `paths.APP_DATA_DIR`，實際路徑值不變。
- **全 repo 文件品牌改寫與署名補正**：`README.md` 等全部文件逐檔改寫產品自稱為「聲成文 VoxProse」，描述歷史沿革的既有事實敘述保留原名不竄改。GitHub repo 同步更名為 `SanHsien/voxprose`。
- **`ui/settings_window.py` god file 拆分**（REVIEW.md #7）：拆成 `ui/settings/` 子套件，七個分頁各一個 mixin 檔，對外契約不變。
- **`requirements-win.txt`／`requirements-cuda-win.txt` 加主版本上限鎖定**（REVIEW.md #8）。

### Fixed

- **清理 pystray 技術債殘留**（REVIEW.md #23、24-2）：`ui/menu_bar.py` 死分支與 `requirements-win.txt` 多餘依賴移除。
- **`ui/settings_window.py` 側欄 logo 重複宣告死碼**：移除未使用的重複宣告。
- **UI 品牌殘留全面清掃**：舊名「嘴炮輸入法」全數改為新品牌，`啟動嘴炮輸入法.bat` 更名為 `啟動聲成文.bat`。
- **簡體字清掃**：6 處打字疏漏修正為繁體。
- **移除原作者個人社群/贊助連結**：SNS 按鈕區塊與孤兒圖示資產移除，署名文字保留不動。
- **啟動/自檢日誌 `BUILD_ID`／`VERSION_NAME` 重複顯示**：移除多餘疊加輸出。
- **設定視窗署名鏈框架錯誤且不完整**：改為完整四層署名。
- **CUDA Dashboard 文案與實際加速行為矛盾**：抽出 `stt/cuda_check.py:probe_cuda()` 共用判定邏輯，文案改為三態。
- **`tests/test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗**：改為篩選特定呼叫，不再對總呼叫次數斷言。

## [3.1.0] - 2026-07-20

以 `win-stable` 分支 v3.0.1 為基底，建立 fork 的開發鷹架。發版工程收尾：新增 `docs/UPSTREAM.md` 上游追蹤、`release_win.ps1` `-NoModel` 打包選項、`.github/workflows/release.yml` 與 `dependency-freshness.yml` 兩條 CI workflow、`tools/check_dependency_freshness.py`，版本推進至 3.1.0。

### Added

- `LICENSE`：初版雙軌授權（上游無正式授權／SanHsien 新增部分 MIT），2026-07-20 上游補齊 MIT 後改寫為全 MIT。
- `CLAUDE.md`、`CHANGELOG.md`（本檔）、`pyproject.toml`：開發鷹架基礎文件。
- `tests/test_smoke.py`、`tests/test_config.py`：全 repo `py_compile` + 設定讀寫回圈測試。
- `.gitattributes`／`.github/workflows/ci.yml`：CRLF 規則、CI 跑 `py_compile` + `pytest`。
- **麥克風裝置選擇＋增益＋AGC**（比照 Mac 主線 v2.9.7）：`audio/recorder.py` 新增 device/gain/AGC 參數，純數學抽成 `audio/gain.py`。新增 `tests/test_audio_gain.py`。
- **錄音靜音預檢跳過 STT**（比照 Mac 主線 v2.9.7）：峰值 RMS 低於門檻即跳過整段 STT 呼叫。
- **Whisper 抗幻覺轉錄參數**（比照 Mac 主線 v2.9.13）：加入 `no_speech_threshold=0.6` + `condition_on_previous_text=False`。
- **OpenRouter fallback 鏈＋預設模型更新**（比照 Mac 主線 v2.9.16）。
- **LLM system prompt 集中化**（比照 Mac 主線 v2.9.13）：新增 `llm/prompts.py`。
- **LLM 未啟用時的輕量版靈魂規則**（比照 Mac 主線 v2.9.7）：新增 `utils/soul_rules.py`。
- **Windows 診斷包匯出**（比照 Mac 主線 v2.9.11）：新增 `utils/diagnostics.py`，一鍵打包環境資訊到桌面 zip。
- `docs/UPSTREAM.md`：記錄雙上游祖先鏈的同步狀態與檢查流程。
- `release_win.ps1` 新增 `-NoModel` 打包選項；`.github/workflows/release.yml`（Lite/NoModel 兩版）；`tools/check_dependency_freshness.py` 依賴新鮮度檢查。

### Changed

- **上游同步（2026-07-20）**：合併 `win-go-mask-202607` 分支 3 個 commit（三步驟安裝、README 改寫、7 張截圖）。
- **LICENSE 全面改版為全 MIT**：上游補齊 MIT 授權後改寫為單一授權文件。
- **文件全面改寫，統一稱謂**：移除擬人化維護者稱呼，改用中性用語。
- `README.md`／`README.en.md`／`AGENTS.md`／`SKILL.md`／`docs/DEVELOPMENT.md`：改寫為反映現行 Windows-only 工作樹的內容。
- `vocab/manager.py`：本機常數 `VOCAB_DIR` 改名為 `_VOCAB_DATA_DIR`，避免撞名混淆。

### Fixed

- **API Key 不再進雲端同步資料夾**：`*_api_key` 欄位加入 `LOCAL_KEYS`，並做一次性遷移。
- 網路逾時補齊：`llm/claude.py`／`stt/groq_whisper.py` 補上統一常數逾時。
- PTT 與 VAD 全時模式互斥：新增 `audio/mutex.py`，PTT 優先。
- **智慧詞彙學習對本地辨識無效**：worker 改讀 IPC `"prompt"` 欄位。
- 計算機移除 `eval()`：改用 `ast` 白名單解析。
- `diagnose_mic.py` 從 macOS 空殼重寫為 Windows 實用診斷。
- `ui/settings_window.py` 靈魂編輯區字型改 `Consolas`。
- `llm/claude.py` 欄位名不一致：改以 config/UI 既有欄位名為準，新增 AST 靜態掃描防回歸。
- `voicetype_installer.iss`：移除引用不存在的 `platform_layer\*`。
- `stt/__init__.py`／`stt/gemini_stt.py`：補上 Gemini 分派分支，並修正簽章與 WAV 重複編碼問題。
- STT 幻覺過濾：移植平台無關的 `stt/hallucination_filter.py`，接進統一 STT 結果處理路徑。
- `paths.py`：移除死碼常數 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`/`AI_PERMANENT_MEMORY_PATH`。
- `stt/openrouter_stt.py`：修正與 `GeminiSTT` 同型的簽章與 WAV 重複編碼 bug。
- STT 語言 hint 被翻譯目標語言污染：移植 `stt/language.py:get_transcription_language()`。
- `ui/settings_window.py:_run_mic_test`：移除誤植的「非 macOS 拒絕」假擋板。

[Unreleased]: https://github.com/SanHsien/voxprose/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/SanHsien/voxprose/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/SanHsien/voxprose/compare/b694e40...v3.1.0
