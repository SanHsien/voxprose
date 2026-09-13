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
- 依賴清單見根目錄 [`../requirements-win.txt`](../requirements-win.txt)（一般依賴）與 [`../requirements-cuda-win.txt`](../requirements-cuda-win.txt)（僅 NVIDIA GPU 需要，`setup_win.bat` 偵測 `nvidia-smi` 後才裝）。**本 repo 沒有 `requirements.txt`**（那是上游 macOS 主線的檔名，含 `pyobjc-*`/`mlx` 等 macOS 專屬套件，早已在 Windows 專用化時移除，不要新增或參考它）。**版本範圍政策**：每個套件同時宣告已支援的最低版本與主版本上限（如 `PyQt6>=6.6.0,<7`），避免安裝時靜默跨到未驗證主版；Dependabot 可提出基線更新，但必須人工審查，不可自動合併（詳見下節與 `docs/DECISIONS.md`）。

### 依賴與安全維護

- [`.github/dependabot.yml`](../.github/dependabot.yml)：每週一 06:20（Asia/Taipei）檢查兩份 requirements 與全部 GitHub Actions；CUDA、一般 Windows runtime、major 更新分組開 PR。
- [`.github/workflows/dependency-freshness.yml`](../.github/workflows/dependency-freshness.yml)：每月 1 日 10:00（Asia/Taipei）及依賴宣告推上 `main` 時執行，將 repo 版本範圍、PyPI 最新版與 open Dependabot PR 彙整到同一份報告；只有最新版超出上限、查詢失敗或仍有 open PR 時才建立／維持 issue，狀態清空後自動關閉。
- [`tools/check_dependency_freshness.py`](../tools/check_dependency_freshness.py)：只讀 repo 宣告與 PyPI JSON API，不讀目前電腦／runner 已安裝套件，因此本機與 Actions 結果一致。最新版未超出版本上限時標為「最新版未超出版本範圍」，實際安裝仍由 pip 依 Python 版本與 wheel 可用性解析相容版，不因最低支援版較舊製造永久 issue；版本上限外的新主線才標為「需評估」，但不代表可直接升級。
- [`.github/workflows/codeql.yml`](../.github/workflows/codeql.yml)：push、PR、手動及每週一排程執行 Python `security-extended` 查詢。
- GitHub repo 已啟用 Issues、vulnerability alerts、Dependabot security updates；排程提醒與安全更新 PR 才能正常運作。

本地預覽依賴報告：

```powershell
$env:PYTHONUTF8 = "1"
python tools\check_dependency_freshness.py --output dependency-freshness-report.md
```

所有依賴 PR 都要人工審查。至少確認套件 changelog、Python 3.10–3.14 的 Windows wheel 與完整 CI；涉及 PyQt6／錄音／Whisper／ONNX Runtime／CUDA／Release actions 時，另做對應真機或可攜包驗證。

## Windows 上啟動

```powershell
git clone https://github.com/SanHsien/voxprose.git
cd voxprose

py -3.12 -m venv venv
venv\Scripts\activate

pip install -r requirements-win.txt
rem 有 NVIDIA GPU 才需要下一行
pip install -r requirements-cuda-win.txt
rem requirements-win.txt 已直接宣告 onnxruntime；
rem 只有自行裁切依賴的精簡環境缺少它時才需要手動補裝：
pip install onnxruntime

python main.py
```

或直接雙擊根目錄的 `啟動聲成文.bat`（委派 `run_voicetype.bat` 挑選正確的 Python 並自動跑必要的設定，執行完會 `pause` 停留在主控台視窗方便看錯誤訊息）；一般使用者安裝走 `setup_win.bat`（自動偵測/安裝 Python、建 venv 或用內嵌 Python、裝依賴、下載模型、建捷徑，詳見根目錄該檔）。

首次啟動時 Windows 可能跳出麥克風權限提示，需允許終端機/Python 存取麥克風；若錄音無聲，先跑 `python diagnose_mic.py`（列出輸入裝置、標示預設裝置、實際開串流測 0.5 秒音量並提示 Windows 隱私權排查方向），或直接用系統設定 → 隱私權 → 麥克風排查。

### Windows 已知地雷

#### Postmortem：PyQt6 與 CUDA (faster-whisper) 初始化崩潰衝突

**症狀**：將本專案（聲成文 VoxProse，前身 VoiceType4TW）從 macOS 移植到 Windows 的過程中，當應用程式執行到載入 `faster-whisper`（底層依賴 `CTranslate2` 和 CUDA）時，Python 進程會**無任何例外或錯誤日誌**直接結束（Exit Code 1）。

**根本原因**：經過大量隔離測試與追蹤後證實，在 Windows 上如果 Python 記憶體中**優先被載入了 PyQt6 相關的動態連結庫（DLL）**（即使完全尚未宣告或實例化 `QApplication`），再進行 CUDA 模組或 GPU 相關框架的初始化，就會引發毀滅性的底層視訊驅動／OpenGL 記憶體衝突。

**解決方案**：強制作業系統的載入順序：
1. **阻擋式防禦**：在 `main.py` 的絕對第一行（環境變數設定之後），**阻擋任何 PyQt6 UI 模組的 `import`**。
2. **預先載入 STT**：判斷若為 Windows 系統，立即在主執行緒中阻塞式地呼叫 `get_stt()` 完成 CUDA 模型的掛載與預熱。
3. **延後 UI 生成**：當模型已成功掛載進記憶體後，再匯入諸如 `ui.mic_indicator` 或 `ui.menu_bar` 等包含 PyQt6 依賴的模組。
4. 在 macOS 系統上則維持原樣設計，依然可以使用非阻塞的 `QThread` 背景載入，因為 CoreML 與 Qt 在 macOS 上並無此類衝突。

因此 `stt/__init__.py` 的 `get_stt()` 在 Windows 上強制回傳 `SubprocessWhisperSTT`（獨立子行程跑模型），`ui/app.py` 的 `run()` 也會在建立/顯示 UI 前先同步預載 STT。修改啟動流程或 STT 掛載順序時務必保留此設計、嚴格遵守此載入順序。

#### 其他 Windows 特有地雷

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

- `tests/test_smoke.py`：對全 repo 每個 `.py` 檔跑 `py_compile`（擋語法/明顯匯入錯誤）；另外對不依賴 PyQt6/sounddevice/faster-whisper/各 LLM SDK 的「純邏輯模組」（`config`、`paths`、`stt.base`、`llm.base`、`vocab.manager`、`memory.manager`、`stats.tracker`、`utils.resources`、`utils.zh_convert`、`utils.foreground`）做匯入驗證；對需要選用第三方套件的模組（`stt.groq_whisper`、`llm.claude`、`llm.openai_llm`、`audio.recorder`、`ui.positions` 等）用「匯入失敗就跳過」策略，不強迫開發環境安裝全部 SDK 才能跑測試。
- `tests/test_foreground.py`：`utils/foreground.py` 的純 ctypes 前景視窗偵測（`get_foreground_process_name()`）與規則比對（`resolve_scenario_for_process()`）行為測試；真正的 Win32 DLL 函式指標存在模組層級變數 `_user32`/`_kernel32`，測試用 `monkeypatch` 整個換成 fake 物件，不需要碰 ctypes 底層即可涵蓋成功/失敗/非 Windows 各分支。
- `tests/test_soul_page_auto_scenario.py`：`ui/settings/soul_page.py` 新增的「前景視窗自動情境切換」UI 區塊 PyQt6 offscreen 煙霧測試（`QT_QPA_PLATFORM=offscreen`），只建構該 mixin 的新元件（不牽動 `SettingsWindow` 其他分頁的檔案系統存取），涵蓋啟用勾選框、規則清單新增/刪除/回填、未知情境值不被靜默丟棄。PyQt6 未安裝時用 `pytest.importorskip` 跳過而非失敗；CI 經 `requirements-win.txt` 一律有裝，仍會實跑。
- `tests/test_config.py`：`config.py` 的 `load_config()`/`save_config()` 讀寫回圈與 `LOCAL_KEYS` 拆分邏輯，用 `monkeypatch` 把 `APP_DATA_DIR`/`LOCAL_CONFIG_PATH`/`GLOBAL_CONFIG_PATH` 導向 `tmp_path`，不會碰到開發者真正的 `%APPDATA%\VoxProse\`。
- `tests/test_stt_engine_dispatch.py`：從 `ui/settings_window.py` 原始碼靜態解析 `STT_ENGINES` 清單（不 import PyQt6），驗證清單裡每個引擎值在 `stt/__init__.py:get_stt()` 都有對應的專屬分派分支（而非靜默落到平台預設分支）。重現並鎖死 REVIEW.md 記錄的「Gemini 選項選了但沒對應分支」問題。
- `tests/test_gemini_stt.py`：`stt/gemini_stt.py:GeminiSTT.transcribe()` 的行為測試（`httpx.post` 全部 monkeypatch，不打真網路）。涵蓋修復前的隱性 bug：舊版用 `soundfile.write(buf, audio_bytes, sample_rate, format="WAV")` 把呼叫端傳入的完整 WAV bytes 當作裸樣本陣列重新編碼，必定拋 `IndexError` 並被吞掉，導致這個引擎其實從未成功轉錄過。
- `tests/test_stt_hallucination_filter.py`：`stt/hallucination_filter.py:is_hallucination()` 的行為測試，從歷史（`git show 51094bf:test_stt_hallucination_filter.py`）移植原始 4 案例並新增 3 個。此邏輯現已接在 `ui/app.py:_process_audio`（STT 拿到文字之後、詞庫修正之前）的統一路徑，對所有 STT 引擎生效。
- `tests/test_openrouter_stt.py`：`stt/openrouter_stt.py:OpenRouterSTT.transcribe()` 的行為測試（`httpx.post` 全部 monkeypatch，不打真網路），比照 `tests/test_gemini_stt.py`。涵蓋修復前的同型隱性 bug（簽章不符 + WAV bytes 重複編碼導致永遠回傳空字串），並驗證呼叫端傳入的 `language` 優先於 config 預設值。

### 歷史測試腳本的處置（`git show 51094bf:<檔名>` 可撈回舊版 Mac 主線的原始內容）

上游 Mac 主線在 Windows 專用化（`v3.0.0`，見 `CHANGELOG.md`「上游繼承版本史」）時移除了根目錄全部 `test_*.py`。逐一檢查後：

| 舊檔案 | 處置 | 原因 |
|--------|------|------|
| `test_save.py` | **已移植**為 `tests/test_config.py` | 測試對象 `config.py` 仍存在且邏輯可攜，僅補上 `tmp_path` 隔離避免污染真實設定檔 |
| `test_qkey.py` | **已移植**為 `tests/manual/manual_qkey_check.py`（非 `test_*.py` 命名，pytest 不會收集） | 需要可顯示視窗環境送出合成 `QKeyEvent`，無法在無頭 CI 執行 |
| `test_stt_hallucination_filter.py` | **已移植**為 `tests/test_stt_hallucination_filter.py` | 2026-07-19 補做：原測試對象 `stt/mlx_whisper.py`（`_is_hallucination`）雖是 Apple Silicon 專屬模組，但底層過濾邏輯是純文字處理、無 MLX 相依，已抽成平台無關的 `stt/hallucination_filter.py` 並接進 `ui/app.py:_process_audio` 的統一 STT 結果處理路徑，對所有引擎生效（此前 win-stable 完全沒有等效防護，見 REVIEW.md 風險 #3） |
| `test_stt_language_selection.py` | **跳過，未移植** | 測試對象 `stt/language.py`（`get_transcription_language`）在現有 `stt/` 中不存在，語言選擇邏輯已改為直接由呼叫端傳入 |
| `test_openrouter_fallback.py` | **跳過，未移植** | 舊版 `llm/openrouter.py` 有「模型無端點時自動 fallback 到 `gemini-2.5-flash`」邏輯；現在的 `llm/openrouter.py` 已簡化為單一模型呼叫失敗即回傳原文，沒有 fallback 邏輯可測，測試會對著不存在的行為斷言 |
| `test_path.py` | **跳過，未移植** | 內容僅 `print(sys.path)`，無斷言、無測試價值，已被 `tests/test_smoke.py` 的匯入驗證取代 |

改動 STT/LLM 邏輯、設定儲存或熱鍵對應時，至少跑 `python -m pytest tests/ -v`；面向整體行為的改動（熱鍵→錄音→辨識→貼字）仍建議在 Windows 實機跑 `python main.py` 手動驗證。另有 `self_check.py`（STT 子行程實際辨識煙霧測試）與 `tests/manual/manual_stt_warmup_check.py`（確認同步 warmup 只在 worker 真正完成後返回）可用。

Windows 可攜版發佈前另須遵循下方「Windows Release 實機驗證」章節：除了
pytest／workflow，必須驗 SHA-256、ZIP CRC 與 UTF-8 中文檔名、Windows
`Expand-Archive`、runtime imports，再把真人語音、Silero/RMS 對照與前景情境
分別記為 `PASS`／`FAIL`／`BLOCKED`。

## Windows Release 實機驗證

本節是 Windows 可攜版的發佈驗證清單。目的不是只確認 workflow 顯示綠燈，
而是證明使用者下載到的 ZIP 能完整解壓、啟動，並完成語音輸入的主要路徑。

### 判定原則

- `PASS`：本次實際執行且結果符合預期。
- `FAIL`：本次實際執行且結果不符合預期；不得發佈或宣稱完成。
- `BLOCKED`：缺真人音訊、API key、硬體或其他外部條件；不得用單元測試代替。
- pytest、CI、靜態讀碼與真機操作分開記錄，不互相替代。
- API key 不貼進 issue、log、截圖或診斷包；雲端引擎只記 provider、時間與成功／失敗。

### 一、版本與自動化基線

```powershell
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
python -m pytest tests/ -v
```

記錄 commit、Python 版本、passed／skipped 數量與 skip 原因。只有
`HEAD == origin/main` 且工作樹狀態已被理解，才能把結果歸到遠端 `main`。

### 二、下載、雜湊與 ZIP 結構

以下以 `vX.Y.Z` 與 Lite 版為例：

```powershell
$VerifyRoot = Join-Path $env:TEMP "voxprose-release-verify-vX.Y.Z"
New-Item -ItemType Directory -Force -Path $VerifyRoot | Out-Null

gh release download vX.Y.Z -R SanHsien/voxprose `
  -p "ShengChengWen-Windows-Lite-vX.Y.Z.zip" `
  -p "ShengChengWen-Windows-Lite-vX.Y.Z.zip.sha256" `
  -D $VerifyRoot --clobber

$Zip = Join-Path $VerifyRoot "ShengChengWen-Windows-Lite-vX.Y.Z.zip"
$Expected = ((Get-Content "$Zip.sha256" -Raw) -split "\s+")[0].ToLowerInvariant()
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Zip).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw "SHA-256 mismatch" }

python tools\verify_release_zip.py $Zip
```

`tools/verify_release_zip.py` 會檢查：

- ZIP 可讀且全檔 CRC 正確。
- 沒有 literal `?`、Unicode replacement character 或重複 entry。
- 非 ASCII entry 有 ZIP UTF-8 flag。
- `可攜版說明.txt`、`啟動聲成文.bat`、`安裝下載教學.MD` 與四個中文情境模板各出現一次。

最後必須用 Windows 內建解壓工具做一次真實 round-trip：

```powershell
$Extract = Join-Path $VerifyRoot "expanded"
Expand-Archive -LiteralPath $Zip -DestinationPath $Extract
Get-ChildItem -LiteralPath $Extract -Recurse |
  Where-Object Name -in @(
    "可攜版說明.txt", "啟動聲成文.bat", "安裝下載教學.MD",
    "社群貼文.md", "商務回應.md", "情商大師.md", "逐字稿.md"
  ) |
  Select-Object FullName
```

少任何一個必要檔案，或 `Expand-Archive` 失敗，整個 release 即為 `FAIL`。

### 三、runtime 與麥克風預檢

在解壓後的版本目錄執行：

```powershell
.\.runtime\python.exe -c "import PyQt6, faster_whisper, sounddevice, numpy, requests, onnxruntime; print('RUNTIME_OK')"
.\.runtime\python.exe .\diagnose_mic.py
```

`diagnose_mic.py` 必須列出預設輸入裝置、成功開啟串流並完成 0.5 秒音量取樣。
只有「程式可 import」不能取代麥克風檢查。

### 四、基本語音輸入

先從 repo checkout 用解壓後版本的內嵌 Python 跑 UI 視窗 smoke check；腳本會
強制驗證實際匯入模組位於指定的 release root，並確認 Settings／About 可見、
未最小化：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$env:VOXPROSE_UI_CHECK_OUTPUT = Join-Path $VerifyRoot "ui-screenshots"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_ui_windows_check.py"
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Remove-Item Env:\VOXPROSE_UI_CHECK_OUTPUT
```

若 ZIP 內另有一層版本目錄，`$Extract` 必須改指向實際含 `ui\app.py` 與
`.runtime\python.exe` 的 package root。輸出的 `about-window.png` 不得裁字／重疊，
`settings-window.png` 應顯示完整設定頁。此腳本不代替下列真人語音操作。

再用同一份解壓後 runtime 驗證真 `QSystemTrayIcon` live state，以及「聲成文
VoxProse」／「關於」兩個可見選單 action 能分別喚回 Settings／About：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
try {
  & "$Extract\.runtime\python.exe" `
    ".\tests\manual\manual_tray_windows_check.py" --target settings
  if ($LASTEXITCODE -ne 0) { throw "Tray Settings callback 驗證失敗" }

  & "$Extract\.runtime\python.exe" `
    ".\tests\manual\manual_tray_windows_check.py" --target about
  if ($LASTEXITCODE -ne 0) { throw "Tray About callback 驗證失敗" }
} finally {
  Remove-Item Env:\VOXPROSE_SOURCE_ROOT -ErrorAction SilentlyContinue
}
```

腳本會反查 `ui/app.py` 與 `ui/tray_manager.py` 確實來自指定 release root，
並驗 `visible=True`、tooltip「聲成文」、icon 非空。PyQt 6.11 在 Windows
上若把已掛到 `QSystemTrayIcon`、但尚未顯示的 closed context menu 直接
`QAction.trigger()`，QA 程序可能 native fail-fast；那不是使用者點擊路徑。
本腳本先用 `QMenu.popup()` 顯示選單再觸發 action，避免製造假失敗。它仍不
取代真人目視通知區內實際圖示像素。

1. 雙擊 `VoxProse.exe`。
2. 在記事本或其他純文字輸入框放置游標。
3. 依目前 PTT／Toggle 設定錄音，真人說「今天天氣真好」。
4. 確認文字辨識合理、貼到原本游標處，沒有貼到 VoxProse 自己的視窗。
5. 目視系統匣圖示與「聲成文」名稱。
6. 若模型需要首次下載，等完成後重新測一次；下載中的失敗不能算語音路徑失敗。

真人未發聲、沒有可用麥克風或無法目視系統匣時，對應項目記 `BLOCKED`。

### 五、Silero VAD 與 RMS 對照

先用同一份真人音訊取得可比較的 VAD 數值證據。腳本會依序要求正常說話、
咳嗽、呼吸、環境雜音各一次；每段只錄一次，再把同一份 PCM 以產品使用的
800-sample block 同時餵給 RMS 與真 Silero。預設只保留 JSON／Markdown
指標，不保存原始錄音：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$VadReport = Join-Path $VerifyRoot "real-audio-vad.json"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_audio_vad_check.py" `
  --output $VadReport
$VadExitCode = $LASTEXITCODE
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Get-Content -LiteralPath $VadReport -Raw
if ($VadExitCode -ne 0) {
  Write-Warning "真人 VAD 對照未通過；依報告判定 FAIL 或 BLOCKED"
}
```

若 ZIP 內另有一層版本目錄，`$Extract` 同樣必須指向實際含 `audio\vad\`
與 `.runtime\python.exe` 的 package root。腳本會反查 `rms_vad.py`、
`silero_vad.py` 的實際匯入路徑；指定不完整或錯誤 root 時直接失敗，不會
退回目前 checkout 產生假 PASS。只有加上 `--keep-wav` 才會在報告同名
目錄保留四段 WAV；音訊含真人聲音，除錯結束後應依本節第八小節處置，
不得 commit 或附在公開 issue。

腳本的 `PASS` 只表示：正常說話時兩引擎皆達門檻，且三種非語音情境中
Silero 的觸發情境數嚴格少於 RMS。它提供公平數值對照，但不會操作 app 的
全時模式狀態機，也不會送 STT；因此仍要完成下列 UI／端到端操作：

1. 設定 → 辨識 AI → 語音偵測引擎，先確認 Silero 顯示「可用」。
2. 選 Silero、開啟全時模式並儲存；依提示重啟後再確認設定仍是 Silero。
3. 分別測：正常說話、單次咳嗽、呼吸聲、鍵盤／環境雜音。
4. 記錄每一種聲音是否開始錄音、是否送出辨識、是否產生文字。
5. 切回 RMS、重啟並用相同聲音與距離重測。

通過標準：兩個引擎都能辨識正常說話；RMS 行為與舊版一致；Silero 對非語音的
誤觸發明顯較少。只有 ONNX 單元測試或合成音訊數值，不能把本項轉成 `PASS`。
真人腳本若回 `BLOCKED`／`FAIL`，也不能只憑 UI 看似有反應改寫為 `PASS`。

### 六、前景視窗自動情境

先驗證設定頁實際使用的三秒 callback 不會把自己搶回前景。下列命令啟動後，
看到 `[READY]` 時在三秒內切到目標程式；只有最終列出同一個 `.exe` 才算
這一層 PASS：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$env:VOXPROSE_EXPECT_FOREGROUND = "LINE.exe"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_foreground_countdown_check.py"
$ForegroundExitCode = $LASTEXITCODE
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Remove-Item Env:\VOXPROSE_EXPECT_FOREGROUND
if ($ForegroundExitCode -ne 0) {
  throw "前景視窗倒數 callback 未取得預期程式"
}
```

可把 `LINE.exe` 換成實際目標。腳本會走
`SoulPageMixin._detect_foreground_app_for_rule()` 本身、反查 `soul_page.py`
與 `foreground.py` 確實來自 `$Extract`，並把原本會阻塞的結果訊息盒轉成
stdout。CI／桌面自動化若需要先準備再觸發，可另設
`VOXPROSE_FOREGROUND_ARM_FILE`；腳本會等該檔案出現後才開始三秒倒數，
外層必須設 timeout，避免協調檔未建立時無限等待。

這個 PASS 只證明 Win32 偵測與設定頁 callback；仍不包含 LLM 請求。接著完成：

1. 先啟用一個可用的 LLM provider，並手動選定 fallback 情境。
2. 設定 → 靈魂設定，啟用「前景視窗自動情境切換」。
3. 按「偵測目前前景程式」，倒數期間切到目標程式；成功訊息必須顯示目標
   `.exe`，不得是 `python.exe`、`VoxProse.exe` 或設定頁本身。
4. 把目標程式綁到一個輸出風格容易辨認的情境並儲存。
5. 在目標程式說一句，確認 LLM 輸出符合綁定情境。
6. 到未綁定程式說同類句子，確認回到手動選定的 fallback 情境。
7. 關閉自動情境後再測一次，確認不沿用上一次 override。

缺真 API key、未實際送出 LLM 請求，或只驗證 `get_foreground_process_name()`，
一律記 `BLOCKED`，不能算端到端通過。

### 七、結果紀錄

| 項目 | 結果 | 證據／備註 |
|---|---|---|
| HEAD 與 origin/main | PASS／FAIL | commit |
| pytest | PASS／FAIL | passed、skipped |
| SHA-256 | PASS／FAIL | asset、digest |
| ZIP validator | PASS／FAIL | entry 數、錯誤 |
| Expand-Archive | PASS／FAIL | 目的目錄 |
| runtime imports | PASS／FAIL | Python、依賴版本 |
| 麥克風預檢 | PASS／FAIL／BLOCKED | 裝置、峰值 |
| 基本語音貼字 | PASS／FAIL／BLOCKED | 目標程式、句子 |
| 系統匣 | PASS／FAIL／BLOCKED | 名稱、圖示 |
| Silero 真人音訊 | PASS／FAIL／BLOCKED | 說話／咳嗽／呼吸／雜音 |
| RMS 回歸 | PASS／FAIL／BLOCKED | 相同測試條件 |
| 前景情境命中 | PASS／FAIL／BLOCKED | process、scenario |
| 未命中 fallback | PASS／FAIL／BLOCKED | process、scenario |
| 真雲端 provider | PASS／FAIL／BLOCKED | provider；不記 key |

驗證完成後，把結論與日期回註根目錄 `REVIEW.md`；修 bug 時依 `AGENTS.md`
補上修復日期與 commit。

### 附錄：手動 UI 快速走查清單（沿用舊版 QC checklist）

不需要留存證據的快速人工勾選清單，作為上述正式驗證章節之外的輔助複查；
與第三、四節重疊的項目（PTT 錄音辨識、文字注入、系統匣圖示）不重複列出。

#### 啟動與初始化
- [ ] 模型預載時是否正確顯示「載入中」指示器？
- [ ] Dashboard 點選「首頁/Dashboard」是否能正確彈出且不遮擋原本視窗（不再 AlwaysOnTop）？

#### 語音辨識與輸入
- [ ] 靜音錄音或噪音是否會導致崩潰？（應安靜消失或提示，不應崩潰）
- [ ] 錄音中按下 Esc 或其他取消操作，流程是否正確中斷且不注入？

#### AI 潤飾與翻譯
- [ ] 切換「商務回應」、「情商大師」等情境，輸出語氣是否明顯改變？
- [ ] 開啟翻譯（英/日）時，即使有其他情境設定，是否優先翻譯為目標語文？
- [ ] AI 是否輸出「好的」、「這是您的結果」等廢話？（應嚴格禁止）
- [ ] 非翻譯模式下，輸入英文是否仍回傳繁體中文（情境需要時）？

#### 系統指令與自動化
- [ ] 說出「切換至國語模式」或「切換至商務英文」，系統設定是否即時連動變更？
- [ ] 測試「天氣」、「時間」、「計算」等內建工具指令是否正確回饋。

#### 穩定性與邊界
- [ ] 錄音中或連續快速點擊選單切換模式，是否不再發生 Access Violation 崩潰？
- [ ] 錄音後 Dashboard 的「分鐘數」與「字詞統計」是否正確累計？
- [ ] 背景待機 1 小時後，熱鍵功能是否依然靈敏？

#### 打包與部署
- [ ] `setup_win.bat` 是否成功編譯 `VoxProse.exe`？桌面捷徑（顯示名稱「聲成文」）是否指向 EXE 且圖示正確？
- [ ] 刪除 `venv`/`.runtime` 後執行 `setup_win.bat` 全流程是否通過（Python 偵測、CUDA 條件安裝、模型下載）？
- [ ] 資料是否正確寫入 `%APPDATA%\VoxProse` 而非唯讀的安裝目錄？

### 八、驗證後清理暫存目錄

只刪除本次自行建立的 `$VerifyRoot`，不要對整個 `$env:TEMP`、萬用字元或
尚未解析的環境變數執行遞迴刪除。先確認完整路徑仍位於系統暫存目錄：

```powershell
if ([System.String]::IsNullOrWhiteSpace($VerifyRoot)) {
  throw "拒絕刪除空白路徑"
}

$TrimSeparators = [char[]]@('\', '/')
$TempBase = ([System.IO.Path]::GetFullPath(
  [System.IO.Path]::GetTempPath()
)).TrimEnd($TrimSeparators)
$CleanupTarget = ([System.IO.Path]::GetFullPath($VerifyRoot)).TrimEnd($TrimSeparators)
$TempChildPrefix = $TempBase + [System.IO.Path]::DirectorySeparatorChar

if (
  $CleanupTarget.Equals(
    $TempBase,
    [System.StringComparison]::OrdinalIgnoreCase
  ) -or
  -not $CleanupTarget.StartsWith(
    $TempChildPrefix,
    [System.StringComparison]::OrdinalIgnoreCase
  )
) {
  throw "拒絕刪除非暫存子目錄：$CleanupTarget"
}

if (Test-Path -LiteralPath $CleanupTarget) {
  Remove-Item -LiteralPath $CleanupTarget -Recurse -Force
}
```

若受控自動化環境的安全政策即使在明確授權後仍攔截 `Remove-Item -Recurse`，
可在完成相同路徑邊界檢查後，以同一個 PowerShell 行程呼叫 .NET：

```powershell
if ([System.IO.Directory]::Exists($CleanupTarget)) {
  [System.IO.Directory]::Delete($CleanupTarget, $true)
}
```

刪除後用 `Test-Path -LiteralPath $CleanupTarget` 確認回傳 `False`。若驗證資料
需要留作事故證據，則不要清理，並在結果紀錄中寫明保留位置與用途。

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
│   └── manual/                # 實機手動腳本（QKey、STT warmup），不被 pytest 收集
├── assets/                    # 圖示、截圖、貼圖等 UI/文件素材
├── self_check.py / diagnose_mic.py   # 既有手動診斷腳本
├── docs/                      # 本開發文件、決策紀錄
├── pyproject.toml            # 套件 metadata + pytest 設定（不取代 requirements-win.txt）
├── CHANGELOG.md               # 版本歷史單一真相源（精簡摘要＋逐版詳細全紀錄）
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

本 fork 的工作樹來自上游 `win-stable` 分支（v3.0.1），upstream 在其 `v3.0.0`「Windows 專用版」整理中已**移除全部 macOS 專屬程式碼與打包鏈**（`setup.py`/py2app、`pack_dmg.sh`、`build_all.sh`、`stt/mlx_whisper.py`、`entitlements.plist`、`.gitmodules`/`.aicore` submodule、`requirements.txt` 的 `pyobjc-*` 依賴等 51 個檔案，詳見 `CHANGELOG.md`「上游繼承版本史」的 `v3.0.0` 條目）。若在文件或程式碼中看到對上述檔案的引用，代表文件落後於實際工作樹，應視為待修正的殘留、而非「維持原樣即可」的既有事實——本次鷹架落地（見 `docs/DECISIONS.md`）已清理 `AGENTS.md`/`SKILL.md` 中的對應殘留。macOS 版開發請直接參考原作者 repo（[`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac)）。
