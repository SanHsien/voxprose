# VoiceType4TW 開發版本全紀錄 (面向物件分析)

本檔案用於精確紀錄「使用者需求」與「實際變更」的對照，並連結至 Git 提交與備份紀錄。最新版本置頂。

---

## [V3.1.0] - 2026-07-20 (SanHsien Fork Release, BUILD-3100-STABLE)
> 本版把 SanHsien fork 自建立以來的全部工程成果（鷹架、bug 修復、Mac 功能吸收、發版工程）收斂為一個正式版本，供後續 squash 為單一 v3.1.0 commit 前的最終狀態。

### 開發鷹架（比照 sticker-forge / gpt-ai-assistant 範本）
- 新增 `CHANGELOG.md`（Keep a Changelog 精簡摘要）、`pyproject.toml`（套件 metadata + pytest 設定）、`.github/workflows/ci.yml`（windows-latest 全 repo `py_compile` + `pytest`）、`.gitattributes`（`.bat`/`.cmd`/`.ps1` 強制 CRLF）。
- `tests/`：`test_smoke.py`（全 repo compile + 純邏輯模組匯入）、`test_config.py`（隔離 `%APPDATA%` 的讀寫回圈）、`manual/manual_qkey_check.py`（需視窗環境的手動腳本，不被 pytest 收集）。

### Mac 主線功能吸收（依 `docs/mac-mainline-absorption-analysis.md` 逐項比對，v2.9.7 ~ v2.9.16）
- 麥克風裝置選擇＋手動增益＋AGC＋錄音靜音預檢跳過 STT（`audio/recorder.py`、`audio/gain.py`）。
- Whisper 抗幻覺轉錄參數（`no_speech_threshold`、`condition_on_previous_text=False`）與平台無關的 `stt/hallucination_filter.py`（此前 win-stable 完全沒有此過濾，是功能倒退補回）。
- OpenRouter fallback 鏈＋預設模型更新（`google/gemini-2.5-flash`）、LLM system prompt 集中化（`llm/prompts.py`）、LLM 未啟用時的輕量版靈魂規則（`utils/soul_rules.py`）。
- Windows 診斷包匯出（`utils/diagnostics.py`，一鍵打包環境資訊/裝置清單/日誌尾段/設定摘要）。
- STT 語言 hint 不再被翻譯目標語言污染（移植 `stt/language.py:get_transcription_language()`）。

### Bug 修復（15+ 項，詳細清單見 `CHANGELOG.md` [3.1.0] 段）
- API Key 不再誤存進雲端同步資料夾（`config.py` `LOCAL_KEYS` 白名單 + 一次性遷移）。
- 網路逾時補齊（`net_config.CLOUD_REQUEST_TIMEOUT_SECONDS`）、PTT 與 VAD 全時模式互斥（`audio/mutex.py`）。
- 智慧詞彙學習對本地辨識無效（`stt/subprocess_whisper.py` worker 未讀 IPC `"prompt"` 欄位）。
- 計算機移除 `eval()`，改用 `ast` 白名單解析。
- `llm/claude.py` API Key 欄位名不一致（引擎讀 `claude_*`，設定存 `anthropic_*`），Claude 引擎過去永遠靜默回傳原文。
- `stt/gemini_stt.py` / `stt/openrouter_stt.py`：STT 引擎分派缺分支＋簽章不符＋WAV bytes 重複編碼，兩引擎過去接上也是壞的。
- `ui/settings_window.py:_run_mic_test`：移除「非 macOS 一律拒絕」的誤植死碼擋板，Windows 麥克風測試功能其實一直能動只是被藏起來。
- `paths.py` 死碼常數清理（`VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`/`AI_PERMANENT_MEMORY_PATH`，指向雲端同步目錄但從未接線）。
- `voicetype_installer.iss` 修正引用不存在的 `platform_layer\*` 來源（打包鏈此前實際上是斷的）。

### 授權與上游同步
- LICENSE 全面改版為全 MIT：上游 `jfamily4tw/voicetype4tw-mac` main 分支正式補齊 MIT 授權（commit `46346d3`）後，本 fork 雙軌授權聲明收斂為單一 MIT 文件。
- 併入上游 `win-go-mask-202607` 分支（三步驟快速安裝、README 全面改寫、7 張新截圖），merge commit 保留正確祖先鏈。
- 新增 `docs/UPSTREAM.md`：記錄雙上游祖先鏈（`win-stable` @ `b694e40`、`win-go-mask-202607` @ `e5ddc02`、Mac 主線分岔點 `51094bf`）同步狀態與檢查流程。

### 發版工程
- `release_win.ps1` 新增 `-NoModel` 選項（保留 CUDA、不隨附 medium 模型）。
- `.github/workflows/release.yml`：push tag `v*` 建置 Lite/NoModel 兩版可攜 ZIP 並發佈 Release（含 sha256）；`workflow_dispatch` 手動觸發僅產生 artifact。
- `tools/check_dependency_freshness.py` ＋ `.github/workflows/dependency-freshness.yml`：每月排程檢查 `requirements-win.txt`/`requirements-cuda-win.txt` 是否落後，落後自動開/更新 issue。
- 版本推進：`paths.py`（`VERSION_NAME`/`BUILD_ID`）、`pyproject.toml`、`voicetype_installer.iss`（`MyAppVersion`/`OutputBaseFilename`）五處版本字串同步至 `3.1.0`/`BUILD-3100-STABLE`。

### 驗證
- `python -m pytest tests/ -v` 全綠（見 CI/本機驗證紀錄）。
- `release_win.ps1` 通過 PowerShell 語法解析與 `-NoModel` 邏輯乾跑驗證；兩條新 workflow YAML 語法通過 `yaml.safe_load` 驗證；`check_dependency_freshness.py` 本機實跑成功（含 PyPI 查詢）。

---

## [win-go-mask v3.0.1] - 2026-07-08 (True Portable Release, BUILD-3010-STABLE)
> 2026-07-08 起，`win-go-mask-202607` 正式作為 Windows 主線來源，推進 `win-stable`。

### 真可攜版：解壓即用 ZIP 打包系統
- **`release_win.ps1` 全面改寫**：從「複製現有 .runtime」改為**自建完整可攜環境**——在 `dist/` staging 內下載嵌入式 Python 3.12、安裝全部依賴（Full 版含 CUDA）、隨附 medium 模型（`bundled_models/`）、放入 Starter EXE（無現成檔會用內建 csc 現場編譯）、生成「可攜版說明.txt」、`tar.exe`（ZIP64）壓縮。版本號自動從 paths.py 讀取。`-Lite`（無 CUDA 無模型）與 `-SkipZip` 參數。
- **`paths.py` 隨附模型自動安裝**：`initialize_paths()` 新增 `_install_bundled_models()`——解壓即用時 launcher 看到 `.runtime` 就緒會直接啟動 App（跳過 setup 的模型安裝），因此 App 首次啟動自行把 `bundled_models/` 複製進 `%APPDATA%`，已存在則跳過。
- **編碼修正**：`release_win.ps1` 與 `get_portable_python.ps1` 改存 UTF-8 with BOM（Windows PowerShell 5.1 讀無 BOM UTF-8 會以 ANSI 解碼，中文內容曾使 here-string 解析炸裂）。
- **實測**：runtime imports 驗證（RUNTIME_OK）、**從可攜資料夾直接啟動 App 成功**（進程確認跑在 `dist\...\.runtime\pythonw.exe`，V3.0.1 banner、零錯誤、STT worker 模型載入）、隨附模型安裝邏輯單元測試（新裝/已存在跳過/無 bundle 無動作）、產出 `VoiceType4TW_Win_Portable_V3010.zip`（約 4.1GB）。

---

## [v3.0.0] - 2026-07-07 (Windows Edition, BUILD-3000-STABLE)
### 正式定義為 Windows 專用版：移除全部 macOS 遺留
- **51 個檔案移除**（git 歷史保留完整可回溯）：
  - macOS 打包鏈：`setup.py` (py2app)、`pack_dmg.sh`、`pack_release.sh`、`build_all.sh`、`install.sh`、`fix_installed_app.sh`、`fix_dmg_icon.py`、`fix_pack_dmg.py`、`set_dmg_icon.py`、`post_build_fix*.py` (mlx)、`entitlements.plist`、`嘴炮輸入法.command`
  - macOS 文件：`首次開啟必看_解除損毀警告.md` (Gatekeeper)、`MIGRATION_GUIDE.md` (macOS 開發機指南)
  - macOS 程式碼：`stt/mlx_whisper.py`（Apple Silicon MLX 引擎，`stt/__init__.py` 同步移除分支）、`open_settings.py` (rumps 備援)、`ui/vocab_editor.py`（無人引用的 tkinter 死碼）
  - 過時/未引用：`setup.iss`（已被 voicetype_installer.iss 取代）、`requirements.txt` (mac 依賴)、`.gitmodules`（子模組不存在）、DMG 背景圖 ×4、mac 時代截圖 ×8、未註冊字型 11 個、`icon.icns` 等未引用圖示
- **文件改寫**：README 定位為 Windows 專用版（註明 macOS 版在原作者 repo）、設定表更新為現行實際欄位（含全時模式參數）、手動安裝僅留 Windows；QC 清單改為 Windows 專用（打包段改為 Starter EXE／乾淨安裝驗證）；.gitignore 移除 mac 項目。
- **驗證**：全模組編譯通過、實機啟動煙霧測試無錯誤。

---

## [v2.9.10] - 2026-07-07 (Settings UI Refinements, BUILD-2991-STABLE)
### 各分頁細節修正（依使用者實測回饋）
- **勾選框全域可辨識**：QCheckBox 指示器原本與深色背景溶在一起，現在未勾選有明顯灰框、勾選為品牌紫底白勾——影響辨識AI（啟用高階智慧潤飾）、詞彙記憶（注入 LLM 記憶）、系統設定（偏好設定全部）。
- **辨識AI**：「AI 魔術指令與展示選項」改名「AI 魔術指令」，移除下方過時提示小字。
- **靈魂設定**：「在 Finder 中打開資料夾」在 Windows 顯示為「從檔案總管開啟資料夾」，並修正實際功能——原本呼叫 macOS 的 `open` 指令在 Windows 上無效，改用 `os.startfile`（並先確保資料夾存在）。
- **詞彙記憶**：「刪除」「壓縮本週記憶」按鈕高度 32→40px，不再裁切文字；長期記憶新增「刪除選取」（單筆刪除，摘要列可清除摘要，歸檔備份不受影響），`memory/manager.py` 新增 `delete_entry(ts)` 與 `clear_summary()`。
- **署名**：協助開發者改為 Claude Code（側欄、關於視窗、README）。

---

## [v2.9.9] - 2026-07-07 (Dashboard UI Overhaul, BUILD-2990-STABLE)
### 設定視窗版面重整（修正元件截斷與過期狀態）
- **模型偵測路徑修正（真 bug）**：Dashboard 的 `_is_model_present` 原本查 `~/.cache/huggingface/hub`，但程式實際下載到 `%APPDATA%/VoiceType4TW/whisper_models`——導致模型裝好了燈號仍全灰、「模型下載進度」卡永遠顯示。現在兩個路徑都查，Medium 綠燈正確亮起、下載卡自動隱藏。
- **截斷根治**：Dashboard 頁改為 QScrollArea（與其他頁一致）——內容超過視窗高度時捲動，不再被 Qt 硬壓縮成文字重疊。
- **版面設計**：側欄 300→240px、視窗最小 1080×720（預設 1200×840）、三張資訊卡等寬、卡片標題統一 13px 灰、統計數字放大至 26px、中文標題改品牌紫、卡片間距與內距統一。
- **文案修正**：側欄版本字串去除重複的 BUILD ID；「顯示顯示浮動按鈕」錯字；運行狀態卡新增「全時模式」開關狀態顯示。
- **驗證**：離屏渲染 1190×970 與最小 1080×720 截圖檢查，無任何元件截斷或重疊；系統設定頁同步驗證。

---

## [v2.9.8] - 2026-07-07 (Roadmap Features, BUILD-2980-STABLE)
### 全時自動觸發 + 多螢幕位置記憶（INTERNAL_TODO 兩項 Roadmap 完成）
- **🎤 全時模式（免按鍵自動觸發）**：新增 `audio/auto_trigger.py` VAD 控制器——常駐低成本音訊串流，以 RMS 遲滯偵測自動切分語音段落（300ms 前導緩衝防切頭、實際講話短於 0.4s 的雜音自動丟棄、60s 安全上限），段落經單一 worker 佇列依序送入既有 STT/LLM 管線，確保連續講話輸出順序正確。浮動選單新增開關；`auto_trigger_sensitivity`/`auto_trigger_silence_sec` 可於 config_local.json 微調（屬本機設定不同步）。PTT/Toggle 熱鍵路徑完全不受影響。
- **📍 多螢幕位置記憶**：MicIndicator 現在可拖曳，與浮動按鈕一樣記住使用者在「每個螢幕」的偏好停靠位置（存於獨立的 ui_positions.json，避免被設定視窗的過期快照覆蓋）；跨解析度變更會自動 clamp 回可視範圍。Indicator 依然跟隨滑鼠所在螢幕，浮動按鈕重啟後回到上次停靠的螢幕與位置。
- **實測**：VAD 狀態機單元測試（正常段落／短雜音丟棄／低噪不觸發）、位置存取與 clamp 單元測試、實機啟動掛載 USB 麥克風 20 秒無誤觸發、與熱鍵監聽共存無衝突。

---

## [v2.9.7] - 2026-07-07 (Windows Install Hardening, BUILD-2970-STABLE)
### 安裝流程強化與 Starter EXE（端對端實測通過）
- **啟動 BAT 修復**：`啟動嘴炮輸入法.bat` 原本直接呼叫系統 `python`（繞過 venv/.runtime，多數機器直接失敗），改為委派 `run_voicetype.bat`；內容改純 ASCII，根除 cmd 編碼亂碼。
- **Python 偵測加固**：`setup_win.bat` 逐一實測 `py -3.12` → `-3.11` → `-3.10`（原本盲信 `py -3.12`）；`python` 指令驗證版本範圍並排除 Microsoft Store 假捷徑；全不符則自動下載可攜式 Python。
- **CUDA 條件安裝**：NVIDIA 套件拆到 `requirements-cuda-win.txt`，偵測到 `nvidia-smi` 才安裝；無獨顯機器省約 800MB。
- **Doctor 放寬**：網路不通、路徑含中文改為警告不中止安裝；報告寫入失敗不再自爆。
- **Starter EXE（INTERNAL_TODO #1）**：新增 `tools/launcher.cs`，`setup_win.bat` 以 Windows 內建 csc 就地編譯 `VoiceType4TW.exe`（本機編譯無 SmartScreen 問題），桌面捷徑優先指向 EXE（無黑窗、無編碼問題）。
- **補齊漏列依賴**：`requests`（ollama 引擎啟動即需）、`soundfile`、`anthropic`、`openai`、`groq`（切換雲端引擎即需）。
- **winget 免管理員**：移除 `--scope machine`。
- **專案治理**：建立 git 版控；17 個殘留 log 與 12 個一次性測試腳本歸檔至 `archive/`；README 對齊新安裝行為。
- **實測**：乾淨環境端對端安裝（py launcher 3.11 降級鏈、GPU CUDA 路徑、模型下載、EXE 編譯、捷徑建立）＋ EXE 啟動實測（LLM/STT 引擎載入、熱鍵監聽、無崩潰）全數通過。

---

## [v2.8.2] - 2026-03-04 19:00 (Stable Release)
### 全功能同步與對齊 (Full Parity)
- **旗艦功能對齊**：同步 Mac 版的高精度「處理耗時顯示」與「執行日誌系統」。
- **API Key 預檢機制**：增加強健性檢查，若 API Key 未填將在 MicIndicator 顯示紅色警告，防止測試閃退。
- **雙層設定架構 (Double-Layer Config)**：
  - `config_local.json`：存放熱鍵、硬體特定設定（不參與同步）。
  - `config_global.json`：存放 API Keys、Prompt（參與同步）。
- **NAS 指標同步**：實作 `sync_path.txt` 目錄重定向，支援 NAS 私密靈魂同步。
- **穩定性修補**：移除 PC 版過時的 `CONFIG_PATH` 依賴。

---

## [v2.8.1-dev] - 2026-03-04 11:15 (Cloud Sync Handover)
### 🚀 跨平台同步開發
- **核心實作**：
  - `paths.py`：實作 `get_sync_base_dir()` 透過指標重定向資料目錄。
  - `config.py`：實作 `LOCAL_KEYS` 白名單，正式拆分 Local 與 Global 設定。
- **UI 強化**：新增 [☁️ 雲端同步] 專屬分頁，支援遷移與連結 NAS 目錄。

---

## [v2.8.0] - 2026-03-03 18:30 (Official PC Release B19)
### 核心穩定性與瀏覽器解禁
- **瀏覽器輸入修復 (B19)**：徹底移除針對瀏覽器的注入攔截，實現全網頁通用輸入。
- **極簡托盤選單 (B16)**：將模式與情境選擇移至浮動按鈕，托盤僅保留基礎設定。
- **浮動按鈕切換 (B18)**：支援使用者自定義開啟/關閉浮動按鈕 UI。
- **啟動防護與穩定性**：解決了 Windows 下的 OpenMP 衝突與 Pystray 死鎖，Build 躍升至 B19。

---

## [v2.7.32 B15] - 2026-03-03 15:00 (Tray Sync Fix)
- **托盤選單修復**：解決 Windows 下儲存設定後圖示選單更新失敗的问题。

---

## [v2.7.32 B14] - 2026-03-03 14:20 (Log Cleanup)
- **日誌淨化**：改進層級控制，關閉 Debug 時不再輸出大量熱鍵日誌。

---

## [v2.7.32 B8-B13] - 2026-03-03 (Security & UX Polish)
- **B13 (Hotfix)**：修正 SettingsWindow 崩潰。
- **B12 (Separate Log)**：實作 `keystrike.log` 職責分離。
- **B11 (Dynamic Prefix)**：前綴改為動態的情境名稱。
- **B10 (Build ID System)**：引入 `paths.py` 硬編碼 Build ID 追蹤。
- **B8-B9 (Memory Sync)**：引入 `<Draft>` XML 標籤保護與 `AI_MEMORY.md` 雙層架構。

---

## [v2.7.32 B7] - 2026-03-03 10:00 (Prompt Alignment)
- **Prompt 結構優化**：規則前置、資料後置。強制半形括號 `[]` 與標點符號風格鎖定。

---

## [v2.7.32 B2-B6] - 2026-03-03 09:00 (Flagship Features)
- **B6 (NameError Fix)**：修復 Demo 模式變數遺漏。
- **B5 (Format Fix)**：校準 `[底層靈魂]` 標籤格式。
- **B4 (UI Alignment)**：整合 Demo 控制項至系統設定頁。
- **B2-B3 (Scenario Loop)**：實作遍歷所有性格的測試模式並優化選單勾選。

---

## [v2.7.32 beta] - 2026-03-02 22:00 (Windows Porting Start)
- **啟動加強**：強制 `KMP_DUPLICATE_LIB_OK=TRUE`。
- **導入優化**：採用延遲導入 (Lazy Import) 避免重複依賴。
- **路徑重組**：將資料路徑導向 `%APPDATA%/VoiceType4TW`。

---

## [v2.7.24-pc-stable] - 2026-03-01 18:00 (Stable Base)
- **Windows 初心版**：建立能在 PC 穩定執行的環境基準，包含 Inno Setup 安裝配置。
