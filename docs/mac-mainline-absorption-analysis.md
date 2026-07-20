# Mac 主線 v2.9.6 → v2.9.16 功能吸收分析

> 日期：2026-07-20
> 分析對象：Mac 主線 tip `51094bf`（v2.9.16 Coffee Edition）相對分岔點 v2.9.6（`b9f997b`）的全部變更
> 現樹基準：`main`（win-stable v3.0.1 基底，HEAD `1e77d4f`）
> 性質：純分析報告，未修改任何程式碼

---

## 1. 方法

1. `git show 51094bf:VERSIONS.md` 取逐版紀錄。**發現：Mac 主線的 VERSIONS.md 在 v2.9 區間只補寫了 v2.9.16 一版**，v2.9.7–v2.9.15 沒有寫進 VERSIONS.md（v2.9.16 下一條直接跳 v2.8.2）。因此逐版清單改以 `git log 51094bf` 祖先鏈的 release/feature commit 全文為準（各 commit 訊息非常詳盡，含驗證紀錄）。
2. 對每個 feature/fix 粒度項目，用 `git show 51094bf:<檔案>` 讀 Mac 版實作，對照現樹對應模組後分類：
   - **已存在**：win-stable 已有等效實作或已移植（附現樹檔案:行號證據）
   - **可攜**：邏輯平台無關，近乎直接搬
   - **需改寫**：概念可用但實作綁 Mac API/架構，要重寫接線
   - **不適用**：Mac 專屬，對 Windows 樹無意義
3. 版本號補充說明（git 考證結果）：
   - **v2.9.8 / v2.9.10 沒有獨立 release commit**——它們的產出（`llm/minimax.py`、target_pid 注入）是在 v2.9.11 commit `09e1d2a` 以「carry-over」名義一併入庫的。
   - **v2.9.9 在整個 git 歷史（含 --all）完全無蹤跡**，commit 訊息、VERSIONS.md、AI_MEMORY.md 均未提及，無法確定其內容（可能是未入庫的本機版號跳號）。誠實標註：**無法分析**。
   - **v2.9.12 是緊急發版**（codesign reseal），隨即被 v2.9.13 取代，其內容全數併入 v2.9.13 commit `960f5e6` 分析。
   - 版本號撞名提醒：現樹（Windows）VERSIONS.md 也有一個自己的「v2.9.10」（2026-07-07 Settings UI Refinements），與 Mac 主線的 v2.9.10 **完全無關**，閱讀時勿混淆。

---

## 2. 逐版逐項分析

### v2.9.7（2026-03-21，commits `a91316c` + `2234611`，merge `0225766`）— 麥克風裝置選擇、增益、AGC、靜音偵測、靈魂規則優化

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 7-1 | 麥克風裝置選擇（QComboBox + 2s 插拔輪詢 + 裝置消失 fallback 系統預設） | **已吸收＋commit** ✅ `b54697e`（2026-07-20） | **高** | 中 | `51094bf:audio/recorder.py`（device 參數 + fallback）、`51094bf:ui/settings_window.py`（_populate_mic_devices 等）→ 現樹 `audio/recorder.py`、`ui/settings_window.py` | 織進現樹既有的 callback-based 架構（現樹用 `sd.InputStream(callback=...)`，Mac 版是 polling thread，兩者已分岔，未整檔覆蓋）。`AudioRecorder` 新增 `device` 參數 + 裝置消失 fallback；`config.py` 新增 `mic_device`（LOCAL_KEYS）；`ui/settings_window.py` 新增裝置下拉選單 + 2 秒插拔輪詢。⚠️ 未實機驗證（本機無 PyQt6/sounddevice） |
| 7-2 | 增益控制（實際 PCM 放大，手動 gain 50~300%，slider） | **已吸收＋commit** ✅ `b54697e`（2026-07-20） | 中 | 小（隨 7-1） | 同上，`51094bf:audio/recorder.py:33,101-118` → 現樹 `audio/recorder.py` | 純數學抽成新檔 `audio/gain.py`（無 sounddevice 依賴，可獨立單元測試，`tests/test_audio_gain.py`）。`config.py` 新增 `mic_gain`（LOCAL_KEYS） |
| 7-3 | AGC 自動增益（獨立 `_agc_factor` 依近期峰值動態調整 0.1~8.0×，不覆蓋手動 gain） | **已吸收＋commit** ✅ `b54697e`（2026-07-20） | 中 | 小（隨 7-2） | `51094bf:audio/recorder.py:41-42,120-131` → 現樹 `audio/recorder.py` | 同上併入 `audio/gain.py`。`config.py` 新增 `mic_gain_auto`（LOCAL_KEYS） |
| 7-4 | 靜音偵測（錄音後任一 chunk 峰值 RMS < 0.3% 即整段跳過 STT） | **已吸收＋commit** ✅ `6565fad`（2026-07-20） | 中 | 小 | `51094bf:audio/recorder.py:8,158-163`（is_silent）、`51094bf:main.py:357`（跳過）→ 現樹 `audio/recorder.py` + `ui/app.py:_on_audio_complete` | ⚠️ 與現樹 VAD **不是同一回事**：現樹 `audio/auto_trigger.py` 是「全時自動觸發模式」的語音分段器（RMS 遲滯切段），只在 auto 模式運作；Mac 這個是 PTT/toggle 錄音完成後的「整段靜音預檢」，省一次 STT 呼叫並防幻覺於源頭。兩者互補不重複。實際接線點是 `ui/app.py:_on_audio_complete`（`self.recorder.on_stop` handler），對應 Mac 版 `main.py:_on_record_stop` 的位置，而非 `_process_audio`（後者同時被不共用 recorder 的 VAD 段落佇列呼叫）。峰值 RMS 計算（`peak_rms`/`is_silent`）併入 `audio/gain.py` |
| 7-5 | LLM 未啟用時套用輕量版靈魂規則（`_apply_basic_soul_rules`：解析 soul md「贅詞清除規則」區段動態抽詞、移除贅詞/句號） | **已吸收＋commit** ✅ `da93f62`（2026-07-20） | 中 | 小~中 | `51094bf:main.py:709-745` → 現樹 `utils/soul_rules.py`（新檔，純函式）+ `ui/app.py:_apply_basic_soul_rules`（讀檔 wrapper） | 純字串解析/刪除邏輯抽成 `utils/soul_rules.py`（無 PyQt6 依賴，可單元測試，比照 `audio/gain.py` 模式），`ui/app.py` 在 `is_llm_used` 為 False 時對 `output_content`/`final_text` 套用。新增 `tests/test_soul_rules.py`（11 個測試） |
| 7-6 | soul/scenario/default.md 贅詞清單加「所以說」「就是說」 | **已吸收＋commit** ✅ `1e53549`（2026-07-20） | 低 | 極小 | `51094bf:soul/scenario/default.md` → 現樹 `soul/scenario/default.md` | 已比對：現樹該檔贅詞區段（default.md:29-38）缺「所以說」「就是說」這一行，其餘相同。一行之差，已補上 |
| 7-7 | 設定頁 QGridLayout 對齊、白色 slider QSS、warmup 進度條 + Dashboard mic info card | **需改寫** | 低 | 中 | `51094bf:ui/settings_window.py` → 現樹 `ui/settings_window.py` | 現樹設定頁已大幅分岔（Windows 版自己迭代過 Settings UI Refinements），Mac 的佈局 patch 無法直接套；且 fake progress timer 在 Mac 自己也因 SIGSEGV 回退過（`1e8e837`）。建議只在做 7-1 時順手參考版面，不單獨吸收 |

### v2.9.8（無獨立 commit，隨 `09e1d2a` 入庫）— MiniMax LLM 引擎

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 8-1 | MiniMax LLM 引擎（`llm/minimax.py`，40 行，httpx 呼叫 MiniMax chat API） | **可攜** | 低~中 | 小 | `51094bf:llm/minimax.py` → 現樹 `llm/minimax.py`（新檔）+ `llm/__init__.py` + `config.py` + `ui/settings_window.py` | 純 HTTP API，平台無關。現樹 `llm/__init__.py` 引擎清單無 minimax。價值取決於維護者是否用 MiniMax；不用就不必搬 |

### v2.9.9 — 無法確定

git 歷史（含 --all）、VERSIONS.md、AI_MEMORY.md 均查無此版內容，無法分析。合理推測為未入庫的跳號。

### v2.9.10（無獨立 commit，隨 `09e1d2a` 入庫）— target_pid 精準注入

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 10-1 | 注入改 `CGEventPostToPid` 指定目標行程（錄音前記住前景 app 的 pid，貼上時精準送達，修 auto-paste 貼錯視窗；GitHub Issue #8） | **需改寫** | 中 | 中 | `51094bf:output/injector.py`、`51094bf:actions/dispatcher.py` → 現樹 `output/injector.py` | CGEventPostToPid 是 macOS API。Windows 等效概念 = 錄音開始時記 `GetForegroundWindow()` hwnd，注入前若前景已變則 `SetForegroundWindow(hwnd)` 再 SendInput。現樹 injector 是 pyperclip + Ctrl+V 直貼「當下前景」（output/injector.py:12-21，inject 無 target 參數），長轉錄期間切視窗會貼錯地方——同類問題在 Windows 一樣存在。需全新 Win32 接線，僅概念可搬 |

### v2.9.11（2026-04-22，commit `09e1d2a`）— CGEventTap 自癒 + 崩潰診斷管道

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 11-1 | CGEventTap 三層自癒（timeout re-enable、5s watchdog、reset_state） | **不適用** | — | — | `51094bf:hotkey/listener.py` | 針對 macOS「event tap callback 太慢被系統靜默停用」的專屬病，Windows 的 Win32 低階 hook（現樹 `hotkey/listener.py`）沒有同一失效模式（Win32 hook 超時被移除是另一種病，且現樹用的是輪詢/RegisterHotKey 式架構）。不搬 |
| 11-2 | Keystrike log 改 queue + writer thread（callback 不做檔案 I/O） | **不適用** | — | — | `51094bf:hotkey/listener.py` | 動機是避免 tap callback 超時（11-1 的配套）。現樹 hotkey 日誌量小且無 callback 超時懲罰機制，無此需求 |
| 11-3 | 崩潰診斷管道：`utils/diagnostics.py`（環境收集 + 一鍵匯出診斷 zip）、faulthandler 寫 debug.log、boot step breadcrumb、設定頁「匯出診斷包」按鈕 | **已吸收＋commit** ✅ `7bc3b0f`（2026-07-20） | 中~高 | 中 | `51094bf:utils/diagnostics.py`（259 行）、`51094bf:main.py` → 現樹 `utils/diagnostics.py`（新檔）+ `ui/settings_window.py` | Windows 化改寫：`collect_env_info()` 用 `platform.win32_ver()` + ctypes `GlobalMemoryStatusEx`（取代 Mac 的 sysctl/system_profiler）；新增 `collect_device_info()` 沿用 `diagnose_mic.py` 的 `sd.query_devices()` 邏輯；crash report 改收現樹既有的 `main_crash.log`（main.py:89-94 的 faulthandler 輸出，本來就存在只是從未打包過）。設定頁新增「📦 匯出診斷包」按鈕。**boot step breadcrumb 未做**（main.py 未新增啟動階段記錄點，僅沿用既有 faulthandler + debug.log）。**順手修復**：原本的「系統診斷」按鈕 stub（settings_window.py，按下彈「此診斷功能目前專為 macOS 設計」）其實是 `_run_mic_test` 內誤植的擋板，其後的測試邏輯本來就跨平台——已移除擋板、恢復按鈕（不再是假功能）。新增 `tests/test_diagnostics.py`（13 個測試，在真實 Windows 開發機上直接驗證環境收集函式，非 mock） |

### v2.9.12（緊急版，內容併入 v2.9.13）＋獨立修復 `27d697c`

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 12-1 | codesign sealed-resources reseal（`post_build_fix.py`） | **不適用** | — | — | — | macOS 簽章專屬 |
| 12-2 | libssl 寫死 Homebrew 路徑修復（install_name_tool rpath） | **不適用** | — | — | `27d697c` | macOS dylib 專屬 |

### v2.9.13（2026-05-14，commits `960f5e6` + `fb596f9`）— MLX pin + 幻覺過濾 + 統一 prompt

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 13-1 | 統一 LLM prompt 系統：`llm/prompts.py` 集中 SYSTEM_PROMPTS（zh/en/ja）+ 所有引擎 refine() 用 `prompt or get_default_system_prompt(language)` fallback，避免空 prompt 進 API 造成幻覺 | **已吸收＋commit** ✅ `19017c8`（2026-07-20） | 中 | 小 | `51094bf:llm/prompts.py`（35 行）+ 各 `51094bf:llm/*.py` 的 fallback pattern → 現樹 `llm/prompts.py`（新檔）+ 現樹 7 個引擎檔 | 純 Python，平台無關，搬時引擎清單對齊現樹 7 個（無 minimax，claude 欄位名沿用 `9192ef6` 修過的 `anthropic_*`，未蓋掉）。清掉 openrouter/gemini/qwen/deepseek 四檔重複的硬編中文 `self.prompt` 死屬性（原本就從未被 `refine()` 使用）。`refine()` 簽章與現樹既有 payload 差異（temperature、指令前綴）不變。新增 `tests/test_llm_prompts.py` |
| 13-2 | Whisper transcribe 加 `no_speech_threshold=0.6` + `condition_on_previous_text=False` | **已吸收＋commit** ✅ `486ef3f`（2026-07-20） | **高** | 小 | `51094bf:stt/mlx_whisper.py` → 現樹 `stt/subprocess_whisper.py:240-244`（faster-whisper 同名參數）、`stt/local_whisper.py:46` | 這是幻覺**源頭**抑制（黑名單過濾是下游補刀），faster-whisper 的 `transcribe()` 支援完全相同的參數名。`subprocess_whisper.py` 的呼叫抽成獨立 `_run_transcribe()` 供 mock 測試。⚠️ `condition_on_previous_text=False` 與現樹 `initial_prompt` 的實際互動效果未在真實模型上實測（本機無法起真實 faster-whisper 推論），僅驗證參數確實有傳入 |
| 13-3 | Whisper YouTube 結尾幻覺黑名單（30+ 中文片語，`_is_hallucination` 初版） | **已存在** | — | — | `51094bf:stt/mlx_whisper.py` → 現樹 `stt/hallucination_filter.py` | 現樹已移植且更完整：片語表在 `stt/hallucination_filter.py:22-51`，接線在 `ui/app.py:319-327`（統一路徑，對本地與雲端引擎都生效，比 Mac 版只掛在 MLX 引擎內更好）。模組 docstring 自述即為此移植（hallucination_filter.py:1-16） |
| 13-4 | default `llm_engine` 由 ollama 改 openrouter（ollama 幻覺較嚴重） | **可攜** | 低 | 極小 | `51094bf:config.py` → 現樹 `config.py:15`（現值仍為 `"ollama"`） | 一行。但屬產品決策：Windows 使用者若無 OpenRouter key，openrouter 引擎會直接 return 原文，體驗未必較好。建議與維護者確認再改 |
| 13-5 | MLX 版本 pin（>=0.29,<0.30）+ `scripts/pre_build_check.py` build 守衛 + metallib 檢查 | **不適用** | — | — | — | MLX/Metal 專屬。「build 前依賴守衛」概念雖好，現樹打包鏈（release_win.ps1）無同類 OS 相容性斷崖，暫無對應痛點 |
| 13-6 | pack_dmg ditto、entitlements、Gatekeeper 文件更新 | **不適用** | — | — | — | macOS 打包/簽章專屬 |
| 13-7 | warmup() 改 noop | **不適用** | — | — | — | MLX C-level abort 專屬考量；現樹 subprocess_whisper 的 warmup 是隔離子行程且有效，不應改 |

### v2.9.14（2026-05-14，commit `7f4fbc9`）— MLX Whisper GPU thread-safety lock

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 14-1 | class-level `_gpu_lock` 包住 MLX transcribe/warmup（修兩 daemon thread 並發轉錄 SIGSEGV，Issue #6） | **不適用**（附註） | — | — | `51094bf:stt/mlx_whisper.py` → （無直接對應） | MLX/Metal command queue 專屬。**附註（無法完全確定）**：現樹 subprocess_whisper 走 pipe IPC，若熱鍵路徑（每段錄音開一個 `threading.Thread`，ui/app.py:294）與全時模式 segment worker 同時 transcribe，pipe 讀寫理論上也可能交錯；現樹有 `audio/mutex.py` RecordingMutex 抑制模式並發（tests/test_recording_mutex.py 有測試），實際風險評估需另行實測，本報告不下定論。若日後出現並發轉錄崩潰/串音，可回頭參考此 commit 的「class-level 序列化」思路 |

### v2.9.15（2026-05-14，commits `3b39dee` + `55238d7`）— 幻覺過濾英文擴充

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 15-1 | 幻覺片語黑名單擴充 30+ 英文片語（Thank you for watching / subscribe / Amara.org…）+ lowercase 正規化 rename | **已存在** | — | — | `51094bf:stt/mlx_whisper.py` → 現樹 `stt/hallucination_filter.py:33-46` | 現樹片語表已含全部英文片語（thank you for watching、subscribe 系列、amara.org、mbc뉴스 等），與 Mac v2.9.16 最終版一致 |
| 15-2 | `_is_hallucination` 三階段判定（整段命中／拆句全黑／忽略 ≤2 字元雜訊後全黑）+ `_SENTENCE_SPLIT` 中英標點拆句 | **已存在** | — | — | 同上 → 現樹 `stt/hallucination_filter.py:97-108`（三階段）+ `:54`（拆句 regex） | 逐行比對一致 |
| 15-3 | stt 的 `print` 改 `log.info`（過濾事件進 debug.log） | **已存在** | — | — | 同上 → 現樹 `ui/app.py:322`（`log.info(f"[process] Hallucination filtered: ...")`） | 現樹過濾接線本來就用 logging |
| 15-4 | 設定頁模型順序改 Small → Medium → Large（`55238d7`，MODEL_META dict 順序） | **不適用** | — | — | `51094bf:ui/settings_window.py` | 現樹設定頁無 `MODEL_META` 同構結構（grep 無此符號），Windows 版模型選擇 UI 已自行分岔，Mac 的一致性 bug 不存在於現樹 |

### v2.9.16（2026-07-08，commit `bc574d5`）— 長靜音幻覺與翻譯模式污染修復

| # | 項目 | 分類 | 價值 | 工作量 | 來源檔 → 目標檔 | 備註 |
|---|------|------|------|--------|----------------|------|
| 16-1 | 長靜音幻覺：`_has_dominant_repetition` 高比例重複 token/n-gram 偵測（「通過」連發、anterior access 長尾） | **已存在** | — | — | `51094bf:stt/mlx_whisper.py` → 現樹 `stt/hallucination_filter.py:58-79`（函式本體）+ `:109-111`（第 5 階段接線） | 逐行比對一致（含 n=1..4、repeats>=8、佔比 0.65 門檻）。tests/test_stt_hallucination_filter.py 也已在現樹 |
| 16-2 | 「多謝您的觀看」等中文/粵語結尾片語擴充 | **已存在** | — | — | 同上 → 現樹 `stt/hallucination_filter.py:25-26` | 六個「多謝」變體全數在列 |
| 16-3 | STT 語言選擇修復：新增 `stt/language.py:get_transcription_language()`，STT 語言改用 `config.language`，不再被 `translation_lang=en` 污染（翻譯是 LLM 輸出層的事，餵給 Whisper 會讓中文聽寫後半段漂成英文） | **已吸收/已修** ✅ `d99a326`（2026-07-20） | **高** | **極小** | `51094bf:stt/language.py`（7 行新檔）+ `51094bf:main.py:475-476` → 現樹 `stt/language.py`（新檔）+ `ui/app.py:307` | **現樹有一模一樣的 bug**：`ui/app.py:307` 原本是 `lang = self.config.get("translation_lang", "zh")` 後直接餵 `self.stt.transcribe(audio_data, language=lang)`。使用者只要用過「翻譯成英文」模式，之後所有中文錄音的 STT 語言 hint 都是 en。已比照 Mac 修法搬入 `stt/language.py`（7 行新檔）+ `ui/app.py:307` 改 1 行 + 移植既有測試 `tests/test_stt_language_selection.py`，`REVIEW.md`/`CHANGELOG.md` 已回註 |
| 16-4 | OpenRouter 模型 fallback 鏈：`OPENROUTER_FALLBACK_MODELS` 5 模型依序重試 + `_is_missing_model_error()`（400/404 + no endpoints found 等字樣才 fallback）+ default model `google/gemini-2.0-flash-001` → `google/gemini-2.5-flash` + 設定頁 PROVIDER_MODELS 下拉清單 | **已吸收＋commit（部分）** ✅ `146f104`（2026-07-20） | **高** | 小 | `51094bf:llm/openrouter.py` + `51094bf:config.py` + `51094bf:ui/settings_window.py`（PROVIDER_MODELS）+ `51094bf:test_openrouter_fallback.py` → 現樹 `llm/openrouter.py`、`config.py:25`、`tests/` | fallback 鏈 + default model 已搬，保留現樹既有 payload 差異（`temperature: 0.1`、注入指令前綴）不對齊 Mac 版整檔覆蓋。**settings 頁 PROVIDER_MODELS 下拉清單仍未做**——現樹目前對任何 LLM 供應商都沒有逐模型下拉選單（只有引擎選擇 + API Key 欄位），維持既有決策不做。**13-1（prompts.py）已於 2026-07-20 收尾批次補上**（`19017c8`，見上方 13-1 列），當時「刻意不吸收」只是批次範圍界線，非技術上不值得做 |
| 16-5 | 模型搬遷：HF cache 搬外部模型快取目錄 + symlink | **不適用** | — | — | — | MLX/HuggingFace cache + macOS symlink 情境。現樹已有自己的 `bundled_models/` 隨附模型機制（paths.py `_install_bundled_models()`），需求已被不同方式滿足 |

---

## 3. 特別確認：現樹實況（避免誤判「缺」）

| 確認項 | 現樹實況 | 證據 |
|--------|----------|------|
| 麥克風裝置選擇 | **無**。recorder 用系統預設裝置，無 device 參數 | `audio/recorder.py:56-62`（`sd.InputStream` 無 device）；設定頁僅唯讀顯示裝置名 `ui/settings_window.py:846` + mic test `:1447` |
| 增益 / AGC | **無**。無 gain、無 `_agc_factor`（grep 全檔無） | `audio/recorder.py` 全文 125 行無相關程式碼 |
| 靜音偵測（跳過 STT） | **無等效**。現樹 `audio/auto_trigger.py` 的 VAD 是「全時模式的語音分段器」（何時開始/結束一段），不是「錄音完成後整段靜音就不送 STT」的預檢；PTT 路徑只有 `len(audio_data) < 8000` 長度守衛 | `audio/auto_trigger.py:1-12`（docstring 自述分段用途）、`ui/app.py:304-306` |
| `llm/prompts.py` 集中化 | **無**。各引擎自帶硬編中文 default prompt，無多語 fallback | `llm/` 目錄無 prompts.py；`llm/openrouter.py:10` 硬編中文 prompt |
| 幻覺過濾 | **已存在且為最終版**（含 v2.9.15 英文擴充 + v2.9.16 重複偵測/多謝片語），且接線位置比 Mac 版更好（統一路徑，所有 STT 引擎生效） | `stt/hallucination_filter.py` 全檔、`ui/app.py:319-327`、`tests/test_stt_hallucination_filter.py` |
| STT 語言選擇 | **有 v2.9.16 修掉的那個 bug**（translation_lang 污染 STT 語言） | `ui/app.py:307` |
| 詞彙（vocab）功能 | **Windows 樹較新**：`_edit_distance_1` 已支援替換/插入/刪除（Mac 版僅等長替換）。Mac 自 v2.9.6 後未再動 vocab | `vocab/manager.py:172` vs `git show 51094bf:vocab/manager.py`；`git log 51094bf -- vocab/manager.py` 最後改動即 `b9f997b`（v2.9.6） |
| 記憶（memory）功能 | **Windows 樹較新**：多了 `delete_entry()`、`clear_summary()`。Mac 自 v2.9.6 後未再動 memory | `memory/manager.py:133-150` vs `git diff 51094bf HEAD -- memory/manager.py` |
| 崩潰診斷 | **部分存在**：faulthandler 已啟用寫 `main_crash.log`；但無環境收集/診斷 zip，設定頁診斷按鈕是 macOS-only stub | `main.py:89-94`、`ui/settings_window.py:1991` |

結論：詞彙與記憶兩塊**沒有任何 Mac 主線 post-v2.9.6 變更可吸收**（方向相反，是 Windows 樹在前）。

> **2026-07-20 更新（第一批）**：上表「麥克風裝置選擇」「增益 / AGC」「靜音偵測（跳過 STT）」三列的「現樹實況：無」已因 `b54697e`/`6565fad` 過時——現樹已補上對應功能（`audio/recorder.py` + `audio/gain.py` + `ui/settings_window.py` + `config.py`），詳見第 2 節 7-1/7-2/7-3/7-4 各列與 `docs/DECISIONS.md` 2026-07-20 條目。
>
> **2026-07-20 更新（收尾批次）**：「`llm/prompts.py` 集中化」與「崩潰診斷」兩列也已過時——`llm/prompts.py` 已建立（`19017c8`，7 個引擎補 fallback）；崩潰診斷已補上 `utils/diagnostics.py`（`7bc3b0f`，環境資訊＋裝置清單＋日誌＋脫敏設定 zip 匯出），設定頁「系統診斷」按鈕的 macOS-only stub 也已移除（該 stub 其實是 `_run_mic_test` 內誤植的擋板，測試邏輯本身早就是跨平台的）。詞彙/記憶兩列現況不變（Windows 樹仍領先）。

---

## 4. 分類統計

| 分類 | 項數 | 項目編號 |
|------|------|----------|
| 已存在 | 6 | 13-3、15-1、15-2、15-3、16-1、16-2 |
| 可攜 | 11 | 7-1、7-2、7-3、7-4、7-5、7-6、8-1、13-1、13-2、13-4、16-3、16-4 中扣除→實為 12，見下註 |
| 需改寫 | 3 | 7-7、10-1、11-3 |
| 不適用 | 10 | 11-1、11-2、12-1、12-2、13-5、13-6、13-7、14-1、15-4、16-5 |
| 無法確定 | 1 | v2.9.9（整版無紀錄） |

註：可攜實數 **12** 項（7-1、7-2、7-3、7-4、7-5、7-6、8-1、13-1、13-2、13-4、16-3、16-4）。14-1 歸不適用但附有「現樹並發轉錄風險未定論」的誠實註記。

---

## 5. 建議吸收順序（高價值低風險在前）

1. **16-3 STT 語言選擇修復**——現樹有一模一樣的 bug（`ui/app.py:307`），7 行新檔 + 1 行改動 + 現成測試，零風險高實益，應立刻吸收。✅ **已吸收＋commit** `d99a326`（2026-07-20）
2. **13-2 Whisper 轉錄參數（no_speech_threshold + condition_on_previous_text）**——幻覺源頭抑制，faster-whisper 同名參數，兩行改動；與現有 `initial_prompt` 的互動需附實測。✅ **已吸收＋commit** `486ef3f`（2026-07-20）
3. **16-4 OpenRouter fallback 鏈 + default model 更新**——現樹 default `google/gemini-2.0-flash-001` 有淘汰失效風險，fallback 鏈是純 HTTP 邏輯，測試檔現成；注意與現樹 payload 差異逐段合併。✅ **已吸收＋commit（部分）** `146f104`（2026-07-20）——fallback 鏈 + default model 已搬，PROVIDER_MODELS 下拉 UI 未做（現樹無此 UI 慣例）
4. **7-1（+7-2、7-3）麥克風裝置選擇 + 增益 + AGC**——本區間唯一的大型可攜功能，sounddevice 跨平台，Windows 多麥克風場景實益高；工作量中（UI 接線要適配現樹設定頁），建議 recorder 邏輯先搬、UI 分段做。✅ **已吸收＋commit** `b54697e`（2026-07-20，未實機驗證）
5. **7-4 靜音偵測（錄音後 RMS 預檢跳過 STT）**——與幻覺過濾互補（省一次 STT 呼叫），邏輯十幾行；可與 7-1 同批搬 recorder。✅ **已吸收＋commit** `6565fad`（2026-07-20）

次梯隊（有價值但不急）：13-1 prompts.py 集中化（與 16-4 同檔交會，建議同批做）、7-5 LLM-off 輕量靈魂規則、11-3 診斷包匯出（需改寫成 Windows 收集項，現成 UI stub 接點）、7-6 soul 贅詞兩詞（順手即可）。

> **2026-07-20 收尾批次**：次梯隊四項全部完成——13-1 ✅ `19017c8`、7-5 ✅ `da93f62`、11-3 ✅ `7bc3b0f`、7-6 ✅ `1e53549`。至此，本報告「可攜」「需改寫」兩類（共 15 項）除第 6 節「建議不吸收清單」明確列出的 8-1／13-4／10-1／7-7（已隨 7-1 一併處理，無需單獨吸收）外，全數已吸收或已有明確處置。

## 6. 建議不吸收清單

| 項目 | 理由 |
|------|------|
| 11-1 CGEventTap 自癒、11-2 keystrike queue | macOS event tap 專屬失效模式，Windows hook 架構無此病 |
| 12-1/12-2/13-5/13-6/13-7 全部打包鏈修復（codesign、libssl、MLX pin、entitlements、warmup noop） | macOS 簽章/MLX/dylib 專屬 |
| 14-1 MLX GPU lock | 無 MLX；現樹如日後出現並發轉錄問題再參考其序列化思路 |
| 15-4 模型順序 UI 修復 | 現樹 UI 已分岔，無同構矛盾 |
| 16-5 模型外部快取 symlink | 現樹 bundled_models 機制已用不同方式滿足需求 |
| 10-1 target_pid 注入 | 不建議「不吸收」但降級：概念值得（Windows 也會貼錯視窗），惟需全新 Win32 實作且有 SetForegroundWindow 限制地雷，建議等使用者實際回報貼錯視窗再立項 |
| 13-4 default engine 改 openrouter、8-1 MiniMax 引擎 | 產品決策/依維護者實際使用習慣而定，技術上可攜但預設值變更需維護者拍板 |

## 7. 無法確定 / 誠實聲明

- **v2.9.9**：整個 git 歷史無任何紀錄，內容不明。
- **14-1 附註**：現樹熱鍵路徑與全時模式是否可能真正並發呼叫 subprocess_whisper 的 pipe，本報告只做了靜態閱讀（RecordingMutex 存在且有測試），未做動態驗證，不下定論。
- **13-2**：`condition_on_previous_text=False` 與現樹 `initial_prompt` 的交互作用（faster-whisper 中 initial_prompt 在該設定下仍對每個 window 生效與否）需吸收時實測確認。
- 本報告基於 commit 訊息 + 原始碼靜態比對，Mac 版各功能的實際行為未在 macOS 上執行驗證（本機為 Windows）。
