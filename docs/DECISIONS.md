# Decisions

本專案（fork）的重要決策紀錄（新到舊）。每筆記：日期、決定、理由。與 [`DEVELOPMENT.md`](DEVELOPMENT.md) 的「怎麼做」互補，這裡記「為什麼」。

> **關於歷史 commit hash**：v3.1.0 發版時 fork 開發歷史已 squash 成單一 commit（`84d1b28`）。本檔引用的更早 hash 屬 squash 前的開發過程紀錄，已不存在於 git 歷史，僅作文件內識別碼保留。

## 2026-07-23 — v3.4.0 Release ZIP 中文檔名損毀與發佈 gate

- **事故**：GitHub v3.4.0 的 Lite／NoModel workflow 顯示成功，但 Lite 資產實際無法由 Windows `Expand-Archive` 解壓。中央目錄有 7 個中文檔名被寫成 literal `?`：3 個根目錄說明／啟動檔與 4 個 `soul/scenario` 情境模板。
- **根因**：`release_win.ps1` 用 Windows `tar.exe -a` 建 ZIP。bsdtar 的 Windows ZIP 路徑經系統 ANSI code page，且未設定 ZIP UTF-8 filename flag；繁中 CP950 主機會留下未標示編碼的 raw bytes，英文 GitHub runner 則在壓縮當下把無法表示的中文字逐字替換成 ASCII `0x3F`。workflow 的 `PYTHONUTF8`／`PYTHONIOENCODING` 只影響 Python，對 native `tar.exe` 無效。
- **修法**：改用 .NET `ZipArchive` 並指定 `Encoding.UTF8`；保留頂層 release 目錄，ZIP64 由 .NET 自動處理。以 65,536 entries 實包確認 ZIP64 EOCD／locator 存在，Windows PowerShell 5.1 路徑亦實建成功。
- **防回歸**：新增 `tools/verify_release_zip.py`，在 hash／artifact upload／Release 發佈前檢查 CRC、重複 entry、literal `?`／replacement character、非 ASCII UTF-8 flag，以及 7 個必要中文資源。完整操作方式與 `PASS`／`FAIL`／`BLOCKED` 判定見 `docs/RELEASE_VERIFICATION.md`。
- **實證**：原 GitHub Lite 資產（236,740,232 bytes，SHA-256 `84b7adf693d2234a7be7fa3482404d4567eca13a7ddc951a35d617544d6101b5`）validator 必然失敗；修正版 Lite（240,477,115 bytes）共 16,279 entries、全檔 CRC 通過、7 個中文資源皆有 UTF-8 flag，Windows `Expand-Archive` 完整成功且 7 檔 hash 與 staging 相同。
- **發佈判定**：workflow 綠燈不再等同 release 可用。既有 v3.4.0 資產仍是壞包；在修正版正式發佈前，不得把 v3.4.0 標記為完整收官。

## 2026-07-23 — 前景視窗感知的情境模板自動切換（`docs/REFERENCES.md` 調研項目落地）

維護者核准實作 `docs/REFERENCES.md` 調研的第二個大型功能（概念來自 Wispr Flow）：依「當下正在打字的應用程式」自動套用對應的三層靈魂系統情境模板，取代目前完全手動的系統匣切換。本功能發佈時標記「🔍 待實機驗證」（見 `REVIEW.md` 27-2），由維護者之後統一驗證真實使用情境（在不同應用程式間切換錄音）。

- **偵測方式（純 ctypes，不加依賴）**：新增 `utils/foreground.py`，`GetForegroundWindow()` → `GetWindowThreadProcessId()` → `OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION)` → `QueryFullProcessImageNameW()` 取得前景視窗所屬程序的執行檔名稱（如 `OUTLOOK.EXE`）。刻意不用 `psutil`——現有 `hotkey/listener.py`、`utils/permissions.py` 等 Windows 專屬模組都是純 `ctypes.windll`，沒有理由為這個功能破例加新依賴。DLL 函式指標存在模組層級變數 `_user32`/`_kernel32`（而非函式內區域變數），讓測試可以整個換掉 mock 物件而不必碰 ctypes 底層，見 `tests/test_foreground.py`。任何失敗（非 Windows、抓不到前景視窗、Win32 呼叫失敗）一律回傳 `None`，絕不拋例外。
- **偵測時機：只在錄音開始那一刻，不輪詢**：`ui/app.py._detect_auto_scenario()` 在 `_on_start()`（PTT/toggle）與 `_on_auto_segment_start()`（VAD 全時模式，且未被 PTT/VAD 互斥擋下時）各呼叫一次，取代原本「常駐監看前景視窗」的方案——本 app 設計為不搶焦點，前景視窗天然就是使用者正在打字的目標視窗，錄音中途切換視窗不應該讓已經在錄的這一段語音情境「漂移」，故只在起始點採樣一次、整段沿用。
- **套用語義：只影響「這一次」，不覆寫手動設定**：命中規則時，`_session_scenario_override`（app 實例上的暫存值，非 config）覆蓋 `_get_effective_scenario()` 的回傳值，供 `_process_audio()`／`_apply_basic_soul_rules()`／`_build_llm_prompt()` 三處讀取；**完全不寫回 `config["active_scenario"]`**——這是「最不意外」的語義：使用者手動在系統匣選定的情境是持久狀態，不該被一次自動偵測悄悄覆蓋。未啟用功能、偵測失敗、或無規則命中，`_get_effective_scenario()` fallback 回 `config.get("active_scenario", "default")`，與功能存在之前行為位元級一致（既有 363 個測試全綠即為證據——這個改動沒有動到任何既有測試斷言）。若 LLM 未啟用，情境模板本來就只在 LLM 潤飾階段被讀取，故此功能自然無效果，README/UI 文案均已提及。
- **規則比對語義（決定並測死，見 `tests/test_foreground.py::test_resolve_*`）**：`resolve_scenario_for_process()`——不分大小寫；規則鍵可省略 `.exe` 副檔名（`"outlook"` 與 `"outlook.exe"` 都能比對到 `proc_name="OUTLOOK.EXE"`），降低使用者手動輸入規則時的挫折感；規則字典為空或 `proc_name` 為空一律回傳 `None`；多筆規則同時命中時取字典插入順序中第一筆（對應設定頁列表由上到下的順序）。
- **`LOCAL_KEYS` 決定：兩個新設定都不列入（隨全域/雲端同步）**：`auto_scenario_enabled` 性質上與既有的 `active_scenario`／`llm_enabled`（皆非 `LOCAL_KEYS`）同類——是使用者的工作流程偏好，不是機器特定設定（不像熱鍵、麥克風增益那樣「換一台機器就該重設」）；`auto_scenario_rules` 是使用者精心維護的「應用程式→情境」規則表，換到另一台裝置時延續使用才是預期行為，比照 `active_scenario` 的同步邏輯。
- **UI（`ui/settings/soul_page.py`）**：靈魂設定頁在既有分頁下方新增「🪟 前景視窗自動情境切換」區塊——啟用勾選框＋`QTableWidget` 規則清單（程式檔名／情境模板下拉，選項來源與 `ui/menu_bar.py` 手動情境選單一致：`"default"` + `SOUL_SCENARIO_DIR` 底下所有 `*.md` 檔名）、新增/刪除列按鈕、「偵測目前前景程式」按鈕。偵測按鈕的已知限制——按下當下前景視窗就是設定視窗本身——採 3 秒倒數（`QProgressDialog`，比照既有麥克風測試按鈕的 UX 慣例）：提示使用者切到目標視窗，倒數結束才真正呼叫 `get_foreground_process_name()`，避免每次都測到「聲成文設定」自己。已用 PyQt6 offscreen 模式（本機系統 Python 3.14.6 + 新裝 `PyQt6==6.11.0`）驗證：獨立 mixin 建構（不牽動其他分頁的檔案系統存取）、勾選狀態、規則新增/刪除、既有規則回填、未知情境值不被靜默丟棄、完整 `SettingsWindow()` 端到端建構＋`_save_action`/`refresh_config` 資料流手動腳本驗證皆通過，見 `tests/test_soul_page_auto_scenario.py`。
- **本機真實偵測驗證（非 mock，真 Windows）**：`python -c "from utils.foreground import get_foreground_process_name; print(get_foreground_process_name())"` 實際回傳 `'LINE.exe'`（當時前景應用程式），證明 ctypes 呼叫鏈在這台機器上確實能取得真實前景程式執行檔名稱。
- **未驗證邊界**：真人在不同應用程式間切換並實際錄音，驗證情境確實依規則切換且輸出內容套用正確的 LLM 情境 prompt；PyInstaller 打包後 ctypes.windll 呼叫鏈是否受影響（理論上不會，`hotkey/listener.py` 已是同類用法且打包後正常運作，但本次未重新驗證打包鏈）。

## 2026-07-23 — Silero VAD 全時模式引擎（`docs/REFERENCES.md` 調研項目落地）

維護者核准實作 `docs/REFERENCES.md` 調研的大型功能：Silero VAD 作為全時模式（`audio/auto_trigger.py`）的選用語音偵測引擎，取代/輔助現行 RMS 能量+遲滯門檻判斷。本功能發佈時標記「🔍 待實機驗證」（見 `REVIEW.md` 27-1），由維護者之後統一驗證真人麥克風場景。

- **架構（介面抽象，RMS 行為位元級不變）**：新增 `audio/vad/` 套件——`base.py`（`BaseVAD` 抽象介面，只定義 `compute_level(indata) -> float` 一個方法＋`reset()`）、`rms_vad.py`（把 `auto_trigger.py` 原本內嵌的 RMS 公式逐行搬移包裝，無任何數值調整）、`silero_vad.py`（onnxruntime 版）、`__init__.py`（`get_vad_engine(engine)` 工廠函式＋`describe_silero_availability()`）。`auto_trigger.py` 的 hysteresis/`min_speech_sec`/`max_segment_sec` 狀態機完全不動，只把原本內嵌的 RMS 算式換成呼叫 `self._vad.compute_level(indata)`——因為 RMS 與 Silero 的輸出天然都落在 0~1 尺度，`auto_trigger_sensitivity`/`auto_trigger_silence_sec` 的門檻語義不必因引擎切換而改變，使用者既有設定不需重學。
- **決定（後端用 onnxruntime，不用 torch）**：torch 完整安裝約 2GB，塞不進可攜打包版；onnxruntime CPU 版只有數十 MB，模型本身（ONNX 版）約 2.3MB。
- **依賴決策校正（同日實包覆核）**：原判斷只看「能否在 `requirements-win.txt` 直列同一個 onnxruntime 版本區間」，漏看 `faster-whisper` 本身已宣告 `onnxruntime>=1.14,<2`。pip 會依 Python 3.10-3.14 各自解析有相容 wheel 的版本，不需要五個 Python 共用同一 wheel。實際 Python 3.14 開發環境取得 onnxruntime 1.26.0，修正版 Python 3.12 Lite runtime 取得 1.27.0。不過 `audio/vad/silero_vad.py` 會直接 import 此套件，依「直接 import 就直接宣告」原則，現已在 `requirements-win.txt` 明列 `onnxruntime>=1.14,<2`；這是相容範圍而非單一版本 pin。缺席時 fallback RMS 的防禦行為維持不變。
- **決定（模型來源：首次使用時下載，釘住穩定 tag 而非 vendor 進 repo）**：模型來源查證用 `gh api repos/snakers4/silero-vad/...`，確認 `src/silero_vad/data/silero_vad.onnx`（2,327,524 bytes，MIT）在 `v6.2.1`（最新 release tag，2026-02-24）存在且可下載；下載 URL 釘住這個 tag（而非 `master` 分支），避免上游更新造成不可預期的行為變化。下載到 `%APPDATA%\VoxProse\models\silero_vad.onnx`，比照 `tools/download_models.py` 的 Whisper 模型下載模式（首次使用觸發，不進版控）。權衡：vendor 進 repo 可省一次網路請求，但要多一份 2.3MB 二進位檔案入 git 歷史；選擇下載模式與既有 Whisper 模型的使用者心智模型一致（設定頁已經有「模型未下載」的三態文案先例），故不 vendor。
- **真模型實測（scratchpad `venv_real`，Python 3.11.15 + onnxruntime 1.27.0，非 mock）**：
  - 下載驗證：`ensure_model_downloaded()` 對真實 `%APPDATA%\VoxProse\models\` 執行，實際下載 2,327,524 bytes（與 GitHub API 回報的 blob size 一致），首次下載 1.135s。
  - 推論介面查證（**第一版實作的 bug，經真模型測出**）：`InferenceSession.get_inputs()/get_outputs()` 顯示 `input(float32[N,N])`/`state(float32[2,N,128])`/`sr(int64[])` → `output(float32[N,1])`/`stateN`；第一版只餵純 512 樣本窗口，跑起來不報錯，但真實語音音檔（scratchpad SAPI 合成 WAV）機率始終貼近 0（`max=0.0029`），跟純靜音/雜音幾乎無法區分——比對官方 `utils_vad.py:OnnxWrapper.__call__`（`gh api` 抓 `v6.2.1` 版本）發現 v5/v6 系列模型每步驟實際吃「上一步驟最後 64 樣本(context) + 這一步驟新的 512 樣本」共 576 樣本，不是單純 512。補上 context 前綴（`CONTEXT_SAMPLES=64`，`audio/vad/silero_vad.py`）後才恢復正常判別力。
  - 修正後數字（2 秒靜音／2 秒白雜音／4 段 SAPI 合成語音，全部經 `AutoTriggerController` 同款 50ms/800 樣本 block 餵入）：靜音 `max=0.0089 mean=0.0041`；雜音 `max=0.0418 mean=0.0092`；語音（`tts_normal.wav`）`max=1.0000 mean=0.7823`（77% 的 block 機率 >0.5）、`tts_um_sentence.wav` `mean=0.7391`、`tts_um_triple.wav` `mean=0.5104`、`tts_um_long.wav` `mean=0.3140`——語音與靜音/雜音有數量級差距，判別力明確。
  - 端到端：把 `tts_normal.wav`（+1 秒尾端靜音）以 `AutoTriggerController._callback()` 逐 block 餵入（`vad_engine="silero"`），`on_segment_start` 觸發 1 次、`on_segment_stop` 觸發 1 次、輸出 116,844 bytes 非空 WAV（`min_speech_sec` 門檻正常判定為有效語音，可送 STT）。
- **驗證產物清理**：真模型測試過程中一度誤觸發 `SettingsWindow._save_action()` 把 `vad_engine="silero"` 寫進真實 `%APPDATA%\VoxProse\config_local.json`（測試腳本副作用，非產品邏輯問題）；已手動移除該 key，確認 `load_config()` 還原回預設 `rms`。真的模型快取檔（`silero_vad.onnx`，2.3MB）留在 `%APPDATA%\VoxProse\models\`——與 Whisper 模型快取同一分類，視為合法產物不清除。
- **UI（`ui/settings/engine_page.py`）**：麥克風增益區塊下方新增「🎯 全時模式語音偵測引擎 (VAD)」區段，下拉選單列出 RMS／Silero 兩個選項；Silero 不可用（未裝 onnxruntime）時選項仍然列出但文字註明原因，下方另有一行狀態文案即時反映目前選取的引擎是否可用（比照 `stt/cuda_check.py` 的 CUDA 三態誠實文案原則，`audio/vad/__init__.py:describe_silero_availability()` 是共用真相源）。已用 PyQt6 offscreen 模式（venv_real）煙霧測試：下拉 2 個選項、資料值正確、切換後狀態文案正確更新。
- **測試**：`tests/test_vad_rms.py`（11 項，含逐項比對重構前公式）、`tests/test_vad_factory.py`（8 項，涵蓋 fallback 三情境：缺 onnxruntime／初始化失敗／`engine="rms"`成功路徑）、`tests/test_vad_silero.py`（11 項，mock onnxruntime session 驗證 512+64 窗口緩衝、state/context 跨呼叫延續、下載函式三情境）。`python -m pytest tests/ -q`：**363 passed, 11 skipped**（基準 326 passed + 37 淨增，含 7 個新檔案的 `test_smoke.py::test_py_compile` 自動 parametrize）。

## 2026-07-23 — 正式支援 Python 3.13/3.14

- **背景**：26-5（`docs/DECISIONS.md` 前一輪）修 CI matrix 時明確留下伏筆：「本輪任務範圍只要求修 CI matrix，未動 `requires-python` 上限或這台機器的直譯器版本，留給日後若要正式支援/驗證 3.13+ 時再處理」。本機系統 Python 已是 3.14.6，且 `python -m pytest tests/ -q` 全綠（326 passed, 11 skipped），是時候把上限放寬。
- **查證**（PyPI JSON API 實查，非憑印象）：`ctranslate2` 4.8.1 有 `cp313`/`cp314` win_amd64 專屬 wheel；`PyQt6` 6.11.0 用 `cp310-abi3` 穩定 ABI wheel（涵蓋 3.10 以上所有版本）；`faster-whisper` 1.2.1／`sounddevice` 0.5.5 是 `py3-none-any` 通用 wheel；`opencc-python-reimplemented` 0.1.7 只有 sdist（本來就一直如此，純 Python 重寫無 C 擴充，任何版本都能建置，非本次新增風險）；`numpy`／`pywin32`／`Pillow` 等其餘 `requirements-win.txt` 依賴逐一確認皆有 cp313/cp314 win_amd64 wheel。`actions/setup-python@v5` 依據的 `actions/python-versions` manifest 也已收錄 3.13.x／3.14.x。
- **決定**：`pyproject.toml` 的 `requires-python` 由 `>=3.10,<3.13` 放寬為 `>=3.10,<3.15`；`.github/workflows/ci.yml` 矩陣同步擴充為 `3.10/3.11/3.12/3.13/3.14`（`tests/test_ci_workflow.py` 動態解析兩邊比對，繼續通過不需改斷言本身）；`setup_win.bat` 的 py-launcher 偵測鏈擴充為 `3.14→3.13→3.12→3.11→3.10`（新到舊優先）。
- **維持不動**：可攜包內嵌式 Python（`tools/get_portable_python.ps1`）維持 `3.12.2` 不變——這是打包產物已實測驗證過的版本，換版本要重新驗證整條打包鏈（下載/解壓/`ensurepip`/依賴安裝/EXE 編譯/啟動），本次任務範圍只到「正式支援」（讓使用者自己的系統 Python 3.13/3.14 能跑），不含重新驗證可攜包鏈，故不動。
- **驗證**：本機系統 Python 3.14.6 實跑 `python -m pytest tests/ -q` 全綠（326 passed, 11 skipped），作為 3.14 相容性的直接證據。

## 2026-07-23 — keystrike 死碼清除（推翻 REVIEW 26-4「決定不做」）

- **背景**：同日稍早的隱私與加固審查（見下一節）已查明 `keystrike.log` 從未被實際寫入、`separate_keystrike_log` 開關無程式碼讀取，並判定「無隱私疑慮、死碼留給未來需要時再處理」（REVIEW.md 26-4 🚫 決定不做）。
- **決定**：主人本次明示改為指示清除，推翻原判定。已移除：`paths.py` 的 `KEYSTRIKE_LOG_PATH` 常數與 `initialize_paths()` 的 `touch()` 佔位、`config.py` 的 `separate_keystrike_log` 死開關、`main.py` 啟動時的 keystrike 路徑記錄、`ui/settings/general_page.py` 的勾選框與「檢視熱鍵紀錄」按鈕（連帶移除 `ui/settings_window.py` 兩處讀寫該勾選框的殘留代碼）、`utils/diagnostics.py` 的 `keystrike.log` 收集項。全 repo grep `keystrike`（不分大小寫）確認程式碼零殘留；`CHANGELOG.md`／`docs/DECISIONS.md`／`REVIEW.md` 的既有歷史紀錄段落原文保留，僅 REVIEW.md 26-4 狀態回註為 ✅ 已修。
- **理由**：既然功能本來就沒人用、也沒有計劃要接線，留著死碼只會誤導後續接手者（同類判斷見 `paths.py` 頂部關於 `VOCAB_DIR` 等常數的死碼清理記錄）；主人的清除指示優先於先前「留給未來」的保守判斷。

## 2026-07-23 — 隱私與加固審查（實機驗證前的靜態修 bug 輪）

v3.3.0 已發佈、實機驗證前，主人指示做能做的修 bug／加固。五項依序處理，每項 atomic commit。

### 一、keystrike.log 隱私審查——無需修改

- **查證**：`hotkey/listener.py` 目前的 Windows 實作（`GetAsyncKeyState` 輪詢）只監控 `ui/app.py` 傳入的 `hotkey_configs`（使用者自訂的 ptt/toggle/llm 三個熱鍵 VK 碼），不是全域按鍵 hook，不可能記到一般按鍵。
- **關鍵發現**：`paths.KEYSTRIKE_LOG_PATH` 只在 `initialize_paths()` 被 `touch()` 建立成空檔案，全 repo 沒有任何 `logging.Handler`／`open(..., "a")` 實際寫入這個檔案——`git log -p` 顯示舊版（macOS/pynput 時代）曾經真的有「log ALL raw key interactions」的實作（`_keystrike_queue`／`_keystrike_writer_loop`），但 Windows 化改寫成目前的 polling 版本時已經整段拿掉，只是常數／`touch()`／UI 檢視按鈕沒有跟著清乾淨。
- **連帶發現（死碼）**：`config.py` 的 `separate_keystrike_log` 開關（UI 有勾選框、預設關）現在完全不影響任何行為——沒有任何程式碼讀取這個 key 去決定要不要寫 log。`utils/diagnostics.py` 打包 `keystrike.log` 尾段 500 行時，因為檔案永遠是空的，`_tail_file()` 回傳 `b""`、依現有邏輯根本不會被塞進 zip（`tests/test_diagnostics.py::test_skips_missing_logs_without_creating_empty_entries` 已覆蓋這個行為）。
- **決定**：如實回報「無需修改」——目前無隱私疑慮。死碼（無作用的 `separate_keystrike_log` 開關與空占位檔）留給未來若真的要做「熱鍵事件獨立記錄」功能時一併處理，本次不擴大範圍去刪除或重新接線一個沒人要求的功能。

### 二、log 無限增長加固

- **問題**：`debug.log`（`main.py`）與 `worker_debug.log`（`stt/subprocess_whisper.py`）過去分別用 `logging.FileHandler`／`basicConfig(filename=...)` 附加寫入，沒有大小上限；長期執行（尤其常駐背景程式、每次 STT 子行程重啟都 append）會無限增長。
- **決定**：新增共用的 `utils/log_rotation.py:make_rotating_file_handler()`，統一用 `RotatingFileHandler`，單檔 5MB、備份 2 個（共最多 15MB/log）——數字是工程判斷（足夠涵蓋單次除錯需求，不無限占用磁碟），非上游規格。`keystrike.log` 因為目前沒有任何 handler 實際寫入（見上一項），不適用輪替，等未來真的接線寫入功能時再一併套用同一個 helper。

### 三、broad except 靜默吞噬清查

- **背景**：本專案歷史上三個「引擎自始壞掉」bug（`stt/gemini_stt.py`／`stt/openrouter_stt.py` 的 soundfile 重編碼、`stt/subprocess_whisper.py` 的 vocab prompt IPC 欄位未讀取）都是被 `except Exception` 吞掉才長期未被發現。
- **掃描結果**：全 repo（不含 tests/）165 處 `except`，扣掉 4 處在 tests 目錄，161 處production code。逐一讀 context 分類：**43 處**判定「該補 log 或該收窄型別」並修正；其餘 **118 處** 已有 log/print/使用者可見的錯誤訊息，或是刻意設計成靜默且有正當理由（如 `utils/diagnostics.py` 的診斷收集器本身就該「單一收集項失敗不影響整包匯出」、`__del__`／行程即將 `os._exit()` 前的清理、bare `except: pass` 純屬 cosmetic beep 失敗）。
- **修正原則**：只加 log／收窄例外型別，不改變任何 fallback 行為語義（讀不到設定檔一樣退回 default，串流關閉一樣跳出迴圈）——這是主人明確要求的邊界，避免修 log 順便動到行為造成新回歸。
- **高風險項目**（原本完全靜默、且屬於使用者會實際感知到「東西無聲壞掉」的路徑）：`config.py` load_config() 5 處設定檔損毀靜默重置、`memory/manager.py`／`stats/tracker.py` 資料檔損毀靜默清空、`ui/app.py` 的靈魂情境／私人詞庫／長期記憶三處 LLM prompt 注入失敗靜默跳過、`audio/recorder.py` 錄音輪詢迴圈例外靜默中斷、`stt/subprocess_whisper.py`／`stt/local_whisper.py` 的 `build_vocab_prompt()` 失敗靜默退回預設 prompt（與歷史 bug 同一條路徑）、多個 UI 設定頁（`vocab_mem_page.py`／`stats_page.py`／`sync_page.py`）清單刷新失敗畫面「無聲空白」。
- **順手修正**：`main.py`／`stt/subprocess_whisper.py`／`hotkey/listener.py`／`ui/mic_indicator.py`／`ui/floating_button.py` 等處的 bare `except:` 收窄為 `except Exception:`，避免誤吞 `KeyboardInterrupt`/`SystemExit`；`ui/settings/soul_page.py:129` 從 bare except 收窄為 `(json.JSONDecodeError, TypeError, ValueError)`（那裡只可能是 JSON 解析錯誤）。

### 四、`utils/permissions.py` Windows 化——確認早已完成，補強實質功能

- **查證**：`git log` 顯示本檔在 `b4094b7`（v2.9.6 Windows Stable — Mac cleanup）就已經移除全部 macOS 專屬邏輯（AXIsProcessTrusted 等 TCC 檢查），`AGENTS.md` 模組表寫「內容仍偏 macOS 導向」是舊描述沒跟著更新，已一併修正。
- **實際問題**：4 個函式裡只有 `ensure_all_permissions()` 被 `ui/app.py` import，但從未被呼叫——整個模組是死碼；`check_microphone()` 永遠回傳 `True`，即使使用者在 Windows 隱私設定裡真的關掉了麥克風權限也偵測不到。
- **決定**：`check_microphone()` 改讀 `CapabilityAccessManager\ConsentStore\microphone` 登錄機碼判斷同意狀態（讀不到機碼/例外一律視為已授權，避免誤報——這只是「額外提示」不是麥克風能否運作的唯一依據，實際能不能用仍以 `general_page.py` 的錄音測試「完全靜音」偵測為準）；`ensure_all_permissions()` 於 `ui/app.py.__init__()` 實際呼叫，被拒時只記一筆 warning log、**不**自動彈出系統設定視窗（啟動流程不該有意外跳窗副作用）；`request_microphone_permission()` 保留供未來 UI 按鈕接線，本次不新增按鈕（避免範圍蔓延）。

### 五、CI Python 版本矩陣

- **問題**：`pyproject.toml` 宣告 `requires-python = ">=3.10,<3.13"`，但 `.github/workflows/ci.yml` 只測 3.12——3.10/3.11 從未被 CI 實際驗證過。
- **決定**：改成 `strategy.matrix.python-version: ["3.10", "3.11", "3.12"]`、`fail-fast: false`（比照 yt_fetch）。`requirements-win.txt` 的重依賴（`faster-whisper`/`ctranslate2`/`PyQt6`）在這三個版本都有預編譯 wheel，不需要退回「只跑 py_compile＋輕量測試子集」的降級方案。順手把 `pyyaml` 明確列進 `pyproject.toml` 的 `dev` extras與 CI 的測試依賴安裝步驟（`tests/test_ci_workflow.py` 直接 import，不該靠 `requirements-win.txt` 透過 `ctranslate2`/`huggingface_hub` 轉手依賴僥倖存在）。

### 意外發現

- 執行 `python -m pytest` 時系統預設 Python 是 **3.14.6**（`C:\Python314\python.exe`），已超出 `pyproject.toml` 宣告的 `<3.13` 上限——本輪任務範圍只要求修 CI matrix，未動 `requires-python` 上限或這台機器的直譯器版本，留給日後若要正式支援/驗證 3.13+ 時再處理。

## 2026-07-22 — CUDA 加速與可攜包實測驗證

在裝有 `requirements-cuda-win.txt` 的機器上驗證 `stt/cuda_check.py:probe_cuda()` 回報 `accel_available=True`，STT worker 實際載入模型於 CUDA（`Model loaded successfully on cuda.`），同段音訊 medium 模型 GPU 0.55s vs CPU 8.57s（約 15.6 倍）——此前只驗證過「有 GPU 缺函式庫時的正確降級」，未驗證過真加速。同時實測 `release_win.ps1 -Lite` 端到端建置（616MB，launcher 現場編譯）與打包產物實際啟動，確認 `opencc` 等依賴進 `.runtime`、無崩潰。兩項填補 `REVIEW.md` 先前列出的未驗證邊界，健康分數 8.3→8.7。

## 2026-07-22 — 上游 main 分支 805b007 審視：吸收 3 項平台無關修正，推進 3.3.0

上游 `jfamily4tw/voicetype4tw-mac` `main` 分支新 commit `805b007`（v2.9.18，2026-07-21）審視完畢。此 commit 主體是 macOS 26 裝置端 LLM（Apple Foundation Models）校正功能，但夾帶三項平台無關修正。

### 採用

1. **`vocab/manager.py` 模糊比對短 ASCII 縮寫守衛**：`apply_vocab_correction()` 對 4 字以下純 ASCII 縮寫（STT/PTT/API）做 edit-distance-1 模糊修正太激進，會誤植詞庫另一個縮寫——本 fork 自己樹上也有同型既有 bug，直接移植上游守衛條件。
2. **OpenCC 簡體→繁體後處理**：獨立抽成通用模組 `utils/zh_convert.py`（不直接搬移 macOS 專屬的 `llm/apple_local.py`），接在幻覺過濾之後、詞彙修正之前。選 `s2t`（純簡轉繁）而非 `s2twp`，避免與使用者自訂詞彙衝突；新增設定開關 `zh_convert_enabled`（預設 `True`，不列入 `LOCAL_KEYS`，理由與 `memory_enabled` 同類）；`opencc-python-reimplemented` 為選用依賴，未安裝優雅降級。
3. **`load_all_learned_words()` 排序穩定化**：排序 key 改為 `(-count, word.casefold(), word)`，行為與上游修法前一致，直接移植同一 key。

### 不採用（Mac 專屬／個人化）

Apple Foundation Models 整套、Mac 打包鏈、Mac 專屬 UI 改動、`COMMON_ALIAS_CORRECTIONS`（原作者個人常用詞別名）、句尾標點保護（Apple Local helper 內部行為）——詳見 `docs/UPSTREAM.md` Skipped 表 805b007 條目；`last_reviewed` 已推進至 `805b007`。

### 版本推進 3.3.0

推進 `paths.py`/`pyproject.toml`/`voicetype_installer.iss` 版本號至 3.3.0，本次不 tag、不發佈。

## 2026-07-22 — 設定視窗署名鏈補正＋Dashboard CUDA 文案誠實化＋截圖重拍

主 session 檢視截圖時發現兩個問題：署名區塊框架錯誤且不完整、Dashboard 的 CUDA 狀態文案與 STT worker 實際行為矛盾。

### 一、`ui/settings_window.py:274` 署名區塊框架修正

- **問題**：舊文字把原創作者（吉米丘、CC58TW）誤植為本 fork 的「主要開發者」，且漏列上游 Windows 專用版維護者 go-mask 與本 fork 維護者 SanHsien——是稍早「品牌殘留清掃」任務遺留的缺口（當時 `credit_box` 文字被標註「原封不動」保留，未連帶檢查框架）。
- **決定**：改寫為完整四層署名鏈（原創／上游 Win 版／本 fork／協助），比照 `NOTICE.md`／`README.md`／`about_window.py` 既有措辭；`about_window.py` 核實本來就四層俱全，未改動。

### 二、Dashboard CUDA 狀態文案誠實化

- **查證**：`ctranslate2.get_cuda_device_count()` 只反映驅動層級「有沒有裝置」，本機確有 RTX 3060、回報 1，但驗證環境未裝 `requirements-cuda-win.txt`，worker 的 `cublas64_12.dll` 硬驗證確實失敗——Dashboard 卻仍顯示「加速可用」，與 worker 實際用 CPU 跑矛盾。
- **決定**：新增 `stt/cuda_check.py:probe_cuda()`，抽出與 worker 完全相同的判定邏輯，Dashboard 與 worker 共用同一真相源；文案改為三態（可用／偵測到 GPU 但缺函式庫／未偵測到 GPU）。新增 `tests/test_cuda_check.py`（6 種情境全 mock）。

### 三、意外發現並已修（`tests/test_diagnostics.py` 不穩定斷言）

`test_opens_explorer_to_highlight_zip_on_windows` 的 mock 攔截範圍是行程全域共用的 `subprocess` module，在特定 Python 建置（uv 安裝的 embeddable 3.11.15）上會一併攔截 `platform.win32_ver()` 內部呼叫，導致呼叫次數斷言必然失敗。已用 `git stash` 在未改動的 HEAD 上重現，確認是既有缺陷。改為篩選 `call_args_list` 裡開頭是 `"explorer"` 的呼叫，不再對總呼叫次數斷言。

## 2026-07-22 — 品牌殘留全面清掃＋原作者個人網址移除

維護者在實機驗證過程中發現：品牌雖已改名，但程式 UI 仍多處顯示舊名「嘴炮輸入法」，`REVIEW.md` 混入簡體字。要求「類似錯誤全都要檢查、改過」，並追加移除程式 UI 裡所有指向原作者個人社群/贊助頁的連結。

- **UI 品牌殘留（6 處）**：`ui/menu_bar.py`、`ui/settings/dashboard_page.py`、三處 `QMessageBox` 標題全數改為新品牌。
- **`ui/app.py:98` 歷史版本註解**：含舊名雙關語，為讓守門測試可對 `ui/**` 做無例外全面掃描，直接拿掉字面量而非開特例。
- **`vocab/manager.py:206` docstring 範例**：改用新品牌同音例子「聲成文」/「生成文」。
- **決定（歷史/上游敘述維持不變）**：`NOTICE.md`／`README.md`／`LICENSE`／`CHANGELOG.md`／`VERSIONS.md` 等描述 fork 出處/歷史沿革的文字保留原名。
- **決定（檔名更名）**：`啟動嘴炮輸入法.bat` → `啟動聲成文.bat`，並更新所有引用；`VERSIONS.md` 提及舊檔名的歷史稽核記錄維持不動。
- **決定（`run_voicetype.bat`／`voicetype_installer.iss` 不更名）**：兩者皆非使用者可見品牌文案，橫跨打包鏈與已編譯工具，本次任務無法在 Windows 實機重新編譯驗證，貿然改名風險大於收益，維持現狀。

### 原作者個人網址移除

原則：署名文字保留（MIT 授權與基本禮貌要求），只移除可點擊的個人網址／導流連結；上游 GitHub repo 連結不受影響。

- `ui/settings_window.py`：移除側欄底部整個 SNS 按鈕區塊，保留 `credit_box` 文字署名。
- `ui/settings/common.py`：`SNSButton` 類別一併刪除。
- `voicetype_installer.iss:7`：`MyAppURL` 改為指向本 fork。
- `llm/openrouter.py:53`：`HTTP-Referer`/`X-Title` 改為本 fork 品牌。
- 孤兒資產（6 個 SNS 圖示＋`donate-linepay.jpg`）確認零引用後 `git rm`。

### 簡體字全面清掃

用 Python 腳本逐字元比對「簡體專用字→繁體」對照表（非 grep byte-wise，避免假陽性），對照表刻意排除多音義候選字（后／裡⇔里／台等）避免誤殺合法正體用法。實際掃出 7 處單純打字疏漏，逐字修正，重跑掃描全 repo 零命中。

### 守門測試（新增 `tests/test_brand_and_charset_guard.py`）

三個 pytest 測試：簡體字全 repo 掃描、`ui/**` 舊品牌名稱、`ui/**` 原作者個人網域字串（不鎖上游 GitHub repo 連結）。

- **驗證**：`python -m pytest tests/ -v` 270 passed（266 基準 + 4 新增），10 skipped，與起始基準一致。

## 2026-07-21 — 品牌改名第二階段：資料路徑正名，不寫遷移邏輯

維護者推翻第一階段「怕有真實使用者資料」的保留理由：本機從未實際使用過本程式，不存在任何真實資料。

- **決定（不寫任何 old→new 遷移邏輯）**：直接把 `paths.py:APP_DATA_DIR`／`get_sync_base_dir()` 預設值改成新路徑字面量——第一階段規劃的六條遷移原則前提不成立時永遠不會被執行到，寫出來只是死碼。
- **決定（`voicetype_installer.iss` 補做第一階段排除的兩項）**：`MyAppName` 改 `VoxProse`，`AppId` 換發新 GUID——換 GUID 代表舊版（若有）不會被偵測為可升級對象，本專案無既有安裝基礎，可接受。
- **決定（打包鏈與工具全面跟進）**：會被程式/測試實際讀取比對的字面量一律跟著改；描述「上游是誰、以前叫什麼名字」的歷史沿革敘述保留原名。
- **驗證**：`python -m pytest tests/ -v` 266 passed / 10 skipped；新路徑目錄樹在乾淨環境成功建立，驗證後已清理。

## 2026-07-21 — GitHub repo 更名為 `SanHsien/voxprose`

- **事實記錄**：repo 由 `SanHsien/voicetype` 更名為 `SanHsien/voxprose`（2026-07-21），全 repo `.md` 內約 11 處引用已同步更新。
- **決定（`pyproject.toml` 的 `name` 一併改為 `voxprose`）**：純 packaging metadata，grep 確認無程式碼讀取此欄位值，零風險。`version` 同時推進至 3.2.0。
- **維持不動**：本機工作目錄仍是 `voicetype`，維護者尚未指示更名。

## 2026-07-21 — 品牌改名「聲成文 VoxProse」＋署名補正（go-mask）

維護者拍板品牌規格：中文「聲成文」、英文「VoxProse」、標語「自然開口，清楚成文。」，並補齊過去遺漏的署名——上游 Windows 專用版維護者 go-mask 過去只被當成分支名使用，從未以「維護者」身分列名。

- **決定（系統匣落點依實際程式碼結構）**：規格寫 `ui/tray_manager.py`，但實際字串來源是 `ui/app.py:112`，已在正確落點修改。
- **決定（release ZIP 命名版本號來源改用 `pyproject.toml`）**：不再取自 `paths.py` 的 `BUILD_ID`（純數字格式），改用動態解析的 `X.Y`，格式與規格範例一致。
- **決定（`voicetype_installer.iss` 只改規格明列的兩個欄位）**：`MyAppName`／`AppId` 本次不在授權範圍內，維持原樣（代表安裝檔名與 Start Menu 顯示名稱暫時不一致，屬刻意範圍邊界）。
- **決定（不改 `%APPDATA%\VoiceType4TW` 等實際路徑值）**：維護者明確指示第一階段不動，已用 grep 核對未被觸碰。

## 2026-07-21 — 上游更新自動檢查：`last_merged`／`last_reviewed` 雙欄設計

- **決定（雙欄設計）**：`last_merged`（已合併的最後上游 commit）與 `last_reviewed`（已審視過，含決定不採用者）分開記錄，避免「有沒有合併」當判準會讓不適用的 macOS 專屬 commit 永遠重複回報成雜訊。
- **決定（Skipped 表防決策失憶）**：每次審視後決定「不採用」，除推進 `last_reviewed`，必須同時在 Skipped 表補一列，避免日後查無所獲。
- **決定（compare API 而非 `git log` 手動比對；解析失敗必須非 0 退出）**：避免在 CI runner 上全歷史 clone，也避免把「文件被改壞」誤判成「沒有更新」這種更危險的靜默失敗。

## 2026-07-21 — `ui/settings_window.py` god file 拆分（REVIEW.md #7）

前一個 agent 已建立 `ui/settings/` 子套件的部分頁面但未接線進主檔就中斷；本次先驗證半成品可信度，再完成剩餘頁面拆分並接線。

- **驗證半成品**：用 `ast` 逐一抽取並與原始碼 `difflib` 逐行比對，三個既有檔案全部通過，僅空白行尾端空格差異，判定可信、可直接沿用。
- **決定（多重繼承 mixin 而非組合/委派）**：現樹的 `_create_*_page` 方法大量互相依賴同一個 `self`，改組合會是「順手優化」而非機械搬移、範圍大幅超出任務；mixin 讓方法搬到別檔但 `self.xxx` 呼叫方式不變，唯一能同時滿足「純機械搬移」與「拆分」兩要求。
- **決定（`STT_ENGINES` 常數搬到 `common.py`，同步改測試解析目標）**：避免在殼檔重複宣告常數製造兩份定義的技術債。
- **意外發現並修正（`_run_self_check` 的 `__file__` 路徑計算）**：檔案搬到更深一層目錄後，原本兩層 `dirname` 反推 repo root 的邏輯會算錯路徑，補了一次 `os.path.dirname()`；用 `ast` 逐一比對原始檔與新檔（共 63 個項目）後確認這是唯一必要的非空白差異。
- **對外契約**：`from ui.settings_window import SettingsWindow` 不變，`ui/app.py` 零 diff。
- **測試**：`python -m pytest tests/ -v`：246 passed, 10 skipped（拆分前 241 passed）。PyQt6 實機建構煙霧測試：乾淨 venv 直接 import 真正的 `SettingsWindow`，逐一切換全部 7 個分頁並存取關鍵 widget，exit code 0。
- **commit**：`1252a68`。

## 2026-07-20 — v3.1.0 發版工程收尾（UPSTREAM 追蹤、-NoModel 打包、release/dependency-freshness workflow、版本推進）

維護者指示：v3.1.0 發版前最後一批工程項，完成後 fork 全部 commit 將 squash 成單一 commit。

- **決定（`docs/UPSTREAM.md` 記錄雙上游祖先鏈）**：本 fork 同時追蹤 Windows 線與 Mac 主線兩條祖先鏈，squash commit 保留雙親（`51094bf`＋`e5ddc02`），避免日後合併找不到正確共同祖先。
- **決定（`release_win.ps1` 新增 `-NoModel` 而非只有 Lite/Full）**：滿足「有 CUDA 加速但不綁 medium 模型」的中間選項需求。
- **決定（release workflow 只打包 Lite + NoModel，不含 Full）**：Full 版模型體積會讓 ZIP 逼近 GitHub Releases 2GB 上限，且 CI runner 無模型快取。
- **測試**：`python -m pytest tests/ -v`：233 passed, 10 skipped。

## 2026-07-20 — 上游同步（win-go-mask-202607 三步驟安裝＋MIT 補授權）與雙軌授權收斂為全 MIT

- **決定（合併用 merge commit，保留歷史）**：`git merge --no-ff`，只有 `README.md` 產生衝突。
- **決定（README.md 衝突解法）**：保留本 fork 骨架，整合上游三步驟安裝流程，下載連結改指向本 fork，不引入下游販售/贊助段落。
- **決定（LICENSE 全面改版為全 MIT）**：上游已正式補齊 MIT，雙軌授權聲明失去存在理由，改寫為單一 MIT 文件（上游全文＋本 fork 新增部分附加聲明）。
- **測試**：232 passed, 10 skipped，與改動前一致（本批不涉及 `.py` 邏輯變更）。

## 2026-07-20 — Mac 主線吸收收尾批次（13-1／7-5／7-6／11-3）＋剩餘 bug/死碼清理

- **決定（推翻先前「13-1 刻意不搬」的批次範圍限制）**：13-1（`llm/prompts.py`）本次做完，`refine()` 簽章不變，只加防禦性 fallback。
- **決定（11-3 診斷包 Windows 化改寫）**：改用 `platform.win32_ver()` + ctypes `GlobalMemoryStatusEx`（不額外依賴 `psutil`）。
- **決定（順手修復假 stub，非任務外加碼）**：`_run_mic_test` 的「非 macOS 拒絕」擋板是誤植死碼（其後邏輯本來就跨平台），移除並取消 Windows 隱藏。
- **維持不動**：MiniMax 引擎、`target_pid` 精準注入等項目重新檢視後沒有新事證，維持原判斷。
- **測試**：232 passed, 10 skipped（起始 193 passed）；本次開發機仍無 `PyQt6`/`sounddevice`，未實機驗證。

## 2026-07-20 — subprocess_whisper worker 補讀詞彙庫 prompt 欄位（既有 bug 修復）

- **問題**：worker 端 `_stt_worker` 從未讀取 IPC 訊息的 `"prompt"` 欄位，永遠用硬編預設字串，詞彙庫學到的專有名詞從未真正影響本地 Whisper 辨識。
- **決定（修法）**：`_run_transcribe()` 新增 `initial_prompt` 參數，worker 改讀 `msg.get("prompt")`，空/缺 fallback 回預設字串。
- **決定（比照 Mac 版語義，取代而非串接）**：`build_vocab_prompt()` 回傳值本身已是完整語句，正確語義是整個取代而非拼接；`stt/local_whisper.py` 本來就正確接線。
- **測試**：新增 4 個回歸測試，193 passed, 10 skipped。

## 2026-07-20 — Mac 主線功能吸收第 2-5 項（13-2／16-4／7-1~7-3／7-4）

- **決定（13-2 抗幻覺轉錄參數）**：`no_speech_threshold=0.6` + `condition_on_previous_text=False`，比照 Mac 版數值原封不動搬。
- **決定（7-1/7-2/7-3 麥克風裝置/增益/AGC，架構層面最大取捨）**：現樹是 callback-based，Mac 版已改 polling-thread——選擇把功能織進現樹既有架構而非整檔覆蓋，因兩種架構在「加裝置參數、放大 PCM、算 RMS」幾個切入點完全等價。純數學抽成 `audio/gain.py`（無 sounddevice 依賴，可單元測試）。
- **決定（7-4 靜音預檢）**：放在 `_on_audio_complete` 而非 `_process_audio`，避免 VAD 路徑誤判 PTT 殘留狀態。
- **誠實聲明**：本次開發機無 `PyQt6`/`sounddevice`，UI 接線與真實 Whisper 效果未實機驗證，純邏輯部分有 mock/純函式單元測試覆蓋。

## 2026-07-19 — llm/claude.py 欄位名不一致修復（追加，六項修復時的意外發現）

- **決定**：改 `llm/claude.py` 對齊 config/UI 既有欄位名（`anthropic_*`）而非反向改 config，零遷移成本。此 bug 導致 Claude LLM 引擎自始拿到空 key，靜默回傳原文。
- **全 provider 檢查**：grep 全部 provider 逐一比對 DEFAULT_CONFIG，僅 claude 一處中雷。
- **防回歸**：新增 `tests/test_llm_config_keys.py`，AST 靜態掃描驗證欄位名存在於 DEFAULT_CONFIG。

## 2026-07-19 — REVIEW.md 風險表六項修復（API Key 同步／逾時／PTT-VAD 互斥／eval／diagnose_mic／Monaco）

- **決定（API Key 本地化＋一次性遷移，風險表 #4）**：所有 `*_api_key` 欄位動態併入 `LOCAL_KEYS`，並對既有 `config_global.json` 做一次性遷移即刻落盤，避免洩漏窗口。
- **決定（逾時統一常數）**：只補完全沒有 timeout 的兩個 SDK 呼叫點，已有合理 timeout 的呼叫點不動。
- **決定（PTT/VAD 互斥採 PTT 優先）**：PTT 是主動按鍵意圖明確，VAD 是被動偵測可能誤觸發，對使用者最不意外的行為是「照我按的來」。
- **決定（eval → ast 白名單）**：擋節點類型而非字串黑名單，`__import__` 等繞法在結構上不可能通過。
- **決定（diagnose_mic.py 重寫而非刪除）**：刪檔會斷打包鏈（`release_win.ps1` 按檔名複製），且麥克風診斷有實際支援價值。
- **決定（Monaco → Consolas）**：等寬字型比黑體更適合編輯區，且 Windows 內建無 fallback 風險。

## 2026-07-19 — REVIEW.md 四項修復（installer 死引用／Gemini STT／幻覺過濾／paths 死碼）

- **決定（installer）**：移除引用不存在的 `platform_layer\*`，找不到任何歷史紀錄顯示曾規劃具體用途。
- **決定（Gemini STT）**：補分派分支而非移除 UI 選項（實作邏輯平台無關）；順手修正簽章不符與 WAV 重複編碼兩個既有 bug。
- **決定（幻覺過濾）**：抽成不依賴任何 STT 引擎的 `stt/hallucination_filter.py`，接在統一路徑，對本地與雲端引擎一視同仁生效。
- **決定（paths.py 死碼）**：`VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 已 grep 驗證零引用，直接移除而非補實作（跨裝置同步是另一個需求變更）。
- **意外發現（已處理）**：`stt/openrouter_stt.py` 有與修復前 `GeminiSTT` 完全相同的 bug，已比照修法處理。

## 2026-07-19 — README Windows 化改寫

- **決定**：`README.md`/`README.en.md` 改寫為「本 repo 只做 Windows 10/11」定位，功能特色與設定欄位表全部對照現行程式碼重寫。
- **理由**：避免使用者照著 macOS 步驟卡關，或誤以為這裡有 macOS 支援。

## 2026-07-19 — 11 項開發鷹架落地（依 `dev-env-best-practices.md` 範本）

- **決定**：補齊 `CLAUDE.md`、`pyproject.toml`、`tests/` + pytest、`CHANGELOG.md`、`.gitattributes`、`.github/workflows/ci.yml`；全面改寫 `AGENTS.md`/`SKILL.md`/`docs/DEVELOPMENT.md`，清除「Mac 純化版 main」時代遺留的錯誤描述。
- **決定（測試移植策略）**：從舊版 Mac 主線撈回的 6 支 `test_*.py`，只有 2 支測試對象仍存在可移植，其餘跳過並記明原因，不硬套對不存在行為斷言的測試。
- **理由**：`AGENTS.md`/`SKILL.md` 曾宣稱 `CLAUDE.md` 存在但實際不存在，是文件對外承諾與現況不符的直接缺口。

## 2026-07-19 — 雙軌授權聲明 + 引入上游 win-stable 分支

- **決定（授權）**：雙軌 `LICENSE`——上游程式碼誠實揭露無正式授權，SanHsien 新增部分掛 MIT。
- **決定（Windows 路線）**：以活躍維護的 `win-stable`（含完整 Windows 工具鏈）為開發基底，不走「把 Mac 純化的 main 修回跨平台」路線。
- **理由**：main 分支自 v2.9.0 起被 Mac 純化（Windows 健康分數 2/10），`win-stable` 成本低、風險小。

## 2026-07-19 — 建立開發鷹架，比照 sticker-forge / gpt-ai-assistant

- **決定**：補上 `AGENTS.md`、`NOTICE.md`、`SKILL.md`、`docs/DEVELOPMENT.md`、`docs/DECISIONS.md`（本檔）、`README.en.md`，格式比照既有兩個 repo。
- **Review 採 latest-only**：`REVIEW.md` 只放最新一次覆核，不逐版累積歷史。
- **授權誠實揭露**：查證上游與本 fork 都沒有正式 `LICENSE` 檔，如實記錄查證過程與結論，不捏造授權聲明。
- **理由**：讓 AI agent 接手時有一致的專案定位與驗證方式，文件需明確標註平台差異。
