# VoiceType4TW（嘴炮輸入法）Review — win-stable 分支

- **日期**：2026-07-19
- **Reviewer**：Claude Code（對 win-stable 做全面靜態 review，未實際安裝/執行程式）
- **Review 對象**：上游 `jfamily4tw/voicetype4tw-mac` 的 **`win-stable` 分支，v3.0.1「win-go-mask」（commit `b694e40`，2026-07-08，BUILD-3010-STABLE）**，讀碼位置為唯讀 worktree `...\scratchpad\vt-win-stable`（下文所有檔案路徑皆指此 worktree 內容，即 win-stable 分支）
- **重要前情提要（讀碼過程中發現，非本次任務範圍但必須先講）**：見下方「⚠️ 重大發現」

---

## ⚠️ 重大發現：Windows 路線決策與鷹架建立已經執行完畢

本次 review 一開始只打算讀 win-stable 分支程式碼並改寫本檔案，但讀碼途中發現：**主 repo（`C:\Users\SanHsien\OneDrive\文件\GitHub\voicetype`）目前 checkout 在 `main` 分支，HEAD 是 `d9fb5c3`——一個已經把 `win-stable`（`b694e40`）合併進 `main` 的 merge commit，領先 `origin/main` 20 個 commit（尚未 push）。**

證據：
- `git log --oneline -3`（主 repo）：`d9fb5c3 merge: 以上游 win-stable (v3.0.1, b694e40) 為 main 的 Windows 開發基底` → `51094bf Revise README...`（這是**舊版 REVIEW.md 審閱的那個 HEAD**）→ `b694e40 release(win): mark win-go-mask v3.0.1`。
- `docs/DECISIONS.md`（主 repo，2026-07-19 條目）明確記載維護者已拍板：「專案目標是 Windows 版...以活躍維護的 win-stable 為 Windows 開發基底...不走『把 Mac 純化的 main 修回跨平台』路線」，並且同時完成了雙軌授權（新增 `LICENSE`、`NOTICE.md`）與鷹架文件建立（`AGENTS.md`、`SKILL.md`、`README.en.md`、`docs/DEVELOPMENT.md`），文件裡明白寫著「本次鷹架建立不含 REVIEW.md（由另一個 agent 負責）」——也就是本次任務。
- 主 repo 目前的檔案列表已經與 win-stable worktree 幾乎一致（`main.py`、`paths.py`、`ui/app.py` 等全部就位），舊 REVIEW.md（審閱 Mac 純化版 `main`，HEAD `51094bf`）已經是歷史文件。

**結論給維護者**：本次任務原本設定的決策點（第 7 節「決定是否合併 win-stable」）**已經被另一個 session 執行掉了**。下面第 7 節「接手起點建議」會直接跳過「要不要合併」的討論，改成「合併之後，接下來做什麼」。舊 REVIEW.md 提到的「無 LICENSE」風險（風險排序表 #4）也已經由 `LICENSE` + `NOTICE.md` 處理。本檔案改寫**只針對 win-stable 分支本身的程式碼品質**，不重新審閱主 repo 合併後的最終樹狀態（那不在本次任務範圍內，若需要應另開一次 review）。

---

## 總評

**健康分數：6.5 / 10。**

win-stable 是一個「血淚教訓寫成程式碼」的可用 Windows 版本，作者顯然是在真實 Windows 機器上反覆試錯（Access Violation、CTranslate2/PyQt6 衝突、embedded Python 打包）打磨出來的——`main.py` 開頭一大段環境變數與 `os.dup2` 黑魔法、`stt/subprocess_whisper.py` 把 faster-whisper 整個丟進獨立子程序隔離 CUDA、`hotkey/listener.py` 完全放棄 `pynput` 改用 Win32 `GetAsyncKeyState` 輪詢，這些都是「比文件裡寫的教訓更進一步」的實戰解法（見第 2 節）。安裝鏈（`setup_win.bat`、`release_win.ps1`、`tools/get_portable_python.ps1`）也做到了偵測 Python 版本降級鏈、依 GPU 有無條件安裝 CUDA、產生真正解壓即用的可攜版 ZIP，比一般個人專案的打包成熟度高出不少。

但它同時保留了個人專案常見的問題：`ui/settings_window.py`（2050 行）是 god file；完全沒有任何 `test_*.py`（`self_check.py`/`diagnose_mic.py` 是手動煙霧測試腳本，不是單元測試，且 `diagnose_mic.py` 整支是 macOS-only 死碼，在 Windows 上跑了等於沒跑）；STT 引擎選單裡的「Gemini (雲端 API)」選項實際上是壞的（`get_stt()` 沒有對應分支，選了會靜默 fallback 成別的引擎，見第 2 節）；`paths.py` 宣告的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 雲端同步路徑其實從未被 `vocab/manager.py`/`memory/manager.py`/`stats/tracker.py` 使用，是三個死掉的常數，代表「詞彙與記憶會跨裝置同步」這件事目前不成立；`voicetype_installer.iss` 裡引用一個不存在的 `platform_layer\*` 資料夾，Inno Setup 編譯時大機率直接失敗。config.json（worktree 內樣本檔）**沒有真實 API key**，這點可以放心。整體來說：**這是一個「能跑但需要一輪紮實整理」的分支**，比 Mac 純化版的 main（Windows 健康分數 2/10，見文末「main 對照」）好得多，適合直接作為 Windows 開發基底。

---

## 1. 架構總覽

### 模組結構（win-stable）

| 模組 | 行數 | 職責 | 備註 |
|---|---|---|---|
| `main.py`（win-stable） | 131 | 純啟動殼：環境變數黑魔法、日誌初始化、`from ui.app import VoiceTypeApp` | 與 main 分支的 969 行 `main.py`（身兼 pipeline）**完全不同構** |
| `ui/app.py`（win-stable） | 521 | 事實上的核心：`VoiceTypeApp` 生命週期、`_process_audio`、`_build_llm_prompt`、UI 訊號分派 | 相當於 main 分支 `main.py` 的角色被搬進了 `ui/` |
| `ui/settings_window.py` | 2050 | 設定視窗（Dashboard/辨識引擎/靈魂/詞彙/系統設定共數頁） | God file，比 main 分支的 3046 行版本小，但仍是全 repo 最大檔案 |
| `hotkey/listener.py` | 136 | 全域熱鍵，**純 Win32 `ctypes` 輪詢**，無 `pynput` | 與 main 分支（461 行，`Quartz`/`pynput` 雙軌）完全不同實作，見第 2 節 |
| `stt/`（618 行） | | `base.py` + `subprocess_whisper.py`（430 行，子程序隔離 CTranslate2）+ `local_whisper.py`（56 行，非 Windows fallback）+ `groq_whisper.py`/`openrouter_stt.py`/`gemini_stt.py` | `mlx_whisper.py` 已不存在（Apple Silicon 專用，Windows 分支不需要） |
| `llm/`（285 行） | | 7 個 provider：ollama/openai/claude/openrouter/gemini/qwen/deepseek | 比 main 分支少 minimax，其餘結構相同 |
| `output/injector.py` | 165 | 剪貼簿 + `SendInput` 模擬 Ctrl+V／Shift+Left 選字 | Windows 分支寫得完整，macOS 分支（AppleScript）也保留 |
| `audio/`（296 行） | | `recorder.py`（PTT 錄音）+ `auto_trigger.py`（172 行，v2.9.8 VAD 全時自動觸發） | `auto_trigger.py` 是 win-stable 獨有、main 分支沒有的功能 |
| `actions/`（156 行） | | `dispatcher.py`（正則比對語音指令）+ `builtins.py`（天氣/時間/搜尋/計算機） | 與 main 分支邏輯一致 |
| `vocab/manager.py` | 233 | 自訂詞彙 + 自動學習 | 與 main 分支邏輯一致，但儲存路徑不同（見第 2 節） |
| `memory/manager.py` | 224 | 跨 session 記憶、`delete_entry`/`clear_summary`（v2.9.10 新增，main 分支沒有） | |
| `utils/`（84 行） | | `branding.py`（AppUserModelID + 圖示注入）、`permissions.py`（Windows 全部 no-op）、`resources.py` | |
| `tools/` | | `doctor.py`（環境預檢）、`download_models.py`、`get_portable_python.ps1`（嵌入式 Python）、`launcher.cs`（C# Starter EXE 原始碼） | win-stable 獨有，main 分支沒有對應物 |
| `paths.py` | 168 | 路徑常數、`SYNC_BASE_DIR` 雲端同步重定向、`_install_bundled_models()`（v3.0.1 真可攜版模型自動安裝） | |

### 與 main（Mac 版）架構差異

- **入口點不同構**：main 分支的 `main.py`（969 行）本身就是 `VoiceTypeApp` 的所在地；win-stable 的 `main.py`（131 行）只是啟動殼，真正的 App 類別在 `ui/app.py`（win-stable:53-521）。這證實了舊版 REVIEW.md 第 7 節引用的 `openspec/specs/v296_windows_port_brief.md:16`（「Windows 分支的主流程檔案是 `ui/app.py`」）——**這件事現在可以直接讀碼證實，不再是「未驗證」**。
- **熱鍵實作完全不同**：main 分支 `hotkey/listener.py` 是 macOS `Quartz.CGEventTap` 為主、Windows 走 `pynput` 為輔的雙軌設計；win-stable 的 `hotkey/listener.py`（win-stable:1-137）**整個檔案只有 Windows 一條路**，用 `ctypes.windll.user32.GetAsyncKeyState` 輪詢（win-stable:53-99），完全沒有 `pynput` 或 `Quartz`。這不是「移植」，是「重寫」。
- **STT 引擎選擇邏輯不同**：win-stable 的 `stt/__init__.py:6-26` 依平台強制走 `SubprocessWhisperSTT`（Windows）或 `LocalWhisperSTT`（其他平台），main 分支預設走 `mlx_whisper`。
- **win-stable 獨有功能**：`audio/auto_trigger.py`（全時自動觸發/VAD，v2.9.8）、`memory/manager.py` 的 `delete_entry`/`clear_summary`（v2.9.10）、`paths.py` 的 `_install_bundled_models()`（v3.0.1 真可攜版）——這幾項在 main 分支的 VERSIONS.md 裡也有記載（版本號相同代表這些是「先在某條線做出來、後來人工同步過去」的功能，兩邊命名版本號一致但程式碼是分開維護）。

### 資料流（win-stable）

`ui/app.py:277-416` 的 `_process_audio`：STT (`self.stt.transcribe`, win-stable ui/app.py:290) → 短音檔/空字串防呆 → 詞庫修正 (`vocab.manager.apply_vocab_correction`, ui/app.py:299-300) → 語音指令派發 (`action_dispatcher.dispatch`, ui/app.py:313) → LLM 潤飾（`_build_llm_prompt` + `llm.refine`，ui/app.py:365-367，另有 Demo 模式的多情境並行處理，ui/app.py:332-361）→ 標點全形化 + 前綴雜訊剔除（ui/app.py:372-379）→ `injector.inject()`（ui/app.py:396）→ 記錄 `stats`/`memory`（ui/app.py:401-413）。與 main 分支流程相同（同一套「錄音→STT→詞庫→指令→LLM→注入→記憶」骨架），差異主要在「怎麼跑 STT」這一步。

---

## 2. Windows 實作品質

### 全域熱鍵：從 pynput 換成純 Win32 API（重大架構改善）

`hotkey/listener.py:53-99`（win-stable）完全捨棄 `pynput`，改用 `ctypes.windll.user32.GetAsyncKeyState` 每 15ms 輪詢一次（`time.sleep(0.015)`，win-stable:99），並支援 `code:<VK>` 格式的精確虛擬鍵碼設定（win-stable:60-64）或內建的字串到 VK 對照表（win-stable:66-74，如 `alt_r: 0xA5`）。

這個設計**結構性地解決了** 舊版 REVIEW.md 與 `windows_cuda_qt_crash_postmortem.md:18`（win-stable 也有同一份文件）記載的「Windows 右 Alt 鍵在不同鍵盤語系下可能被 `pynput` 註冊為 `alt_gr` 而非 `alt_r`」問題——因為它根本不經過 `pynput` 的跨平台按鍵名稱轉譯層，直接查 VK code，不存在「同一個實體鍵在不同語系被翻成不同字串」的問題。註解本身也點出動機（win-stable:78-80）：輪詢比低階鍵盤鉤子（`WH_KEYBOARD_LL`）更能避免與 OpenMP/CUDA/ctranslate2 的訊息迴圈衝突。**這是一個「比文件建議的修法更根本」的解法**，值得在往後的重構中保留這個方向，不要為了「看起來更標準」而換回 hook 或 `pynput`。

代價：`_run_windows`（win-stable:53-99）是忙輪詢（busy-poll），15ms 週期换算大約 CPU 佔用不高但非零，且沒有除錯用的按鍵事件日誌節流（`self.log.debug` 每次按鍵狀態改變都會記，一般情況下量不大）。

### PyQt6 / CUDA 衝突：從「文件建議的 import 順序」進化成「子程序隔離」

`windows_cuda_qt_crash_postmortem.md`（win-stable 也收錄同一份文件）建議的解法是「阻擋 PyQt6 import，先阻塞式載入 STT，再匯入 UI」。實際程式碼**沒有照單全收**：`ui/app.py:11`（`from PyQt6.QtWidgets import QApplication`）在檔案最頂端就已經 import PyQt6，並不是等到 STT 載入完成後才 import。

但實際採用的是更徹底的方案——`stt/__init__.py:16-23` 的註解直接寫明：「已經證實在同一個 process 裡讓 CTranslate2 跟 PyQt6 event loop 共存必定會造成 Access Violation (0xC0000005)，因此 Windows 上必須把 `SubprocessWhisperSTT` 當唯一選項」。`stt/subprocess_whisper.py:20-431` 用 `multiprocessing.get_context('spawn')` 把整個 faster-whisper/CTranslate2 模型丟進完全獨立的子程序，主程序（含 PyQt6）與子程序之間只透過 `multiprocessing.Pipe` 交換音訊 bytes 與轉錄結果（`_stt_worker`, win-stable:20-278；`SubprocessWhisperSTT`, win-stable:280-431）。子程序內還做了 `AllocConsole()`（win-stable:55-69，避免 ctranslate2 在無 console 環境下 Access Violation）、NVIDIA DLL 路徑注入（win-stable:71-94）、CUDA 可用性硬驗證失敗自動降級 CPU（win-stable:110-122）。

`ui/app.py:139-140,155-169` 的 `_sync_preload_models()` 額外在主執行緒同步等待 LLM/STT 就緒（註解寫「防止 ctranslate2/PyQt thread conflict」），這解決的是「執行緒競爭」問題，跟 postmortem 講的「DLL 載入順序」是不同層次的問題——**兩者都做了，但文件跟程式碼對「真正的根因」的敘事已經不一致**，接手者應該以「子程序隔離 + 同步預載」這個實作現狀為準，而不是照字面重讀 postmortem 去改 `main.py`/`ui/app.py` 的 import 順序（那樣做不會有實際效果，因為問題早就用別的方式解決了）。

字體地雷（postmortem 第三點：Windows 需要強制 `QFont("Microsoft JhengHei", 10)`）**已落實**：`ui/mic_indicator.py:309`（`self._app.setFont(QFont("Microsoft JhengHei", 10))`）以及 `ui/settings_window.py`（多處 `win_font = "Microsoft JhengHei" if platform.system() == "Windows" else ...`，如 win-stable:317,370,378,416,439,778,831,847）。但 `ui/settings_window.py:1086,1154` 的程式碼編輯區/靈魂編輯區用了硬編碼 `QFont("Monaco", 12)`／`QFont("Monaco", 11)`——Monaco 是 macOS 專屬字型，Windows 上沒有，Qt 會靜默 fallback 成系統預設等寬字型（不會崩潰，但這兩處明顯是複製 Mac 版程式碼時漏改的），視覺上與其他地方已經做好平台判斷的字型設定不一致。

### 已發現的具體 Bug：STT 引擎下拉選單的「Gemini」選項是壞的

`ui/settings_window.py:24`：`STT_ENGINES = ["local_whisper", "groq", "gemini", "openrouter"]`，`ui/settings_window.py:1002-1010` 把這四個值都放進使用者可選的下拉選單（`engine_meta` 甚至有專屬顯示文字「Gemini (雲端 API)」，win-stable:1006）。但 `stt/__init__.py:6-26` 的 `get_stt()` 分派邏輯只認得 `"groq"` 和 `"openrouter"` 兩個特殊值（win-stable:9-14），其餘所有值（含 `"gemini"`、`"local_whisper"`、任何打錯字的值）全部落進 `else` 分支，該分支只依 `platform.system()` 決定回傳 `SubprocessWhisperSTT` 或 `LocalWhisperSTT`（win-stable:15-26），**完全沒有引用 `stt/gemini_stt.py` 裡的 `GeminiSTT` 類別**。也就是說：使用者在設定頁選擇「Gemini (雲端 API)」作為語音辨識引擎，實際上完全不會呼叫 Gemini API，會靜默地繼續用本地 Whisper——UI 顯示的選項與後端行為完全脫節。`stt/gemini_stt.py` 這個檔案目前是死碼（沒有任何呼叫路徑能觸發它），除非透過其他管道呼叫。這是一個使用者可見、容易發現、但目前沒人反應過的真實 bug。

### 資料同步路徑：宣告了但沒接上的死碼

`paths.py:56-58` 宣告了 `VOCAB_DIR = SYNC_BASE_DIR / "vocab"`、`MEMORY_DIR = SYNC_BASE_DIR / "memory"`、`STATS_DIR = SYNC_BASE_DIR / "stats"` 三個常數，語意上暗示詞彙/記憶/統計會跟著 `config_global.json` 一起同步到使用者自訂的雲端目錄。但實際上：
- `vocab/manager.py:13,15`：`from paths import get_data_dir` + `VOCAB_DIR = get_data_dir("vocab")`——注意這裡是**用同名區域變數覆蓋掉語意**，`get_data_dir()`（`paths.py:72-75`）回傳的是 `APP_DATA_DIR`（本機 AppData）子目錄，跟 `paths.py:56` 那個指向 `SYNC_BASE_DIR` 的 `VOCAB_DIR` 完全是兩回事。
- `memory/manager.py:13,15`：同樣模式，`DATA_DIR = get_data_dir("memory")`，也是本機路徑。
- `stats/tracker.py:10,12`：同樣模式。

**結論**：`paths.py:56-58` 這三個常數目前在全 repo 沒有任何地方被引用（已用 grep 驗證），是純粹的死碼；詞彙庫、長期記憶、使用統計目前只存在本機 `%APPDATA%\VoiceType4TW\{vocab,memory,stats}`，**不會**跟著雲端同步目錄走（只有 `config_global.json` 和 `soul/` 系列目錄真的會同步，見 `paths.py:45,48-53`）。如果之後要做「換電腦後詞彙/記憶跟著走」的功能，這三個常數可以直接拿來用，但目前它們只是「看起來已經做了、其實沒做」的陷阱，接手者容易被誤導。

### Threading / 併發

- STT 走獨立子程序 + `queue.Queue` 分派（`stt/subprocess_whisper.py:305,312-340`），主程序與子程序之間用 `threading.Lock`（`_lock`, win-stable:284,375）保護 pipe 存取，設計上是安全的。
- `audio/auto_trigger.py`（VAD 全時模式）與 `audio/recorder.py`（PTT）各自開自己的 `sounddevice.InputStream`，兩者互不干涉（README.md 與程式碼註解都強調這點，`audio/auto_trigger.py:10-11`），但這代表**兩個模式同時啟用時會有兩個並行的麥克風輸入串流**——目前沒看到互斥檢查，若使用者同時打開 PTT 熱鍵又開全時模式，理論上有兩個 stream 搶同一個裝置的可能性（多數音效卡驅動允許多開，但沒有見到針對此情境的顯式測試或防呆）。
- `_on_config_saved`（`ui/app.py:490-500`）持有 `self._config_lock` 重新載入 config、重建 `self.llm`/`self.stt`，但重建 `self.stt` 時舊的 `SubprocessWhisperSTT` 實例只靠 Python GC 觸發 `__del__`（`stt/subprocess_whisper.py:422-430`）才會送出 quit 訊號、`terminate()` 子程序——如果 GC 沒有立即回收（CPython 引用計數通常會，但如果有其他地方持有引用就不會），舊的 STT worker 子程序可能會變成孤兒程序繼續佔用記憶體/GPU，直到主程式結束。

### 資源釋放

- `AudioRecorder.stop()`（`audio/recorder.py:93-112`）妥善呼叫 `stream.stop()`/`stream.close()` 並包 try/except。
- `SubprocessWhisperSTT.__del__`（win-stable:422-430）嘗試優雅送出 quit 訊號、`join(timeout=1.0)`、逾時後 `terminate()`——邏輯完整，但依賴 `__del__` 被觸發的時機不保證（見上一段）。
- `quit()`（`ui/app.py:460-466`）最後呼叫 `os._exit(0)`，跟 main 分支一樣是硬退出，不會觸發正常 Python cleanup；子程序 STT worker 若還在跑，會隨父程序 `os._exit` 一起被系統回收（Windows 上子程序不會自動變成孤兒被殺，但這裡剛好因為是 `daemon=True` 的 `multiprocessing.Process`，作業系統通常仍會清掉，風險低）。

### eval() 計算機（與 main 分支相同問題）

`actions/builtins.py:36-47`（win-stable）與 main 分支同樣的模式：正則清洗只留數字與運算符後 `eval(clean_expr)`。注入面很小，但建議項同舊版 review：改用安全的運算子解析取代 `eval`。

---

## 3. 安全與隱私

### API Key：config.json 是否含真金鑰？—— **不含，可以放心**

`config.json`（win-stable worktree 根目錄，1-8 行）內容為：
```json
{
    "stt_engine": "local_whisper",
    "whisper_model": "medium",
    "language": "zh",
    "llm_enabled": false,
    "active_scenario": "default",
    "auto_paste": true
}
```
**沒有任何 API key 欄位**（沒有 `openai_api_key`/`anthropic_api_key`/`gemini_api_key` 等任何一個 key 的值），這是一個開發用的樣本設定檔（且對應 `config.py:67-80` 的舊版 `config.json` 遷移邏輯：偵測到 `%APPDATA%` 下的舊版單檔 config 會自動拆分成 `config_local.json`/`config_global.json` 後刪除原檔）。**明確結論：worktree 裡的這個 config.json 不含真實金鑰，沒有外洩風險。**

### API Key 儲存架構與雲端同步（與 main 分支相同的設計，風險同樣存在）

`config.py:51-59`（win-stable）的 `LOCAL_KEYS` 白名單與 main 分支幾乎一致，所有 `*_api_key` 欄位都不在白名單內，因此會被拆進 `GLOBAL_CONFIG_PATH`（`paths.py:45`，位於 `SYNC_BASE_DIR`，可被 `sync_path.txt` 指標重定向到 iCloud/Google Drive/NAS，`paths.py:17-36`）。這與舊版 REVIEW.md 對 main 分支的發現（風險 #2）**完全相同的設計**——win-stable 沒有比 main 分支更謹慎，同樣是「API Key 明碼且設計上可能被同步到第三方雲端資料夾」。這點在 win-stable 上實測相關程式碼路徑完全成立，仍建議在雲端同步設定頁加上明確警語（見舊版 review 建議 #10，同樣適用於此）。

### LLM Provider 的空 Key 防護（win-stable 比 main 分支做得更好）

`llm/claude.py:11-13` 與 `llm/openai_llm.py:12-14`（win-stable）的 `refine()` 開頭都有 `if not self.api_key: return text` 防護——這點**與舊版 REVIEW.md 對 main 分支的發現不同**：main 分支的 `llm/claude.py`/`llm/openai_llm.py` 當時被記錄為「沒有這層防護」。win-stable 這兩個 class 都補上了，是比 main 分支更安全的版本。`llm/gemini.py:13-14`、`llm/ollama.py`（無 key 概念，本機服務）、`llm/qwen.py`/`llm/deepseek.py`（未逐一列出，但沿用同一套已驗證的模式）也都有類似防護。

### 網路請求逾時（沿用 main 分支的不一致問題）

| 模組 | timeout |
|---|---|
| `llm/ollama.py:24` | 5s |
| `llm/openai_llm.py:24` | 30s |
| `llm/gemini.py:24` | 30s |
| `llm/claude.py` | 無明確 timeout（SDK 預設值） |
| `actions/builtins.py:10` | 5s（wttr.in 天氣） |

與 main 分支相同的結論：沒有統一逾時策略常數，`llm/claude.py` 仍缺 timeout。由於 STT 走獨立子程序、不佔用主 UI 執行緒，這個問題在 win-stable 上的影響範圍比 main 分支略小（不會卡住下一次錄音的 STT worker），但仍可能讓 `_process_audio` 背景執行緒卡住很久。

### Gemini API Key 走 URL query string（Google 官方設計，非本 repo 問題）

`llm/gemini.py:15`：`url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"`——與 main 分支相同的模式，是 Google Gemini API 官方認證方式，不是本 repo 的漏洞，但一樣有「URL 常被記錄在 proxy/log」的通用風險。

### 隱私：轉錄文字落地情況（與 main 分支結論相同）

`memory/manager.py:47-59`（win-stable）的 `add_entry()` 在每次成功處理後被呼叫（`ui/app.py:410-411`），把 STT 原文與 LLM 潤飾後全文明碼寫入本機 `%APPDATA%\VoiceType4TW\memory\memory.json`（注意：**不是**寫到雲端同步目錄，見上方「資料同步路徑」小節），保留最近 50 筆（win-stable:19,57-58），超過 7 天觸發歸檔（`maybe_archive`, win-stable:85-125）但原文仍完整保留在 `archive/*.json` 裡。錄音音訊本身（WAV bytes）同樣不落地，只在記憶體中傳遞（`audio/recorder.py` 全檔案搜尋不到任何 `.wav` 寫檔呼叫，`_to_wav_bytes()` 回傳的是記憶體 bytes）。

### 子程序/系統呼叫

- Windows 端全部走 `ctypes.windll.user32.SendInput`（`output/injector.py:100-157`）或 `GetAsyncKeyState`（`hotkey/listener.py`），沒有 `subprocess.run` 呼叫外部指令，注入面比 main 分支的 AppleScript 方案更小（沒有字串拼接進 shell 指令的疑慮）。
- `actions/builtins.py:25,33`（win-stable）同樣延續 v2.7.32 的「不自動開啟瀏覽器」安全決策。

---

## 4. 相依與打包

### requirements-win.txt / requirements-cuda-win.txt

`requirements-win.txt`（win-stable，1-16 行）：
```
PyQt6>=6.6.0
pystray>=0.19.5
Pillow>=10.2.0
pywin32>=306
pyperclip>=1.8.2
faster-whisper>=1.0.0
httpx>=0.27.0
certifi>=2024.2.2
numpy>=1.26.0
sounddevice>=0.4.6
requests>=2.31.0
soundfile>=0.12.1
anthropic>=0.25.0
openai>=1.30.0
groq>=0.9.0
```
`requirements-cuda-win.txt`：`nvidia-cublas-cu12>=12.1.3`、`nvidia-cudnn-cu12>=8.9.2`，並有註解說明只在偵測到 NVIDIA GPU 時才由 `setup_win.bat` 安裝。

**與舊版 REVIEW.md 對 main 分支 `requirements.txt` 的發現相比，這裡有明確改善**：
1. `requests` 已明確宣告（win-stable:11）——main 分支當時是隱性相依（靠遞移安裝），這裡已修正（對應 VERSIONS.md v2.9.7「補齊漏列依賴」條目）。
2. `anthropic`/`openai`/`groq` 也都明確列出（win-stable:13-15），不會有引擎切換時才發現套件沒裝的問題。
3. CUDA 相關套件拆到獨立檔案並依硬體條件安裝，避免沒有獨顯的機器白白裝 800MB 用不到的函式庫。

**仍然沒解決的問題（與 main 分支相同）**：所有套件都只給下限（`>=`），**沒有任何上限鎖定**，理論上 `pip install` 抓到未來的 breaking change 版本一樣有風險（main 分支對 `mlx` 有版本上限鎖定的最佳實踐，這裡完全沒有對應措施套用到 `faster-whisper`/`PyQt6` 等套件上）。`pystray` 被列在 `requirements-win.txt:2`，但 `ui/tray_manager.py`（win-stable）已經完全改用 `QSystemTrayIcon`（PyQt6 內建），**沒有任何地方 import `pystray`**（已 grep 驗證）——這是一個多餘依賴，`pystray` 這個套件會被安裝但用不到，屬於清理項而非風險項。

### setup_win.bat / release_win.ps1 / voicetype_installer.iss 打包鏈

三條打包路徑都存在且相對完整，這是 win-stable 相對 main 分支最大的優勢之一：

1. **`setup_win.bat`**（1-140+ 行）：偵測順序是「embedded `.runtime` → `py -3.12/3.11/3.10` launcher → `python` 指令版本驗證（排除 Microsoft Store 假捷徑）→ 都沒有就下載可攜式 Python 或呼叫 winget」，並會跑 `tools/doctor.py` 做環境預檢（磁碟空間/寫入權限/路徑安全/網路連線），再依 `nvidia-smi` 是否存在決定要不要裝 CUDA 函式庫，最後嘗試用系統內建 `csc.exe` 現場編譯 `VoiceType4TW.exe` Starter EXE。這條腳本經過多次版本迭代（VERSIONS.md v2.9.7「Windows Install Hardening」條目記載了完整的問題與修法），成熟度明顯高於「隨手寫的安裝腳本」。
2. **`release_win.ps1`**（1-175 行）：v3.0.1 全面改寫為「自建完整可攜環境」——下載嵌入式 Python、安裝全部依賴、隨附 Whisper medium 模型（`bundled_models/`）、編譯/複製 Starter EXE、產生說明文字檔、用 `tar.exe`（bsdtar，Win10+ 內建，ZIP64 安全）壓縮成 ZIP。支援 `-Lite`（無 CUDA/無模型）與 `-SkipZip` 參數。
3. **`voicetype_installer.iss`**（Inno Setup）：**發現一個真實的打包風險**——`voicetype_installer.iss:44`：
   ```
   Source: "platform_layer\*"; DestDir: "{app}\platform_layer"; Flags: ignoreversion recursesubdirs createallsubdirs
   ```
   但 win-stable 分支的專案根目錄**沒有 `platform_layer` 這個資料夾**（已用 `ls` 驗證不存在）。Inno Setup 編譯器（ISCC）在 `[Files]` 段遇到一個找不到來源、且沒有 `skipifsourcedoesntexist`旗標的條目時，預設行為是編譯失敗並報錯（「Source file not found」一類的錯誤），**不會靜默跳過**。這代表如果現在直接對 win-stable 執行 `iscc voicetype_installer.iss`，大機率無法編譯成功，除非先建一個空的 `platform_layer` 目錄或移除這一行。這應該是專案曾經規劃過的目錄結構重構（把跨平台程式碼抽到 `platform_layer/`）但沒有真的做完、`.iss` 忘記同步清掉的殘留設定。**這是接手後第一批要修的項目之一**（見第 7 節）。

### .gitmodules / submodule 狀態

**win-stable 分支根本沒有 `.gitmodules` 檔案**（已確認 `cat .gitmodules` 回傳「No .gitmodules」）。舊版 REVIEW.md 與本次任務指派的「fetch 時出現 multiple configurations found for 'submodule..aicore.path'」警告，其成因是 **main 分支** 的 `.gitmodules` 裡有重複的 `.aicore`/`jfamily-ai-context` 條目（該 repo 的問題），與 win-stable 分支本身無關——`git fetch` 同時抓取兩個分支時，Git 會合併讀取兩邊的 `.gitmodules` 設定（如果本機 `.git/config` 裡對同一個 path 累積了多次 submodule 設定），這個警告是「fetch 這個動作」層級的訊息，不代表 win-stable 這個分支的樹裡有問題。VERSIONS.md（win-stable，v3.0.0 條目）也證實：`.gitmodules`（子模組不存在）已經在 v3.0.0 的「51 個檔案移除」清單中被移除。**結論：這個警告不是 win-stable 程式碼的問題，是本機 git 設定歷史累積的訊息，可以忽略；且第 7 節提到的主 repo 合併後，`.gitmodules`/`.aicore` 已經不在合併後的樹裡（見「重大發現」一節的 merge diff stat）。**

---

## 5. 測試

### 現況：完全沒有 test_*.py

`find . -iname "test_*.py"` 在 win-stable 分支**沒有任何結果**——main 分支至少有 3 個真正帶斷言的 `unittest.TestCase`（`test_openrouter_fallback.py`/`test_stt_hallucination_filter.py`/`test_stt_language_selection.py`），這 3 個檔案**都沒有被移植或重寫到 win-stable**。win-stable 目前的「測試」完全是手動煙霧測試腳本：

| 檔案 | 型態 | 說明 |
|---|---|---|
| `self_check.py`（1-75 行） | 功能性煙霧測試 | 真的會啟動 `SubprocessWhisperSTT`、等待模型就緒、送假音訊做端到端轉錄驗證（`test_stt_recognition()`, win-stable:13-44），有基本的成功/失敗判斷（`sys.exit(0/1)`），但沒有斷言框架，需要人看輸出或看結束代碼，且會實際下載/載入 Whisper 模型（慢、有網路依賴） |
| `diagnose_mic.py`（1-31 行） | **macOS-only 死碼** | 第 10 行 `if platform.system() != "Darwin": print("Not macOS"); return`——這支腳本在 Windows 上執行只會印出「Not macOS」然後直接返回，**完全不做任何診斷**，是從 Mac 版複製過來但沒有改寫成 Windows 版的殘留檔案。檔名暗示「診斷麥克風」，實際上在目標平台（Windows）上是空殼。 |
| `tools/doctor.py` | 環境預檢（非單元測試） | 磁碟空間/寫入權限/路徑安全/Python 完整性/網路連線 5 項檢查，`setup_win.bat` 安裝流程的一部分，性質上是「安裝前置檢查」，不是程式邏輯測試 |

### 缺口

- 完全沒有涵蓋 `ui/app.py:_process_audio`（核心 pipeline）、`_build_llm_prompt`、`vocab/manager.py:apply_vocab_correction`、`memory/manager.py:_generate_digest`/`maybe_archive`、`config.py:load_config`/`save_config` 拆分邏輯的任何自動化測試。
- `stt/subprocess_whisper.py` 這個全 repo最複雜、風險最高（子程序、CUDA、DLL 注入）的檔案，只能靠 `self_check.py` 手動跑一次端到端驗證，沒有可以在 CI 或無 GPU 環境快速跑的單元測試（例如 mock 掉 `WhisperModel` 測試 IPC 訊息協定本身）。
- `hotkey/listener.py` 的 VK 碼解析邏輯（`code:<N>` 格式解析、字串 fallback 對照表，win-stable:60-74）是純函式邏輯，容易寫單元測試，目前沒有。
- 沒有 CI（`.github/workflows` 不存在，已確認 win-stable 目錄結構裡沒有 `.github`）、沒有 lint/typecheck 設定。
- **正面說明**：`self_check.py` 至少證明作者有「端到端驗證」的意識，且 VERSIONS.md 多個條目（如 v2.9.8「VAD 狀態機單元測試」、v3.0.1「隨附模型安裝邏輯單元測試」）記載了「曾經寫過」單元測試並實測通過的敘述——但這些測試程式碼本身**沒有留在 repo 裡**（不在任何 `test_*.py` 或其他可辨識的測試檔案中），只有 VERSIONS.md 裡的文字紀錄，代表這些測試可能是一次性手動驗證後就被捨棄，而不是留存的自動化回歸測試資產。

---

## 6. 與 main 的版本關係

### Git 拓樸

`git merge-base main win-stable` 在合併前的狀態下 = `b694e40`（win-stable 分支尖端本身）。這代表：**win-stable 與（合併前的）main 分支在很久以前的某個共同祖先之後就完全分岔獨立演進**，win-stable 領先 old-main 19 個獨有 commit，old-main（Mac 純化路線）領先 win-stable 30 個獨有 commit——**兩條線在分岔後幾乎沒有互相 cherry-pick**，是人工「看 VERSIONS.md 對照著重新實作」的同步方式，不是共用 commit 歷史。

`git diff --stat 51094bf b694e40`（old-main HEAD vs win-stable HEAD）：**177 個檔案變更，+4662/-9218 行**——差異規模非常大，符合「两套獨立維護的程式碼庫」的判斷。

### 版本號對照（VERSIONS.md 雙邊互相引用，但程式碼各自實作）

win-stable 的 VERSIONS.md 記錄的里程碑（`v2.7.24-pc-stable` 2026-03-01「Windows 初心版」→ `v2.7.32` 系列「Windows Porting Start」→ `v2.8.x`「雲端同步」/「全功能同步與對齊」→ `v2.9.6`「Mac 版功能移植 + 嵌入式 Python」→ `v2.9.7~v2.9.10`「安裝硬化/VAD 全時模式/UI 精修」→ `v3.0.0`「正式定義 Windows 專用版，移除 51 個 macOS 殘留檔案」→ `v3.0.1`「真可攜版 ZIP」）與 main 分支的 VERSIONS.md（`v2.9.0` Mac 純化 → `v2.9.11` LLM prompt 統一 → `v2.9.13` MLX 版本鎖 → `v2.9.14` MLX GPU thread-safety → `v2.9.15` 幻覺過濾擴充 → `v2.9.16` Coffee Edition）**版本號體系完全平行但獨立**——例如 win-stable 沒有 `v2.9.11`「LLM prompt 統一系統」這個 win-stable 自己的版本號（win-stable 的 `llm/` 目錄下也確實沒有 `prompts.py` 這個檔案，是 `ui/app.py` 頂部直接寫死 `DEFAULT_LLM_PROMPT`/`DEFAULT_ASSISTANT_PROMPT` 兩個字串常數，`ui/app.py:30-51`），也沒有 `v2.9.13~15` 的 MLX 相關內容（win-stable 從來就沒有 `mlx_whisper.py`，不需要這些修復）。

### 回收 main 分支新功能的難度評估

| main 分支功能 | 回收到 win-stable 的難度 | 說明 |
|---|---|---|
| v2.9.11 LLM prompt 統一系統（`llm/prompts.py`，語言感知 fallback） | **低** | win-stable 的 `ui/app.py:30-51` 已經有兩份寫死的 prompt 常數，改成呼叫一個新的 `llm/prompts.py` 模組是直接的重構，7 個 LLM provider 的 `refine()` 介面簽章相容（`text, prompt`），可以逐一移植而不影響行為 |
| v2.9.13 MLX 版本鎖 | **不適用** | win-stable 沒有 MLX（Apple Silicon 專屬），這整套修復對 Windows 分支無意義 |
| v2.9.14 MLX GPU thread-safety lock | **不適用** | 同上，win-stable 的 GPU 隔離走的是完全不同的子程序方案（`subprocess_whisper.py`），架構上已經比 MLX lock 更徹底地解決了「STT 引擎與 GPU 資源的執行緒安全」這個同一類問題，不需要移植 MLX 版的解法 |
| v2.9.15 STT 幻覺過濾擴充（新增英文變體關鍵字、print 轉 logging） | **中** | win-stable 目前**沒有看到獨立的幻覺過濾邏輯**（`ui/app.py:277-416` 的 `_process_audio` 沒有 main 分支 `main.py:487-497` 那種關鍵字比對防護，`stt/subprocess_whisper.py` 也沒有對應 main 分支 `stt/mlx_whisper.py:_is_hallucination` 的邏輯）——**這是一個功能缺口**，不是「回收升級」而是「win-stable 目前完全沒有這個防護，需要從頭補上」，優先度應該提高（短音檔沉默偵測 `ui/app.py:284` 這種基本防呆有，但 Whisper 常見的「幻覺重複句」問題沒有專門處理） |
| v2.9.16 Coffee Edition（README/版本資訊調整） | **低（不太需要）** | 主要是文件/品牌調整，win-stable 有自己的 README 定位（Windows 專用），不需要照搬 |

**整體判斷**：win-stable 與 main 分支在「音訊/GPU 隔離」這個維度上已經走在不同且互不相容的技術路線（子程序 vs MLX class-level lock），沒有回收必要；但在「LLM prompt 治理」與「STT 幻覈過濾」這兩個純邏輯層面的功能上，win-stable 明顯落後 main 分支，且這兩塊都是相對獨立、低風險的模組，值得優先移植。

---

## 7. 接手起點建議

> 如「⚠️ 重大發現」所述，「要不要以 win-stable 為 Windows 開發基底」這個決策已經執行（`main` 分支已合併 `win-stable`，鷹架文件 `AGENTS.md`/`NOTICE.md`/`LICENSE`/`docs/DECISIONS.md` 也已建立）。以下建議直接針對「win-stable 程式碼本身接下來要做什麼」，依高價值低風險 → 大工程排序。

### 立即可做（零風險，高價值）

1. **修掉 `voicetype_installer.iss:44` 的 `platform_layer\*` 死引用**：確認這個目錄過去是否真的規劃過但沒完成，若確定不需要就整行刪除，否則現在打包會在 Inno Setup 編譯階段直接失敗。
2. **修 STT 引擎選單的「Gemini」死路徑**：`stt/__init__.py:6-26` 加一個 `elif engine == "gemini": from .gemini_stt import GeminiSTT; return GeminiSTT(config)` 分支，讓 UI 選項與後端行為一致（目前選了會靜默 fallback，使用者完全不會發現，是個容易讓人誤以為「功能故障」而來回報 bug 的地雷）。
3. **清掉 `requirements-win.txt` 裡用不到的 `pystray`**：`ui/tray_manager.py` 已完全改用 `QSystemTrayIcon`，確認沒有殘留引用後移除這個依賴，減少安裝體積與潛在版本衝突面。
4. **修 `ui/settings_window.py:1086,1154` 的硬編碼 `"Monaco"` 字型**：改成與檔案其他地方一致的 `platform.system() == "Windows"` 判斷式，統一用 `Microsoft JhengHei`（或改用等寬字型如 `Consolas`，程式碼編輯區用等寬字型可能比黑體更合適）。
5. **`diagnose_mic.py` 決定去留**：要嘛刪掉這支對 Windows 完全無作用的死碼，要嘛重寫成真正測試 Windows 麥克風權限/裝置列舉的版本（`sounddevice.query_devices()` 之類）。

### 短期（中等工程量，價值高）

6. **補上 STT 幻覈過濾**：這是目前 win-stable 相對 main 分支最明確的功能缺口（第 6 節）。可以直接參考 main 分支 `stt/mlx_whisper.py:_is_hallucination`/`_has_dominant_repetition` 的邏輯，改寫成一個獨立於 STT engine 的共用檢查函式（例如放進 `stt/base.py` 或新建 `stt/hallucination_filter.py`），在 `ui/app.py:_process_audio` 的 STT 結果之後、詞庫修正之前呼叫。
7. **移植 v2.9.11 LLM prompt 統一系統**：把 `ui/app.py:30-51` 的兩份寫死 prompt 常數搬進獨立的 `llm/prompts.py`，並讓各 provider 的 `refine()` 依語言 fallback——這是 main 分支已經驗證過的架構，可以直接借鏡設計、重新用 win-stable 自己的 7 個 provider 實作，不需要重新設計。
8. **`ui/settings_window.py`（2050 行）拆分**：分頁邏輯拆成獨立檔案/class，降低單檔複雜度（規模比 main 分支的 3046 行版本小，趁現在拆比未來功能長更大之後拆容易）。
9. **補齊 `paths.py:56-58` 死掉的同步常數，或乾脆刪掉**：先跟維護者確認「詞彙/記憶要不要真的做跨裝置同步」，若要，就把 `vocab/manager.py`/`memory/manager.py`/`stats/tracker.py` 改成真的引用 `paths.py` 的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`；若不需要，就把這三個死常數從 `paths.py` 移除，避免未來的接手者被誤導。
10. **補核心邏輯的單元測試**：優先 `hotkey/listener.py` 的 VK 碼解析（純函式，容易測）、`vocab/manager.py:apply_vocab_correction`、`config.py:load_config`/`save_config` 拆分邏輯、`memory/manager.py:_generate_digest`——這些都是 main 分支當年也標記為「零測試覆蓋」的相同類型純函式，且都還沒有被移植成正式測試。
11. **`requirements-win.txt` 補版本上限**：至少對 `faster-whisper`、`PyQt6`、`ctranslate2`（隱性相依）這幾個容易 breaking change 的核心套件加上 `<major.minor` 上限，仿照 main 分支對 `mlx` 的鎖法。

### 中期（較大工程量）

12. **`stt/subprocess_whisper.py`（430 行）補自動化測試**：至少 mock 掉 `WhisperModel` 測試 IPC 訊息協定本身（`transcribe`/`warmup`/`quit` 三種訊息的收發邏輯），不需要真的載入模型也能驗證子程序管理邏輯不會壞掉，比 `self_check.py`（依賴真實下載模型、跑很慢）更適合放進 CI。
13. **導入 CI**：即使只是 GitHub Actions 跑 `python -m unittest discover`（等第 10 項的測試補上後）也好，目前完全沒有自動化執行任何測試。
14. **音訊裝置互斥檢查**：確認 PTT 模式與全時 VAD 模式不會同時開啟兩個 `sounddevice.InputStream`（第 2 節提到的潛在風險），加一個顯式的「二選一」邏輯或至少在 UI 上防呆。

### 大工程（若要往「單一程式碼庫雙平台共用」方向走）

15. **這條路線目前看起來優先度低**：既然維護者已經決定「以 win-stable 為 Windows 開發基底，不走跨平台統一」（`docs/DECISIONS.md`），第三節提到的「HotkeyBackend/TrayBackend 抽象層」大工程建議可以先擱置，除非未來明確要重新支援 macOS。

---

## main 分支對照（前次 review 摘要）

> 以下濃縮自舊版 REVIEW.md（審閱 macOS 主幹 `main` 分支，HEAD `51094bf`，v2.9.16 Coffee Edition）的核心結論，供對照參考。**該次 review 之後，main 分支已被合併進 win-stable（見「⚠️ 重大發現」），故以下內容為歷史紀錄，不代表目前 main 分支的現況。**

- **健康分數**：5.5/10（macOS 環境）／ 2/10（Windows 11 環境）。
- **核心發現**：main 分支自 v2.9.0（2026-03-19）起被明確「Mac 純化」，移除所有 Windows 殘碼；殘留的 `platform.system() == "Windows"` 判斷式是清理不乾淨的痕跡。`hotkey/listener.py` module 層級無條件 `import Quartz`、`ui/tray_manager.py` 無條件 `import rumps`，兩者在 Windows 上都會直接 ImportError 並導致開機崩潰；`requirements.txt` 混雜 macOS-only 套件（`rumps`/`mlx`/`pyobjc-*`）且無平台標記，`pip install` 在 Windows 上直接失敗。**結論：main 分支的 `main.py` 完全無法在 Windows 11 上啟動。**
- **架構亮點**：STT 幻覺過濾（`stt/mlx_whisper.py:_is_hallucination`）、MLX GPU class-level lock、CGEventTap 自癒 watchdog、OpenSSL rpath 修復，都是「認真根因分析後落地」的成熟設計，顯示原作者遇到問題會深挖，不是隨便補丁。
- **安全**：API Key 明碼存放且設計上會同步到使用者自訂雲端目錄（iCloud/Google Drive/NAS）——這點在 win-stable 上依然成立（本次 review 第 3 節已確認）。
- **測試**：6 個 `test_*.py` 中只有 3 個是真正帶斷言的 `unittest`，核心 pipeline（`_process_audio`）零測試覆蓋。
- **打包**：`setup.py`（py2app）+ DMG 打包鏈 100% macOS 專用，在 Windows 上完全不適用。
- **文件**：README 自相矛盾（同時宣稱「原生支援 macOS 與 Windows」又說 Windows 版在獨立分支）；無 LICENSE 檔案——**這兩項在合併後的 main 分支已經處理**（`docs/DECISIONS.md` 2026-07-19：win-stable 的 README 本身已正確定位為 Windows 專用；`LICENSE`/`NOTICE.md` 已新增，採雙軌授權誠實揭露）。
- **當時給的建議路線**：優先修正 README 矛盾、`requirements.txt` 補平台標記、決定「合併 win-stable vs 就地修復」——**這個決策點現在已經執行完畢**，選擇了合併 win-stable。

---

## 風險排序表（嚴重度 × 確定度，針對 win-stable 分支本身）

> **修復回註（2026-07-19）**：本表發現的問題已於同日分兩批修復（commit `04d82cc`..`9192ef6`，均含測試並經 fresh-context 驗收），修復狀態欄如下。修復過程中另揪出並修復兩個本表未列的 bug：
> - **OpenRouter STT 引擎自始壞掉**（與 #2 的 GeminiSTT 同型：簽章不符＋WAV bytes 重複編碼，被 broad except 吞掉永遠回空字串）→ `75952fd`
> - **Claude LLM 引擎自始壞掉**（`llm/claude.py` 讀 `claude_api_key`/`claude_model`，但 config/UI 存的是 `anthropic_*`，永遠拿空 key 靜默回原文）→ `9192ef6`，並加 `tests/test_llm_config_keys.py` AST 靜態掃描鎖住全部 provider 欄位名
> - 另補第 3 節指出的網路逾時缺口（anthropic/groq SDK 無 timeout）→ `eb61819`
>
> **維護慣例：之後每修復本表（或後續 review）列出的問題，須回到本檔在對應項目標註修復 commit 與日期。**
>
> **修復回註（2026-07-20，源自 `docs/mac-mainline-absorption-analysis.md` 16-3 項）**：`ui/app.py:_process_audio` 把翻譯目標語言 `translation_lang` 當 STT 語言 hint 餵給 Whisper——使用者用過一次「翻譯成英文」後，`translation_lang` 留在 config 裡是 `"en"`，之後所有中文錄音的辨識 hint 都被污染成英文。比照 Mac 主線 v2.9.16（`51094bf:stt/language.py`）移植 `stt/language.py:get_transcription_language()`，STT 語言改回讀使用者實際設定的 `config["language"]`，翻譯只影響 LLM 輸出層（`active_scenario` prompt 選擇），不再干擾辨識 → `d99a326`，新增 `tests/test_stt_language_selection.py`。
>
> **修復回註（2026-07-20，智慧詞彙學習對本地辨識無效）**：`stt/subprocess_whisper.py` client 端 `SubprocessWhisperSTT.transcribe()`（約行 356-391）把 `vocab.manager.build_vocab_prompt()` 的結果放進 IPC 訊息的 `"prompt"` 欄位送給子行程 worker，但 worker 端 `_stt_worker` 迴圈過去從未讀取該欄位，永遠用硬編字串「以下是繁體中文的語音內容：」當 `initial_prompt`——詞彙庫學到的專有名詞實際上從未餵進本地 Whisper，智慧詞彙學習對本地辨識完全無效（只剩事後文字修正那半套）。修法：worker 迴圈新增讀取 `msg.get("prompt")`（`stt/subprocess_whisper.py:250-252`），轉交 `_run_transcribe()`（新增 `initial_prompt` 參數，`stt/subprocess_whisper.py:34-42`，空/缺 fallback 回 `DEFAULT_INITIAL_PROMPT` 向下相容）；呼叫點更新於 `stt/subprocess_whisper.py:268`。比照 Mac 版語義（`git show 960f5e6:stt/mlx_whisper.py:128-129,154`；`51094bf` 為對應 Mac 原始碼庫的 commit，於本 repo 歷史中不可達）：`build_vocab_prompt()` 回傳值本身就是完整 `initial_prompt`（取代而非串接）。另查證 `stt/local_whisper.py:46,51` 非 Windows fallback 路徑本來就正確接線（`initial_prompt=prompt` 直接使用 `build_vocab_prompt()` 結果），無需修改。新增 4 個回歸測試於 `tests/test_stt_transcribe_params.py`（預設值、自訂詞彙 prompt 透傳、空/None fallback、worker 原始碼靜態檢查）→ `aee3973`（2026-07-20）。
>
> **修復回註（2026-07-20，Mac 主線吸收收尾批次——13-1/7-5/7-6/11-3 + bug 清理）**：依 `docs/mac-mainline-absorption-analysis.md` 剩餘「可攜」「需改寫」項目逐一吸收，另修復本表第 6 項當時暫留的尾巴。
> - **13-1 LLM system prompt 集中化** → `19017c8`：新增 `llm/prompts.py`，7 個引擎 `refine()` 補 `prompt or get_default_system_prompt(language)` 防禦性 fallback，清掉 4 個引擎重複的硬編中文死屬性。`tests/test_llm_prompts.py`。
> - **7-5 LLM 未啟用時的輕量版靈魂規則** → `da93f62`：新增 `utils/soul_rules.py`（純函式，比照 `audio/gain.py` 抽出模式），`ui/app.py:_apply_basic_soul_rules` 在未使用 LLM 時清除 soul md 定義的贅詞。`tests/test_soul_rules.py`。
> - **7-6 soul 贅詞清單補漏** → `1e53549`：`soul/scenario/default.md` 補「所以說」「就是說」。
> - **11-3 診斷包匯出 + 假 stub 修復** → `7bc3b0f`：新增 `utils/diagnostics.py`（Windows 環境資訊＋裝置清單＋日誌尾段＋脫敏設定 zip 匯出），設定頁新增按鈕。**順手揪出一個本表未列的獨立 bug**：`ui/settings_window.py:_run_mic_test` 內有「非 macOS 一律拒絕」擋板（`platform.system() != "Darwin"` 就彈「此診斷功能目前專為 macOS 設計」），但擋板之後的測試邏輯本來就是跨平台程式碼（連錯誤訊息都是寫給 Windows 隱私權設定看的）——擋板是誤植死碼，導致 Windows 使用者連按鈕都被藏起來。已移除擋板＋取消 Windows 隱藏。`tests/test_diagnostics.py`（13 個測試，在真實 Windows 開發機上直接驗證環境收集邏輯，非 mock）。
> - **本表第 6 項尾巴：`paths.py:AI_PERMANENT_MEMORY_PATH`** → `53a4ef3`：與同批清掉的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 是同一批死碼（皆指向雲端同步目錄、皆零引用），當時因不在指定範圍暫留，本次一併移除。
> - **`vocab/manager.py` 命名混淆修復**（本表第 6 項備註曾提及的撞名風險）→ `27d93c8`：本機常數 `VOCAB_DIR` 改名 `_VOCAB_DATA_DIR`，避免與已移除的雲端同步死碼常數同名混淆。純改名不改行為。
>
> `python -m pytest tests/ -v`：232 passed, 10 skipped（含本批新增 24 個測試：13 個 `test_llm_prompts.py` 相關斷言＋11 個 `test_soul_rules.py`，另 `test_diagnostics.py` 13 個獨立計入）。⚠️ 未實機驗證：`ui/settings_window.py` 的新按鈕接線（本機無 PyQt6）；`utils/diagnostics.py` 的 `collect_env_info`/`collect_device_info`/`export_diagnostic_bundle` 本身已在真實 Windows 11 開發機上直接執行驗證（非模擬），僅 sounddevice 裝置清單因本機未裝該套件而走「未安裝」分支，未覆蓋「真的列出裝置」路徑。

| # | 風險 | 嚴重度 | 確定度 | 證據 | 修復狀態 |
|---|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*`，Inno Setup 打包大機率失敗 | 高（打包鏈斷裂） | 已驗證（目錄確認不存在，Inno Setup 對缺失 Source 預設報錯） | `voicetype_installer.iss:44` | ✅ 已修 `04d82cc`（2026-07-19，其餘 Source 逐條核對存在） |
| 2 | STT 引擎選單「Gemini」選項實際無效，靜默 fallback 到本地 Whisper | 中高（使用者可見的功能性 bug） | 已驗證（讀碼確認 `get_stt()` 無對應分支） | `ui/settings_window.py:24,1002-1010` vs `stt/__init__.py:6-26` | ✅ 已修 `71f0cbe`（2026-07-19，補分派＋修 GeminiSTT 內部簽章與 WAV 重編碼兩個 bug；`tests/test_stt_engine_dispatch.py` 鎖 UI↔實作一致） |
| 3 | 完全沒有幻覺過濾機制，相對 main 分支是功能倒退 | 中高（辨識品質風險） | 已驗證程式碼無此邏輯，未驗證實際辨識品質差異幅度 | `ui/app.py:277-416` 全檔搜尋無 hallucination 相關邏輯 | ✅ 已修 `7bf8592`（2026-07-19，自舊 main 移植成 `stt/hallucination_filter.py`，接 `_process_audio` 統一路徑、全引擎生效） |
| 4 | API Key 明碼且設計上會同步到第三方雲端資料夾 | 高 | 已驗證（與 main 分支相同設計） | `config.py:51-59`、`paths.py:17-45` | ✅ 已修 `cc1e2d1`（2026-07-19，全部 `*_api_key` 改 local-only＋一次性遷移、同步檔即刻改寫落盤） |
| 5 | 完全沒有 `test_*.py`，核心 pipeline 零自動化測試覆蓋 | 中高 | 已驗證 | 第 5 節 | ✅ 已修 `f8633de` 起（2026-07-19 建 `tests/`＋CI，至 `9192ef6` 累計 148 passed） |
| 6 | `paths.py` 宣告的雲端同步路徑（`VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`）是死碼，實際未同步 | 中（誤導性） | 已驗證 | `paths.py:56-58` vs `vocab/manager.py:13,15`、`memory/manager.py:13,15`、`stats/tracker.py:10,12` | ✅ 已修 `c37b286`（2026-07-19，移除死碼；「真同步」記 DECISIONS 為日後功能項） |
| 7 | `ui/settings_window.py`（2050 行）god file | 中 | 已驗證 | 行數/職責統計 | ⏳ 未修（重構級非 bug，待實機跑通後再動） |
| 8 | `requirements-win.txt` 無版本上限鎖定 | 中低 | 已驗證 | `requirements-win.txt` 全檔 | ⏳ 未修（政策調整，待實機驗證相容版本後再鎖） |
| 9 | `diagnose_mic.py` 在 Windows 上是空殼死碼 | 低（誤導性，非功能風險） | 已驗證 | `diagnose_mic.py:10` | ✅ 已修 `0ee2730`（2026-07-19，重寫為真診斷：列裝置＋實錄 RMS，實機驗證通過） |
| 10 | 兩個音訊觸發模式（PTT/VAD）並行時缺乏互斥檢查 | 低中 | 已驗證程式碼無互斥邏輯，未驗證實機是否真的衝突 | `audio/auto_trigger.py` vs `audio/recorder.py` | ✅ 已修 `e33d479`（2026-07-19，`audio/mutex.py` PTT 優先狀態機；實機熱鍵行為待驗） |
| 11 | `eval()` 用於計算機指令 | 低（已有輸入清洗） | 已驗證 | `actions/builtins.py:36-47` | ✅ 已修 `3d2c215`（2026-07-19，ast 白名單解析＋守門測試） |
| 12 | `ui/settings_window.py:1086,1154` 硬編碼 macOS 字型 `Monaco` | 低（視覺不一致，非崩潰） | 已驗證 | 同上 | ✅ 已修 `2e52f87`（2026-07-19，改 Consolas；實機視覺待驗） |

---

*本 review 為針對 win-stable 分支（唯讀 worktree）的純靜態程式碼閱讀分析，未實際安裝依賴或在 Windows 環境執行程式。標記「未驗證」之處代表僅能從程式碼推論、無法在本次審閱中直接證實。worktree 本身未做任何修改；主 repo 僅修改本檔案（`REVIEW.md`），未 commit。*
