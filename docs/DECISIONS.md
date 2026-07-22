# Decisions

本專案（fork）的重要決策紀錄（新到舊）。每筆記：日期、決定、理由。與 [`DEVELOPMENT.md`](DEVELOPMENT.md) 的「怎麼做」互補，這裡記「為什麼」。

> **關於歷史 commit hash**：v3.1.0 發版時 fork 開發歷史已 squash 成單一 commit（`84d1b28`）。本檔引用的更早 hash 屬 squash 前的開發過程紀錄，已不存在於 git 歷史，僅作文件內識別碼保留。

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
