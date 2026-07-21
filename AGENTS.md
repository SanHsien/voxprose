# AGENTS.md

給 Codex 與其他 AI coding agents 在本專案工作時的指引，**單一真相源**。Claude Code 專屬補充見 [`CLAUDE.md`](CLAUDE.md)（薄補丁，衝突時以本檔為準）。

## 專案宗旨

`voxprose`（聲成文 VoxProse，上游/歷史脈絡稱嘴炮輸入法 / VoiceType4TW）是本機優先的語音輸入法：按住或切換全域快捷鍵錄音，透過本地 Whisper（`faster-whisper`，CPU/CUDA）或選用雲端引擎（Groq、Gemini、OpenRouter）辨識成文字，可選經 LLM 依「三層式靈魂系統」潤飾語氣，自動貼回目前有輸入焦點的視窗。

本專案 fork 自 [`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac)（VoiceType4TW／嘴炮輸入法）的 `win-stable` 分支（v3.0.1，`win-go-mask` 主線），原作者為**吉米丘（Jimmy）**與 **CC58TW**；上游 Windows 專用版維護者為 **go-mask**（`win-go-mask-202607` 分支）。上游原生跨平台開發（macOS + Windows），**本 fork 只專注 Windows 10/11 版本的開發與改良**——目前整棵工作樹已是 Windows-only（macOS 專屬程式碼與打包鏈已在上游 `v3.0.0` 的「Windows 專用版」整理中移除，見 `VERSIONS.md`）。授權狀態見 [`NOTICE.md`](NOTICE.md)：上游已於 2026-07-20 補齊 MIT 授權，本 fork 整體採 MIT（`LICENSE`）。GitHub repo 已由維護者更名為 `SanHsien/voxprose`（原 `SanHsien/voicetype`，本機工作目錄名稱維持不變，見 `docs/DECISIONS.md`）。

## 硬性邊界

- 不移除或竄改上游對吉米丘 / CC58TW（原創作者）與 go-mask（上游 Windows 專用版維護者）的署名；見 [`NOTICE.md`](NOTICE.md)、[`README.md`](README.md)。
- 不在文件中宣稱上游程式碼有正式開源授權——見 `LICENSE` 與 `NOTICE.md` 的雙軌說明。
- 不提交 API key（Groq / OpenAI / Anthropic / Gemini / OpenRouter / Qwen / DeepSeek 等）、`config_local.json`、`config_global.json`、`sync_path.txt`、使用者 `soul.md`、`memory/*.json`、`vocab/*.json`、`audio/*.wav`、`output/*.txt`、`bundled_models/` 等本機/私密/大型資料（`.gitignore` 已涵蓋，勿反向強制加回）。
- **不破壞既有打包鏈**：`setup_win.bat`（環境建置：偵測/安裝 Python、建 venv、裝 `requirements-win.txt` + 視 GPU 裝 `requirements-cuda-win.txt`、下載 Whisper 模型、建捷徑）、`build_win.py`（PyInstaller 打包 exe）、`release_win.ps1`（自建可攜 ZIP：內嵌 Python + 全部依賴 + medium 模型）、`voicetype_installer.iss`（Inno Setup 安裝程式）——除非任務明確要求，不修改這些檔案；改動 `main.py`/`paths.py`/`config.py` 的路徑或啟動邏輯時，必須確認不會讓這條鏈斷掉。
- **Windows 上 PyQt6 與 CUDA 的載入順序有致命衝突**（見 `windows_cuda_qt_crash_postmortem.md`）：`main.py` 透過 `stt/__init__.py` 的 `get_stt()` 在 Windows 上強制走 `SubprocessWhisperSTT`（獨立子行程跑 CTranslate2/faster-whisper，避免與同行程的 PyQt6 事件迴圈衝突）。修改啟動流程或 STT 掛載方式時，**不要**把 Whisper 模型改回與 PyQt6 同行程載入。

## 架構速覽

```text
全域熱鍵 (hotkey/listener.py，純 ctypes 輪詢 Windows API，無 pynput/跨平台分支)
        │ 按住 (PTT) 或切換 (Toggle)
        ▼
錄音 (audio/recorder.py，sounddevice) ──▶ STT (stt/get_stt()：Windows 強制走 subprocess_whisper.py
        │                                    子行程隔離；或 groq/gemini/openrouter 雲端引擎)
        │                                              │
        │                              [llm_enabled] LLM 潤飾 (llm/：依 soul/ 三層靈魂組 prompt)
        ▼                                              │
main.py → ui.app.VoiceTypeApp(QObject) 協調 ◄───────────┘
        │
   ┌────┼─────────────┬─────────────┐
   ▼    ▼             ▼             ▼
output/injector.py  ui/ (PyQt6)   actions/ 分派   vocab/ + memory/ + stats/
（貼回焦點視窗+剪貼簿）（選單列/浮動按鈕/浮動指示/設定視窗）（語音指令/魔術語）（詞彙學習/長期記憶/統計）
```

### 模組職責（實際瀏覽現有程式碼後歸納，非上游文件抄錄）

| 模組 | 職責 |
|------|------|
| `main.py` | 進入點；設定 Windows 專屬 crash-proofing 環境變數（`KMP_DUPLICATE_LIB_OK`、`MKL_THREADING_LAYER=SEQUENTIAL`、`TQDM_DISABLE` 等）→ 初始化 `paths`/logging/faulthandler → `from ui.app import VoiceTypeApp; app = VoiceTypeApp(); app.run()` |
| `ui/app.py` | `VoiceTypeApp(QObject)`：真正的協調者，建構 `TextInjector`、`MicIndicator`、`AudioRecorder`、`ActionManager`、`FloatingButton`、`VoiceTypeMenuBar`、`TrayManager`、`HotkeyListener`；`run()` 內在 Windows 上同步（阻塞式）預載 STT 模型後才建立/顯示 UI，避免 PyQt6/CUDA 載入順序衝突 |
| `config.py` | `load_config()` / `save_config()`；`DEFAULT_CONFIG` 是所有欄位預設值；`LOCAL_KEYS` 白名單為不隨雲端同步的機器特定設定（熱鍵、STT 引擎、UI 相關、麥克風自動觸發參數等） |
| `paths.py` | `APP_DATA_DIR`（`%APPDATA%\VoiceType4TW`）、`SYNC_BASE_DIR`（可指標重定向的雲端同步目錄）、版本號 `VERSION_NAME`/`BUILD_ID`、`initialize_paths()`（建目錄、舊版資料搬遷、真可攜版 `bundled_models/` 首次安裝） |
| `stt/` | `base.py`（`BaseSTT` 抽象）、`__init__.py` 的 `get_stt()` 依 `stt_engine` 設定與平台分流；`subprocess_whisper.py`（Windows 專用，子行程隔離跑 `faster-whisper`）、`local_whisper.py`（非 Windows 或直接呼叫時用，同樣走 `faster-whisper`）、`groq_whisper.py`、`gemini_stt.py`、`openrouter_stt.py`；**沒有 `mlx_whisper.py`／`language.py`**（macOS 專屬與舊版語言選擇邏輯已在 Windows 專用化時移除） |
| `llm/` | `base.py`（`BaseLLM` 抽象）+ 7 個供應商實作：`claude.py`、`openai_llm.py`、`gemini.py`、`ollama.py`、`openrouter.py`、`qwen.py`、`deepseek.py`；**沒有 `minimax.py`／集中式 `prompts.py`**（system prompt 目前內嵌於 `ui/app.py` 的 `DEFAULT_LLM_PROMPT`/`DEFAULT_ASSISTANT_PROMPT`，各引擎 `refine(text, prompt)` 直接吃呼叫端傳入的 prompt） |
| `ui/` | PyQt6：`app.py`（協調者）、`menu_bar.py`（`VoiceTypeMenuBar`）、`tray_manager.py`（`TrayManager`，系統匣選單）、`mic_indicator.py`（浮動錄音狀態指示）、`floating_button.py`（可拖曳的浮動觸發按鈕）、`positions.py`（視窗位置記憶，純邏輯+`paths`，無 PyQt6 相依）、`settings_window.py`（設定視窗，含各分頁 UI）、`about_window.py`；**沒有 `vocab_editor.py`**（未使用的 tkinter 死碼已移除） |
| `hotkey/` | `listener.py`：`HotkeyListener` 純 Windows 實作，`start()` 直接呼叫 `_start_windows()`，以 `ctypes.windll.user32` 輪詢按鍵狀態；**沒有跨平台分支、不依賴 `pynput`**（與舊版 Mac 文件描述不同） |
| `actions/` | `dispatcher.py`（`ActionManager.dispatch()`）+ `builtins.py`：語音指令/魔術語觸發的內建動作（天氣、時間、開網頁、計算機等） |
| `soul/` | 三層式靈魂系統的內建範本：`scenario/`（情境模板：`default.md`、商務回應、情商大師、社群貼文、逐字稿）、`format/`（輸出格式：email、formal_doc、natural、slides、social_post）；使用者實際靈魂資料另存於 `paths.SYNC_BASE_DIR/soul/`（不進版控），首次執行由 `paths._initialize_data()` 複製內建範本 |
| `vocab/` | `manager.py`：使用者自訂詞彙 + 出現次數達門檻自動學習，供 STT `initial_prompt` 使用 |
| `memory/` | `manager.py`：長期記憶（新增/查詢/週期性濃縮存檔/刪除單筆），供 LLM 潤飾時取得上下文 |
| `audio/` | `recorder.py`（`AudioRecorder`，`sounddevice` 錄音）、`auto_trigger.py`（`AutoTriggerController`，VAD 全時自動觸發，免按鍵） |
| `output/` | `injector.py`（`TextInjector`：貼回目前焦點視窗並存入剪貼簿） |
| `stats/` | `tracker.py`：語音輸入時長、字數等使用統計 |
| `utils/` | `branding.py`（`init_windows_id()`/`apply_branding()`，Windows AppUserModelID 與品牌套用）、`permissions.py`（權限檢查，內容仍偏 macOS 導向，Windows 上多為 no-op）、`resources.py`（`get_resource_path()`，處理 PyInstaller 打包後的資源路徑） |
| `tools/` | `doctor.py`（`setup_win.bat` 呼叫的環境診斷）、`download_models.py`（Whisper 模型下載）、`get_portable_python.ps1`（下載嵌入式 Python）、`launcher.cs`（C# 原生 launcher exe 原始碼，`setup_win.bat` 用內建 `csc.exe` 現場編譯） |
| `tests/` | 自動化 pytest 測試（本次鷹架新增，見下方「測試」）；`tests/manual/` 放需要可顯示視窗環境的手動腳本 |
| `self_check.py` / `diagnose_mic.py` | 手動診斷腳本（前者驗證 STT 子行程實際可辨識、非 pytest 案例；後者已重寫為 Windows 麥克風診斷：列出輸入裝置與預設裝置、實測 0.5 秒音量並提示隱私權排查方向） |

## 開發約定

- **Windows 為唯一開發與執行環境**：不要假設或新增 macOS 專屬 API（`AppKit`/`Quartz`/`py2app`/`pyobjc-*`）——這些在目前工作樹中已不存在，`hotkey/listener.py`、`stt/__init__.py` 均已是 Windows-only 實作，沒有跨平台分支需要維護。
- **不動打包鏈**：`setup_win.bat`、`build_win.py`、`release_win.ps1`、`voicetype_installer.iss`、`tools/get_portable_python.ps1`、`tools/launcher.cs` 除非任務明確要求，不修改。
- **依賴管理**：實際安裝以 `requirements-win.txt`（一般依賴）+ `requirements-cuda-win.txt`（NVIDIA GPU 才需要，`setup_win.bat` 偵測 `nvidia-smi` 後才裝）為準；本次新增的 `pyproject.toml` 只提供 metadata 與 `pytest` 設定，**不取代**這兩個 `requirements-*.txt`，也不要讓開發者改成 `pip install -e .` 當作唯一安裝方式。
- **Windows 已知地雷**：見根目錄 `windows_cuda_qt_crash_postmortem.md`——PyQt6 DLL 若先於 CUDA/`faster-whisper` 載入會導致無訊息崩潰（Exit Code 1），因此 Windows 上 STT 一律走獨立子行程（`stt/subprocess_whisper.py`）而非與 UI 同行程；另有右 Alt 鍵可能被系統回報為 `alt_gr` 而非 `alt_r`、`ToolTip` 視窗類型在 Windows 需改用 `Tool | FramelessWindowHint | WindowStaysOnTopHint`、中文字型需強制指定（如 `Microsoft JhengHei`）等已記錄地雷。改動 `main.py` 開頭的環境變數設定或 STT 掛載順序時務必重讀此文件。
- **驗證方式**：`tests/` 內為可自動執行的 pytest 案例（`python -m pytest tests/ -v`）；`self_check.py`、`diagnose_mic.py`、`tests/manual/manual_qkey_check.py` 是需要真實硬體/可顯示視窗環境的手動腳本，不會被 pytest 收集。面向整體行為（熱鍵→錄音→辨識→貼字）的改動，建議另外在 Windows 實機執行 `python main.py` 手動驗證。
- **設定變更**：新增 `config.py` 的 `DEFAULT_CONFIG` 欄位時，同時考慮是否要加進 `LOCAL_KEYS`（機器特定、不同步的設定）。
- **語言與風格**：維護文件用繁體中文；程式碼/變數命名維持英文，既有中英混用註解沿用既有風格，不強制統一。
- **修 bug 必回註 REVIEW.md（適用所有 AI agent：Claude、Codex、Gemini 等，維護者 2026-07-19 指示，常態慣例）**：每修復 `REVIEW.md` 列出的問題，必須回到 `REVIEW.md` 對應項目（風險表「修復狀態」欄或對應章節）標註修復 commit hash 與日期；修復過程中額外發現並修掉的 bug，也要補註進 REVIEW.md 的修復回註區。REVIEW.md 維持 latest-only，但修復狀態必須跟上現況——不得讓 review 持續陳列已解決的問題而不標註。
- **「上游更新檢查」issue 出現時的處理流程（適用所有 AI agent）**：`.github/workflows/upstream-check.yml` 每週跑 `tools/check_upstream_updates.py`，發現上游有新 commit 時會開/更新一個「上游更新檢查」issue。收到這種 issue 後：(1) 逐筆讀 commit 內容，判斷是否適用本 fork 的 Windows 樹；(2) **採用**——走一般 merge/cherry-pick 流程，完成後更新 `docs/UPSTREAM.md` 同步狀態標記區塊的 `last_merged` 與 `last_reviewed`；(3) **不採用**——只推進同步狀態標記區塊的 `last_reviewed`（不動 `last_merged`），**同時**在 `docs/UPSTREAM.md`「Skipped（審視後未採用）」表補一列（分支／commit／標題／審視日期／未採用理由），並在 `docs/DECISIONS.md` 記一句理由。`last_reviewed` 只負責「這次不用再提醒」，Skipped 表才負責「不失憶」——兩件事缺一不可，否則日後想回頭查「當初為什麼跳過」會查無所獲。

## 驗證方向

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements-win.txt
# 有 NVIDIA GPU 才需要：
pip install -r requirements-cuda-win.txt

python main.py                      # 實際啟動，手動測熱鍵/錄音/貼字
python -m pytest tests/ -v          # 自動化測試（詳見 docs/DEVELOPMENT.md）
python self_check.py                # 手動：STT 子行程實際辨識煙霧測試（需下載/已有模型）
```

不接受「應該可以」——面向行為的改動需要跑 `pytest tests/` 或在 Windows 實機手動驗證，兩者缺一不可視改動範圍而定。

## 文件入口

- [`README.md`](README.md) / [`README.en.md`](README.en.md)：使用者入口、功能介紹（中文為主）。
- [`CLAUDE.md`](CLAUDE.md)：Claude Code 專屬薄補丁。
- [`CHANGELOG.md`](CHANGELOG.md)：Keep a Changelog 格式的精簡對外摘要（本 fork 起點開始記）。
- [`VERSIONS.md`](VERSIONS.md)：既有的「開發版本全紀錄」，逐版詳細需求對照與驗證證據，比標準 CHANGELOG 更完整，兩者並存、各司其職。
- [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)：環境需求、Windows 啟動、測試、目錄結構。
- [`docs/DECISIONS.md`](docs/DECISIONS.md)：本 fork 的決策紀錄。
- [`NOTICE.md`](NOTICE.md)：來源、授權查證結果與第三方聲明。
- [`SKILL.md`](SKILL.md)：AI agent 快速上手索引。
- [`REVIEW.md`](REVIEW.md)：最新一次專案覆核（latest-only），風險表附「修復狀態」欄——修 bug 後必須回註（見「開發約定」）。
- `windows_cuda_qt_crash_postmortem.md`：Windows PyQt6/CUDA 崩潰案例與修法（既有文件）。
- `pyproject.toml`：套件 metadata 與 `pytest` 設定（本次新增，補足自動化測試骨架）。
