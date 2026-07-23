# Development

維護者與 AI 接手用的開發文件：環境需求、Windows 啟動、測試、目錄結構。使用者入口在根目錄 [`README.md`](../README.md) / [`README.en.md`](../README.en.md)；AI 協作規則在 [`../AGENTS.md`](../AGENTS.md)；決策紀錄在 [`DECISIONS.md`](DECISIONS.md)；授權查證在 [`../NOTICE.md`](../NOTICE.md)。

## 架構

```text
全域熱鍵 (hotkey/listener.py，純 Windows：ctypes.windll.user32 輪詢，無 pynput/跨平台分支)
        │ 按住錄音 (PTT) 或切換 (Toggle)
        ▼
錄音 (audio/recorder.py, sounddevice)
        │
        ▼
STT 辨識 (stt/get_stt()：Windows 上強制走 subprocess_whisper.py 子行程隔離跑 faster-whisper，
          避免與 PyQt6 同行程載入衝突；或 groq_whisper／gemini_stt／openrouter_stt 走雲端 API)
        │
        ▼（llm_enabled 時）
LLM 潤飾 (llm/：呼叫端組好 prompt（含 soul/ 的情境模板 + 格式決定）後傳入所選供應商的 refine(text, prompt))
        │
        ▼
輸出 (output/injector.py：貼回目前有輸入焦點的視窗，同時存入剪貼簿)
```

`main.py` 只負責環境層級的 crash-proofing（設定 `KMP_DUPLICATE_LIB_OK`/`MKL_THREADING_LAYER`/`TQDM_DISABLE` 等環境變數、Windows 專屬的 branding 初始化、`faulthandler`/logging 設定），實際的協調者是 `ui/app.py` 的 `VoiceTypeApp(QObject)`：建構 `TextInjector`/`MicIndicator`/`AudioRecorder`/`ActionManager`/`FloatingButton`/`VoiceTypeMenuBar`/`TrayManager`/`HotkeyListener`，`run()` 內在 Windows 上同步（阻塞式）預載 STT 模型後才顯示 UI（見下方「Windows 已知地雷」）。

### 模組（詳細職責見 [`../AGENTS.md`](../AGENTS.md) 的架構速覽表）

| 模組 | 一句話 |
|------|--------|
| `stt/` | STT 引擎抽象與各實作（本地 Whisper 子行程、Groq、Gemini、OpenRouter；**沒有 MLX**） |
| `llm/` | 可選 LLM 潤飾引擎：Ollama/OpenAI/Anthropic(Claude)/Gemini/OpenRouter/Qwen/DeepSeek（**沒有 Minimax、沒有集中式 `prompts.py`**，system prompt 內嵌於 `ui/app.py`） |
| `ui/` | PyQt6 選單列、系統匣、浮動按鈕、浮動錄音指示、設定視窗、關於視窗、視窗位置記憶（**沒有詞彙編輯器 `vocab_editor.py`**，已移除的 tkinter 死碼） |
| `hotkey/` | **純 Windows** 全域熱鍵監聽：`ctypes.windll.user32` 輪詢按鍵狀態，無跨平台分支、不依賴 `pynput` |
| `actions/` | 語音指令/魔術語觸發的動作分派 |
| `soul/` | 三層式靈魂系統模板（情境 `scenario/`、格式 `format/`） |
| `vocab/` | 使用者詞彙 + 自動學習，供 STT `initial_prompt` |
| `memory/` | 長期記憶週期性濃縮 |
| `audio/` | 錄音（`recorder.py`）+ 全時自動觸發 VAD（`auto_trigger.py`） |
| `output/` | 文字注入目前焦點視窗 |
| `stats/` | 使用統計 |
| `utils/` | Windows branding（`branding.py`）、權限檢查（`permissions.py`，內容偏 macOS 導向、Windows 上多為 no-op）、PyInstaller 資源路徑（`resources.py`） |
| `tools/` | `doctor.py`（環境診斷）、`download_models.py`、`get_portable_python.ps1`、`launcher.cs`（`setup_win.bat` 打包鏈用） |

## 環境需求

- **Windows 10/11（本 fork 唯一開發與執行環境）**：Python 3.10–3.14，建議搭配 NVIDIA GPU 以使用 CUDA 加速 `faster-whisper`（無 GPU 則自動退回 CPU）。
- 本工作樹**沒有 macOS 程式碼**（見下方「關於 macOS」）；上游 macOS 版本請直接參考原作者 repo。
- 依賴清單見根目錄 [`../requirements-win.txt`](../requirements-win.txt)（一般依賴）與 [`../requirements-cuda-win.txt`](../requirements-cuda-win.txt)（僅 NVIDIA GPU 需要，`setup_win.bat` 偵測 `nvidia-smi` 後才裝）。**本 repo 沒有 `requirements.txt`**（那是上游 macOS 主線的檔名，含 `pyobjc-*`/`mlx` 等 macOS 專屬套件，早已在 Windows 專用化時移除，不要新增或參考它）。**主版本上限鎖定**：兩份 requirements 檔案每個套件都同時宣告下限與主版本上限（如 `PyQt6>=6.6.0,<7`），避免 `pip install` 未來靜默抓到不相容的新主版；下限維持既有值不變，上限依 `tools/check_dependency_freshness.py` 查得的當時 PyPI 最新版本鎖下一主版（詳見 `docs/DECISIONS.md`）。

## Windows 上啟動

```powershell
git clone https://github.com/SanHsien/voxprose.git
cd voxprose

py -3.12 -m venv venv
venv\Scripts\activate

pip install -r requirements-win.txt
rem 有 NVIDIA GPU 才需要下一行
pip install -r requirements-cuda-win.txt
rem 想試全時模式的 Silero VAD 引擎（vad_engine="silero"）才需要下一行——
rem 選用依賴，未裝時全時模式優雅降級回 RMS，見 audio/vad/silero_vad.py
pip install onnxruntime

python main.py
```

或直接雙擊根目錄的 `啟動聲成文.bat`（委派 `run_voicetype.bat` 挑選正確的 Python 並自動跑必要的設定，執行完會 `pause` 停留在主控台視窗方便看錯誤訊息）；一般使用者安裝走 `setup_win.bat`（自動偵測/安裝 Python、建 venv 或用內嵌 Python、裝依賴、下載模型、建捷徑，詳見根目錄該檔）。

首次啟動時 Windows 可能跳出麥克風權限提示，需允許終端機/Python 存取麥克風；若錄音無聲，先跑 `python diagnose_mic.py`（列出輸入裝置、標示預設裝置、實際開串流測 0.5 秒音量並提示 Windows 隱私權排查方向），或直接用系統設定 → 隱私權 → 麥克風排查。

### Windows 已知地雷

詳見根目錄 [`../windows_cuda_qt_crash_postmortem.md`](../windows_cuda_qt_crash_postmortem.md)（既有文件），重點：

- **PyQt6 與 CUDA 載入順序衝突**：若 PyQt6 的 DLL 先於 CUDA/`faster-whisper` 載入，Windows 上會無任何例外訊息直接 Exit Code 1。因此 `stt/__init__.py` 的 `get_stt()` 在 Windows 上強制回傳 `SubprocessWhisperSTT`（獨立子行程跑模型），`ui/app.py` 的 `run()` 也會在建立/顯示 UI 前先同步預載 STT。修改啟動流程或 STT 掛載順序時務必保留此設計。
- **右 Alt 鍵**：不同鍵盤語系下系統可能將其回報為 `alt_gr` 而非 `alt_r`，`hotkey/listener.py`（純 ctypes 輪詢，無 `pynput`）的按鍵對應需手動處理。
- **ToolTip 視窗置頂**：`Qt.WindowType.ToolTip` 在 Windows 未必置頂，浮動指示視窗改用 `Tool | FramelessWindowHint | WindowStaysOnTopHint` 組合。
- **中文字型**：Windows 上 PyQt6 未必預設套用美觀黑體，需強制設定字型（如 `Microsoft JhengHei`）。

## 設定

`config.py` 的 `DEFAULT_CONFIG` 是所有設定欄位的預設值來源，實際運行時的值儲存在兩個檔案（皆不進版控，見 `.gitignore`，路徑在 `%APPDATA%\VoxProse\`）：

- 本機設定 `config_local.json`（`LOCAL_KEYS` 白名單：熱鍵、STT 引擎、全時模式偵測參數、麥克風設定等，不隨雲端同步）。
- 全域設定 `config_global.json`（其餘欄位，例如各 LLM 供應商的 API key、啟用的引擎；可透過 `paths.py` 的同步指標檔 `sync_path.txt` 在多台機器間共用）。

新增設定欄位時，同步考慮是否要加進 `LOCAL_KEYS`——機器特定、不該同步的欄位（例如熱鍵、麥克風增益）才需要加入。

## 測試

本專案現在有 `pyproject.toml`（`[tool.pytest.ini_options]`：`testpaths = ["tests"]`、`pythonpath = ["."]`）與 `tests/` 目錄，可用標準 pytest 一鍵跑：

```powershell
pip install pytest   # 或 pip install -e ".[dev]"（pyproject.toml 的 dev extra）
python -m pytest tests/ -v
```

- `tests/test_smoke.py`：對全 repo 每個 `.py` 檔跑 `py_compile`（擋語法/明顯匯入錯誤）；另外對不依賴 PyQt6/sounddevice/faster-whisper/各 LLM SDK 的「純邏輯模組」（`config`、`paths`、`stt.base`、`llm.base`、`vocab.manager`、`memory.manager`、`stats.tracker`、`utils.resources`、`utils.zh_convert`）做匯入驗證；對需要選用第三方套件的模組（`stt.groq_whisper`、`llm.claude`、`llm.openai_llm`、`audio.recorder`、`ui.positions` 等）用「匯入失敗就跳過」策略，不強迫開發環境安裝全部 SDK 才能跑測試。
- `tests/test_config.py`：`config.py` 的 `load_config()`/`save_config()` 讀寫回圈與 `LOCAL_KEYS` 拆分邏輯，用 `monkeypatch` 把 `APP_DATA_DIR`/`LOCAL_CONFIG_PATH`/`GLOBAL_CONFIG_PATH` 導向 `tmp_path`，不會碰到開發者真正的 `%APPDATA%\VoxProse\`。
- `tests/test_stt_engine_dispatch.py`：從 `ui/settings_window.py` 原始碼靜態解析 `STT_ENGINES` 清單（不 import PyQt6），驗證清單裡每個引擎值在 `stt/__init__.py:get_stt()` 都有對應的專屬分派分支（而非靜默落到平台預設分支）。重現並鎖死 REVIEW.md 記錄的「Gemini 選項選了但沒對應分支」問題。
- `tests/test_gemini_stt.py`：`stt/gemini_stt.py:GeminiSTT.transcribe()` 的行為測試（`httpx.post` 全部 monkeypatch，不打真網路）。涵蓋修復前的隱性 bug：舊版用 `soundfile.write(buf, audio_bytes, sample_rate, format="WAV")` 把呼叫端傳入的完整 WAV bytes 當作裸樣本陣列重新編碼，必定拋 `IndexError` 並被吞掉，導致這個引擎其實從未成功轉錄過。
- `tests/test_stt_hallucination_filter.py`：`stt/hallucination_filter.py:is_hallucination()` 的行為測試，從歷史（`git show 51094bf:test_stt_hallucination_filter.py`）移植原始 4 案例並新增 3 個。此邏輯現已接在 `ui/app.py:_process_audio`（STT 拿到文字之後、詞庫修正之前）的統一路徑，對所有 STT 引擎生效。
- `tests/test_openrouter_stt.py`：`stt/openrouter_stt.py:OpenRouterSTT.transcribe()` 的行為測試（`httpx.post` 全部 monkeypatch，不打真網路），比照 `tests/test_gemini_stt.py`。涵蓋修復前的同型隱性 bug（簽章不符 + WAV bytes 重複編碼導致永遠回傳空字串），並驗證呼叫端傳入的 `language` 優先於 config 預設值。

### 歷史測試腳本的處置（`git show 51094bf:<檔名>` 可撈回舊版 Mac 主線的原始內容）

上游 Mac 主線在 Windows 專用化（`v3.0.0`，見 `VERSIONS.md`）時移除了根目錄全部 `test_*.py`。逐一檢查後：

| 舊檔案 | 處置 | 原因 |
|--------|------|------|
| `test_save.py` | **已移植**為 `tests/test_config.py` | 測試對象 `config.py` 仍存在且邏輯可攜，僅補上 `tmp_path` 隔離避免污染真實設定檔 |
| `test_qkey.py` | **已移植**為 `tests/manual/manual_qkey_check.py`（非 `test_*.py` 命名，pytest 不會收集） | 需要可顯示視窗環境送出合成 `QKeyEvent`，無法在無頭 CI 執行 |
| `test_stt_hallucination_filter.py` | **已移植**為 `tests/test_stt_hallucination_filter.py` | 2026-07-19 補做：原測試對象 `stt/mlx_whisper.py`（`_is_hallucination`）雖是 Apple Silicon 專屬模組，但底層過濾邏輯是純文字處理、無 MLX 相依，已抽成平台無關的 `stt/hallucination_filter.py` 並接進 `ui/app.py:_process_audio` 的統一 STT 結果處理路徑，對所有引擎生效（此前 win-stable 完全沒有等效防護，見 REVIEW.md 風險 #3） |
| `test_stt_language_selection.py` | **跳過，未移植** | 測試對象 `stt/language.py`（`get_transcription_language`）在現有 `stt/` 中不存在，語言選擇邏輯已改為直接由呼叫端傳入 |
| `test_openrouter_fallback.py` | **跳過，未移植** | 舊版 `llm/openrouter.py` 有「模型無端點時自動 fallback 到 `gemini-2.5-flash`」邏輯；現在的 `llm/openrouter.py` 已簡化為單一模型呼叫失敗即回傳原文，沒有 fallback 邏輯可測，測試會對著不存在的行為斷言 |
| `test_path.py` | **跳過，未移植** | 內容僅 `print(sys.path)`，無斷言、無測試價值，已被 `tests/test_smoke.py` 的匯入驗證取代 |

改動 STT/LLM 邏輯、設定儲存或熱鍵對應時，至少跑 `python -m pytest tests/ -v`；面向整體行為的改動（熱鍵→錄音→辨識→貼字）仍建議在 Windows 實機跑 `python main.py` 手動驗證，另有 `self_check.py`（STT 子行程實際辨識煙霧測試）可用。

## 目錄結構

```text
.
├── main.py                   # 進入點；設定 crash-proofing 環境變數後交給 ui.app.VoiceTypeApp
├── config.py                 # 設定載入/儲存
├── paths.py                  # 資料目錄、版本號、路徑解析
├── stt/ llm/ ui/ hotkey/ actions/ soul/ vocab/ memory/ audio/ output/ stats/ utils/
│                            # 功能模組（見上方「模組」表與 AGENTS.md）
├── tools/                   # doctor.py／download_models.py／get_portable_python.ps1／launcher.cs（setup_win.bat 用）
├── tests/                    # pytest 自動化測試（test_smoke.py／test_config.py）
│   └── manual/                # 需視窗環境的手動腳本（manual_qkey_check.py），不被 pytest 收集
├── assets/                    # 圖示、截圖、貼圖等 UI/文件素材
├── self_check.py / diagnose_mic.py   # 既有手動診斷腳本
├── docs/                      # 本開發文件、決策紀錄
├── pyproject.toml            # 套件 metadata + pytest 設定（不取代 requirements-win.txt）
├── CHANGELOG.md / VERSIONS.md # 精簡對外摘要 / 逐版詳細全紀錄
├── .github/workflows/ci.yml  # GitHub Actions：windows-latest，py_compile + pytest 子集
├── .gitattributes             # eol 規則（.bat/.cmd/.ps1 強制 CRLF）
├── AGENTS.md / CLAUDE.md      # AI 協作規則
├── NOTICE.md / LICENSE        # fork 來源、授權查證、雙軌授權聲明
├── README.md / README.en.md  # 使用者入口
├── setup_win.bat / run_voicetype.bat / release_win.ps1 / build_win.py / voicetype_installer.iss
│                            # Windows 環境建置與打包鏈（不隨意修改，見 AGENTS.md 硬性邊界）
└── 啟動聲成文.bat          # Windows 啟動捷徑
```

## 關於 macOS（本工作樹已無 macOS 程式碼）

本 fork 的工作樹來自上游 `win-stable` 分支（v3.0.1），upstream 在其 `v3.0.0`「Windows 專用版」整理中已**移除全部 macOS 專屬程式碼與打包鏈**（`setup.py`/py2app、`pack_dmg.sh`、`build_all.sh`、`stt/mlx_whisper.py`、`entitlements.plist`、`.gitmodules`/`.aicore` submodule、`requirements.txt` 的 `pyobjc-*` 依賴等 51 個檔案，詳見 `VERSIONS.md` 的 `[v3.0.0]` 條目）。若在文件或程式碼中看到對上述檔案的引用，代表文件落後於實際工作樹，應視為待修正的殘留、而非「維持原樣即可」的既有事實——本次鷹架落地（見 `docs/DECISIONS.md`）已清理 `AGENTS.md`/`SKILL.md` 中的對應殘留。macOS 版開發請直接參考原作者 repo（[`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac)）。
