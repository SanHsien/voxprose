# Decisions

本專案（fork）的重要決策紀錄（新到舊）。每筆記：日期、決定、理由。與 [`DEVELOPMENT.md`](DEVELOPMENT.md) 的「怎麼做」互補，這裡記「為什麼」。

> **關於歷史 commit hash**：v3.1.0 發版時 fork 開發歷史已 squash 成單一 commit（`84d1b28`）。本檔引用的更早 hash 屬 squash 前的開發過程紀錄，已不存在於 git 歷史，僅作文件內識別碼保留。

## 2026-07-22 — 上游 main 分支 805b007 審視：吸收 3 項平台無關修正，推進 3.3.0

上游 `jfamily4tw/voicetype4tw-mac` `main` 分支新 commit `805b007`（v2.9.18「mac apple local correction」，2026-07-21）審視完畢。此 commit 主體是 macOS 26 裝置端 LLM（Apple Foundation Models）校正功能，但夾帶三項與平台無關、對本 fork 有實際價值的修正。

### 採用

1. **`vocab/manager.py` 模糊比對短 ASCII 縮寫守衛**：`apply_vocab_correction()` 對 4 字以下純 ASCII 縮寫（STT/PTT/API 等）做 edit-distance-1 模糊修正太激進，會把使用者詞庫裡另一個縮寫誤植進來（例：詞庫有 PTT，講 STT 卻被改成 PTT）。這是本 fork 自己樹上結構相同的既有 bug（`apply_vocab_correction`／`_edit_distance_1` 與上游修法前版本邏輯一致），不是「上游獨有問題」，直接移植上游的守衛條件 `len(vocab_word) <= 4 and vocab_word.isascii() and vocab_word.isalnum()`。
2. **OpenCC 簡體→繁體後處理**：Whisper 偶爾把中文誤判輸出成簡體，本產品定位是繁體中文工具，簡體輸出對使用者而言就是辨識錯誤。上游把這段轉換嵌在 macOS 專屬的 Apple Local LLM 校正流程（`llm/apple_local.py:_to_traditional()`）內，我們沒有那個平台專屬功能——**不直接搬移該檔案**，而是把「簡轉繁」這個概念獨立抽成通用模組 `utils/zh_convert.py`，接在 `ui/app.py:_process_audio` 的統一路徑（幻覺過濾之後、詞彙修正之前），對所有 STT 引擎一視同仁生效。
   - **OpenCC 設定檔選 `s2t`（純簡轉繁）而非 `s2twp`**：後者會額外把大陸慣用詞轉換成台灣慣用詞（例如「軟件」→「軟體」），已經觸及詞彙選字層，可能與使用者在 `vocab/manager.py` 自訂的詞彙/慣用語衝突，超出「修正 Whisper 誤判簡體」這個單純目的。
   - **新增設定開關 `zh_convert_enabled`（預設 `True`）不列入 `LOCAL_KEYS`**：這是文字處理行為偏好，跟 `memory_enabled`/`llm_enabled` 同類——不是像 hotkey／麥克風裝置那樣「換一台機器就該重設」的機器特定設定，值得跨裝置同步。
   - **`opencc-python-reimplemented` 為選用依賴**：`utils/zh_convert.py` 未安裝時優雅降級為原樣返回文字，不拋錯、不擋主流程。已在裝有 opencc 的環境（`pip install opencc-python-reimplemented`）實測兩組 Whisper 常見簡體誤判詞彙（「列進來」「協助開發者」對應的簡體寫法）皆正確轉為繁體；本文件與 `utils/zh_convert.py`/`tests/test_zh_convert.py` 刻意不逐字寫出簡體樣本原文，因本 repo 有全文掃描的簡體字守門測試（`tests/test_brand_and_charset_guard.py`），測試檔改以 `chr()` 碼點組字避免誤觸發。
3. **`load_all_learned_words()` 排序穩定化**：排序 key 由 `-count` 改為 `(-count, word.casefold(), word)`，次數相同的學習詞彙不再依賴 dict 插入順序，UI 清單顯示次序具確定性。我們的對應函式行為與上游修法前完全一致，直接移植同一 key。

### 不採用（Mac 專屬／個人化）

- Apple Foundation Models 整套：`helpers/apple_local_llm.swift`＋編譯後二進位、`llm/apple_local.py`、`llm/__init__.py` 註冊、UI 選單/設定開關、`main.py` 接線——macOS 26 裝置端 LLM，Windows 無對應物。
- Mac 打包鏈：`build_all.sh`、`pack_dmg.sh`、`setup.py`、`paths.py` 的 Mac 路徑調整。
- Mac 專屬 UI 改動（`ui/about_window.py`／`ui/menu_bar.py`／`ui/settings_window.py` 的 Apple Local 開關）、Mac 截圖、上游 `VERSIONS.md`／`README.md` 的 Mac 版本敘述。
- `COMMON_ALIAS_CORRECTIONS = {"Talescale": "Tailscale"}`：原作者個人常用詞別名，對本 fork 無普遍價值。
- 「句尾標點保護」：屬 Apple Local helper 內部行為，我們無對應元件。

詳細審視記錄與逐項理由見 `docs/UPSTREAM.md` 的「Skipped（審視後未採用）」表 805b007 條目；`last_reviewed` 已推進至 `805b007`。

### 版本推進 3.3.0

採用項含新功能（OpenCC 後處理）＋新依賴（`opencc-python-reimplemented>=0.1.7,<1`）→ 推進 `paths.py`（`VERSION_NAME`/`BUILD_ID` → `V3.3.0 Windows Edition (BUILD-3300-STABLE)`/`BUILD-3300-STABLE`）、`pyproject.toml`（`version` → `3.3.0`）、`voicetype_installer.iss`（`MyAppVersion` → `3.3.0`，`OutputBaseFilename` → `ShengChengWen-Windows-Setup-v3.3`）。本次**不 tag、不發佈**，版本字串與 `CHANGELOG.md` 先就緒，待驗收後由主 session 決定發版時機。

## 2026-07-22 — 設定視窗署名鏈補正＋Dashboard CUDA 文案誠實化＋截圖重拍

主 session 檢視前次重拍的 7 張截圖時發現兩個問題：`ui/settings_window.py` 側欄署名區塊框架錯誤且不完整、Dashboard 的 CUDA 狀態文案與 STT worker 實際行為矛盾。

### 一、`ui/settings_window.py:274` 署名區塊框架修正

- **問題**：舊文字 `f"{VERSION_NAME}\n\n主要開發者：吉米丘, CC58TW\n協助開發者：Claude Code"` 把原創作者（吉米丘、CC58TW）誤植為本 fork 的「主要開發者」，且完全漏列上游 Windows 專用版維護者 **go-mask** 與本 fork 維護者 **SanHsien**。這是 2026-07-22 稍早「品牌殘留清掃」任務（見上一條目 #23）遺留的缺口——當時只處理了「移除 SNS 個人連結」，`credit_box` 文字本身被明確標註「原封不動」保留，沒有連帶檢查框架是否正確。`ui/about_window.py` 當時已比對確認四層俱全（`derived_label`/`zh_label`/`assist_label`），只有 `settings_window.py` 這處沒同步。
- **決定**：改寫為完整四層署名鏈，比照 `NOTICE.md`／`README.md`／`about_window.py` 的既有措辭：
  ```
  {VERSION_NAME}

  原創：吉米丘、CC58TW
  上游 Win 版：go-mask
  本 fork：SanHsien
  協助：Claude Code
  ```
  分行呈現（側欄版面有限，不用一行塞四個名詞）。`ui/about_window.py:63-81` 檢查後確認四層本來就俱全（`Derived from VoiceType4TW. / Windows fork maintained by SanHsien.` + 中文段落含吉米丘、CC58TW、go-mask + `協助開發者：Claude Code`），不需改動。
- **守門測試**：`tests/test_brand_and_charset_guard.py` 未鎖定 `credit_box` 具體文字內容（只鎖簡體字／舊品牌名／原作者個人網址三類），本次改動不影響其防護力，也不需要調整測試。

### 二、Dashboard CUDA 狀態文案誠實化

- **查證過程**：
  1. `nvidia-smi` 實測：本機確有 NVIDIA GeForce RTX 3060（12GB），驅動 610.62，非「沒有 GPU」的情況。
  2. `venv_real`（`requirements-win.txt` 完整安裝，未裝 `requirements-cuda-win.txt`）內 `ctranslate2.get_cuda_device_count()` 實測回傳 `1`（ctranslate2 4.8.1）。
  3. 讀 `stt/subprocess_whisper.py` 的 worker 邏輯（`_stt_worker`）發現：worker 在 `device in ["auto", "cuda"]` 時會另外用 `ctypes.WinDLL("cublas64_12.dll")` 做硬驗證，失敗就強制 `device = "cpu"`。實測 `venv_real` 裡這個硬驗證確實失敗（`Could not find module 'cublas64_12.dll'`）——因為 `requirements-cuda-win.txt`（`nvidia-cublas-cu12`/`nvidia-cudnn-cu12`）沒裝，`site-packages` 底下沒有 `nvidia/` 目錄可供 DLL 路徑探索。
  4. **結論確認**：這正是備忘錄假設的情況——「有 GPU 但缺 CUDA 函式庫 → 實際無法加速」。`get_cuda_device_count() > 0` 只反映驅動層級「有沒有 CUDA 裝置」，不代表 `WhisperModel(device="cuda")` 真的能載入；舊版 Dashboard 文案（`✅ CUDA GPU × 1 (加速可用)`）與 worker 實際降級行為（CPU + int8）矛盾，是誤導，不是驗證 agent 誤判。
- **決定（新增共用探測模組 `stt/cuda_check.py:probe_cuda()`）**：抽出與 worker 完全相同的判定邏輯（NVIDIA DLL 路徑探索＋`ctypes.WinDLL("cublas64_12.dll")` 硬驗證），回傳 `{"device_count", "accel_available", "reason"}`。`stt/subprocess_whisper.py` 的 `_stt_worker` 硬驗證段落與 `ui/settings/dashboard_page.py` 的 GPU 卡片改為呼叫同一個函式，兩處不再各自維護一套判斷邏輯、不會再各說各話。
- **決定（Dashboard 文案三態）**：`count>0 且 accel_available` → `✅ CUDA GPU × N (加速可用)`；`count>0 但 not accel_available` → `⚠️ 偵測到 GPU × N，但加速不可用（缺 CUDA 函式庫）`；`count==0` → `⚠️ 未偵測到 CUDA GPU (CPU 模式)`。誠實區分「偵測到裝置」與「真的能加速」，不再混為一談。
- **測試**：新增 `tests/test_cuda_check.py`，全部用 mock（`sys.modules["ctranslate2"]`／`ctypes.WinDLL`）覆蓋六種情境（無 ctranslate2、device_count=0、get_cuda_device_count() 拋例外、有裝置但 cuBLAS 載入失敗［本次 bug 真實重現案例］、完全可用、非 Windows 平台保守回應），不打真實硬體，CI（無 GPU 的 windows-latest runner）也能穩定跑。

### 三、意外發現並已修（`tests/test_diagnostics.py` 不穩定斷言）

驗證改動時發現 `test_opens_explorer_to_highlight_zip_on_windows` 在本次任務用的 `venv_real`（uv 安裝的 cpython 3.11.15 embeddable 建置）上必然失敗，與本次任務改動無關——已用 `git stash` 在完全未改動的 HEAD 上重現同樣失敗，確認是既有問題。根因：該測試 patch 的是 `utils.diagnostics.subprocess.Popen`，實際上是整個行程共用的 `subprocess` module 物件；`collect_env_info()` 呼叫的 `platform.platform()`/`platform.uname()`/`platform.win32_ver()` 在這個 Python 建置上會各自呼叫 `platform._syscmd_ver()`，透過 `subprocess.check_output("ver", shell=True, ...)` 取得完整版本號——這些呼叫也被同一顆 mock 攔截計入次數，讓 `mock_popen.assert_called_once()` 必然失敗（實際呼叫 4 次：3 次 `ver` + 1 次 `explorer`）。既然這道 mock 的攔截範圍本來就是行程全域、且此行為隨 Python 建置而異，不是測試想驗證的行為，修法改為在 `call_args_list` 裡篩選開頭是 `"explorer"` 的呼叫、斷言恰好一次，不再對總呼叫次數斷言。因為這個失敗會擋下本次任務要求的「pytest 全綠才能 commit」硬性規則，判斷屬於「阻擋當前任務的既有缺陷」，在本次任務內一併修掉（獨立 commit，不與署名/CUDA 修正混在一起），而非略過或另開任務。

## 2026-07-22 — 品牌殘留全面清掃＋原作者個人網址移除

維護者在實機驗證過程中發現：品牌雖已改名「聲成文 VoxProse」，但程式 UI 仍多處顯示舊名「嘴炮輸入法」，`REVIEW.md` 也混入簡體字（「個人」一詞誤植為簡體）。要求「類似錯誤全都要檢查、改過」。任務進行中維護者追加規格：移除程式 UI 裡所有指向原作者個人社群/贊助頁的連結。

- **UI 品牌殘留（6 處，皆為使用者可見字串）**：`ui/menu_bar.py:36,63`（浮動選單/系統匣選單頂部標籤）改「聲成文 VoxProse」；`ui/settings/dashboard_page.py:40`（Dashboard 頁中文標題 `QLabel`）改「聲成文」；`ui/settings_window.py:467`／`ui/settings/vocab_mem_page.py:154`／`ui/settings/soul_page.py:194`（三處 `QMessageBox` 標題）統一改「聲成文」（比照同視窗其他訊息框慣例，短標題不含英文）。
- **`ui/app.py:98` 歷史版本註解（`v2.8.27_V57`）**：內含舊名雙關語「嘴炮圖案」。原本判斷「非使用者可見、屬歷史版本標記，可保留」；但實作守門測試（見下方）時發現，若保留這一行就必須在測試裡開一個「排除這個檔案這一行」的特例，讓測試邏輯變複雜且出現例外規則。改為兩害相權：直接把註解裡的舊名字面量拿掉（保留版本標記與其餘敘述），讓守門測試可以對 `ui/**` 做無例外的全面掃描，防護力優先於保留這一句歷史調侃的價值。
- **`vocab/manager.py:206` docstring 範例**：原本用「嘴炮輸入法」/「嘴砲輸入法」（一字之差的同音異字）示範模糊詞彙修正功能。改用新品牌的同音例子「聲成文」/「生成文」（聲 vs 生同音，且「生成文」是 STT 對這句話很寫實的誤判方向），維持範例的教學意圖不變，同時清掉舊名。
- **決定（歷史/上游敘述維持不變）**：`NOTICE.md`／`README.md`／`README.en.md`／`LICENSE`／`pyproject.toml` description／`SKILL.md`／`AGENTS.md`／`REVIEW.md` 標題／`CHANGELOG.md`／`VERSIONS.md`（含既有歷史版本條目）裡的「嘴炮輸入法／VoiceType4TW」全部保留原名——這些是描述 fork 出處/歷史沿革的敘述性文字，判準與品牌改名第一/二階段一致，不重複展開。
- **決定（檔名更名：`啟動嘴炮輸入法.bat` → `啟動聲成文.bat`）**：`git mv` 更名，並更新所有引用：`release_win.ps1:68`（release ZIP 檔案清單）、`docs/DEVELOPMENT.md:66,143`（開發者手動啟動說明與目錄樹）。`VERSIONS.md:30,183` 提及舊檔名的兩處維持不動——那是描述「當時做了什麼」的歷史稽核記錄，不因檔案後來改名而回溯竄改。
- **決定（`run_voicetype.bat` 不更名）**：任務要求評估是否一併改名 `run_voxprose.bat`。查證後發現此檔名被 9 個檔案引用，橫跨打包鏈核心（`voicetype_installer.iss` 的 `MyAppExeName`、`create_shortcut.ps1` 偵測邏輯、`setup_win.bat` 的警語文字、`release_win.ps1` 的檔案清單與提示文字、`tools/launcher.cs` 的註解）。判斷不改：(1) 這是內部委派腳本檔名，非使用者可見品牌文案——使用者實際看到的是已改名的 `啟動聲成文.bat`（雙擊入口）與已改名的 `MyAppName`（Start Menu／桌面捷徑顯示名稱），`run_voicetype.bat` 本身從未直接暴露在使用者視野；(2) 若改名，變動面橫跨打包鏈與已編譯工具（`tools/launcher.cs` 需要重新編譯 `VoxProse.exe` 才能驗證委派鏈是否還接得上），本次任務無法在 Windows 實機重新編譯/走完整安裝流程驗證，貿然改名但驗證不到位風險大於收益；(3) 另有 agent 正在同時做實機驗證（跑 `python main.py`／pytest），改動打包鏈檔名容易與其驗證工作互相干擾。維持現狀符合 `AGENTS.md`「不動打包鏈，除非任務明確要求」的既有邊界——本次只被要求「評估」，非「必須改」。
- **決定（`voicetype_installer.iss` 檔名本身不更名）**：同樣評估後判斷不改。理由：(1) 這是 Inno Setup 原始碼腳本，從未隨安裝檔出貨給使用者，使用者只會看到編譯後的安裝檔（`OutputBaseFilename=ShengChengWen-Windows-Setup-v3.2`，品牌已一致），改這個原始檔名對使用者體驗零影響；(2) 這個確切檔名字面量被 `AGENTS.md`／`CLAUDE.md`／`SKILL.md`／`docs/DEVELOPMENT.md`／`CHANGELOG.md`／`VERSIONS.md`／`REVIEW.md`／本檔等 10＋ 處文件當成「打包鏈檔案清單」的固定識別碼引用，改名要同步全部更新，文件面改動成本遠高於實質效益；(3) 沒有任何 CI workflow 引用這個檔名（已 grep `.github/` 確認），技術風險雖低，但文件維護成本仍不成比例。

### 原作者個人網址移除（維護者中途追加規格）

理由：本 fork 不應在自己的 UI 裡替原作者導流到個人社群/販售/贊助頁——使用者可能誤以為兩者有關聯，原作者也可能因此收到不屬於他的問題/客訴。**原則：署名文字保留（MIT 授權與基本禮貌要求），只移除可點擊的個人網址／導流連結**；上游 GitHub repo 連結（`jfamily4tw/voicetype4tw-mac`）屬必要的 fork 溯源資訊，不受影響。

- **`ui/settings_window.py`**：移除側欄底部整個 SNS 按鈕區塊（`sns_container`／`sns_layout`／`sns_links` 清單，原本連到 YouTube／Facebook／Instagram／TikTok／Threads／`Jimmy4.TW` 六個原作者個人帳號）。保留正上方的 `credit_box`（`主要開發者：吉米丘, CC58TW`／`協助開發者：Claude Code` 文字署名，原封不動）。連帶清掉因此變成未使用的 `import os`、`from pathlib import Path`（原本只為了組 SNS 圖示路徑）與 `SNSButton` import。
- **`ui/settings/common.py`**：`SNSButton` 類別（唯一使用處已被上面的改動移除）一併刪除，連帶清掉只被它使用的 `QIcon`／`QSize`／`QUrl`／`QDesktopServices` import。`docs/DECISIONS.md`（本檔）「原方法 → 新檔對應表」（god-file 拆分那筆歷史記錄）裡列出的 `SNSButton` 維持原樣不回溯修改——那張表記錄的是「當時拆分把它搬去哪」的歷史事實，`SNSButton` 後來被整個刪除是另一件事，記錄在這裡就好。
- **`ui/about_window.py`**：檢查後確認本來就沒有任何個人網址，只有文字署名（`Derived from VoiceType4TW.` / 吉米丘／CC58TW／go-mask／SanHsien 署名鏈），無需改動。
- **`voicetype_installer.iss:7`**：`MyAppURL` 從指向上游 repo（`https://github.com/jfamily4tw/voicetype4tw-mac`）改為指向本 fork（`https://github.com/SanHsien/voxprose`）——`AppSupportURL`／`AppUpdatesURL` 皆透過 `{#MyAppURL}` 巨集引用，自動跟著改。理由：這是本 fork 安裝程式的「發布者支援網址」欄位，理應指向實際維護本安裝檔的來源，而非上游專案（上游不負責、也無法回應這個 fork 的安裝問題）。`MyAppPublisher "jfamily"` 未改動——追加規格只要求處理「網址」，這是發布者名稱欄位非 URL，不在本次規格範圍內，留給維護者另外拍板。
- **`llm/openrouter.py:53`**：`HTTP-Referer` 從一個既非上游也非本 fork 的舊網址（`https://github.com/voicetype-mac`）改為本 fork repo；順手把同一段 headers 裡的 `X-Title: "VoiceType Mac"` 也改成 `"VoxProse"`——這不在追加規格的「網址」範圍內，但屬於送給 OpenRouter API 識別本應用程式身分的同一組 headers，留著舊品牌字面量在同一處明顯不一致，一併修正零風險（純字面量、不影響任何邏輯分支，已跑 `tests/` 確認無測試斷言這兩個舊字串）。
- **孤兒資產清理**：移除 SNS 按鈕後，`assets/sns-youtube.png`／`sns-facebook.png`／`sns-instagram.png`／`sns-tiktok.png`／`sns-threads.png`／`sns-4tw.png`（6 個 SNS 圖示）與 `assets/donate-linepay.jpg`（本來就沒有任何程式碼引用，推測是更早期就已成孤兒的贊助頁截圖）確認全 repo 零引用（含 `voicetype_installer.iss` 的 `[Files]` 區段與 `release_win.ps1` 的 robocopy 清單——兩者都是整個 `assets\*`／`assets` 目錄複製，非逐檔列舉，故刪除個別檔案不影響打包鏈）後，`git rm` 刪除。

### 簡體字全面清掃

不使用 grep 做 byte-wise／regex 多位元組比對（過去在本專案已知會產生大量假陽性）。改用 Python 腳本逐字元比對「簡體專用字→繁體」對照表，對照表刻意排除在正體中文裡也是合法獨立字的多音義候選字（后／裡⇔里／台／出／干／谷／舍／志／卷／表／只／沖／松／着／系／斗／肯／皮／耳／蒙／薄／藏……），避免誤殺「皇后」「公里」「台灣」這類合法正體用法——這些字元一律不放進對照表，若未來要收錄需先人工確認無歧義。掃描範圍：`git ls-files` 全部文字副檔名（排除 `assets/` 二進位資產）。

實際掃出 7 處（含維護者指出的 `REVIEW.md:14`「個人」一詞與 `VERSIONS.md:226`「問題」一詞誤植為簡體）：`REVIEW.md:14`（「個人」）、`VERSIONS.md:226`（「問題」）、`docs/DECISIONS.md:86`（「換」字，本檔既有文字）、`docs/DECISIONS.md:132`（「換」字）、`docs/DECISIONS.md:213`（「補」字）、`tests/test_stt_engine_dispatch.py:9`（docstring 內「靜」字）。全部確認是單純打字疏漏（非引用上游原文、非程式碼識別符），逐字修正為繁體對應字，不改動語意或重寫句子。修正後重跑掃描腳本，全 repo 零命中。

### 守門測試（新增 `tests/test_brand_and_charset_guard.py`）

新增三個 pytest 測試防止本次問題回流：(1) `test_no_simplified_characters_in_repo`——全 repo 逐字元比對上述簡體字對照表；(2) `test_no_legacy_brand_name_in_ui`——`ui/**` 原始碼不得含「嘴炮輸入法／嘴砲輸入法」；(3) `test_no_legacy_author_personal_urls_in_ui`——`ui/**` 原始碼不得含原作者個人網域字串（`jimmy4tw`／`Jimmy4.TW`／`portaly.cc`／`buymeacoffee`／`linepay`／`acykjcms` 等），但不鎖上游 GitHub repo 連結（`jfamily4tw/voicetype4tw-mac`，那是必要的溯源資訊）。測試檔本身的對照表字面量含大量簡體字，用於比對，會被掃描邏輯自我誤判，故在 `_is_text_candidate()` 明確排除測試檔自身路徑。

- **驗證**：`python -m pytest tests/ -v` 270 passed（266 基準 + 3 個新守門測試 + 1 個 `test_smoke.py` 自動為新測試檔案產生的 `test_py_compile` 參數化案例）、10 skipped，與任務起始基準一致（無既有測試被破壞）；全 repo `py_compile` 0 錯誤。

## 2026-07-21 — 品牌改名第二階段：資料路徑正名，不寫遷移邏輯

第一階段（見下方「品牌改名『聲成文 VoxProse』＋署名補正」條目）刻意保留 `%APPDATA%\VoiceType4TW` 與 `Documents\VoiceType4TW_Sync` 兩個實際路徑值不動，理由是「怕有真實使用者資料，貿然改名會造成設定與日誌分裂」。維護者本次任務開頭直接推翻這個保留理由：**維護者從未實際使用過本程式，本機不存在任何真實資料**，且明確指示「不用管 v3.1.0 的 release ZIP 有沒有人下載安裝過，不用保險避免他設定全丟」「寫死、舊安裝都不是理由」。

- **決定（不寫任何 old→new 遷移／備份／fallback 邏輯）**：第一階段規劃書 `docs/BRANDING.md` 原本的「第二階段遷移計畫」列了六條原則（新舊路徑並存、時間戳備份、先複製後刪、驗證後切換、保留 fallback、失敗時退回舊路徑）。這整套邏輯的前提是「舊路徑可能有真實資料需要保護」；前提不成立時，這些邏輯永遠不會被執行到（沒有舊資料觸發遷移分支），寫出來只是死碼、徒增 `paths.py` 複雜度與未來維護負擔。因此本次直接把 `paths.py:APP_DATA_DIR`（`VoiceType4TW`→`VoxProse`）與 `get_sync_base_dir()` 預設值（`VoiceType4TW_Sync`→`VoxProse_Sync`）改成新路徑字面量，不保留任何舊路徑分支。`docs/BRANDING.md` 已同步改寫「第二階段」章節反映此決定並作廢六原則計畫。
- **決定（`voicetype_installer.iss` 補做第一階段明確排除的兩項）**：第一階段「決定（`voicetype_installer.iss` 只改規格明列的兩個欄位）」條目明確排除 `MyAppName` 與 `AppId`。本次維護者明確授權擴大範圍：`MyAppName` 改為 `VoxProse`（連帶 `DefaultDirName`／Start Menu／桌面捷徑安裝後顯示名稱），`AppId` 換發新 GUID（`C3912B98-0808-4B52-84F5-F5BB7A040B9A`，`powershell [guid]::NewGuid()` 產生）。**換 `AppId` 的後果**：Inno Setup 用 `AppId` 判斷「是否為同一程式的升級安裝」，換新 GUID 後舊版（若有人裝過）不會被偵測為可升級對象，而是視為全新程式並列安裝。本專案目前沒有任何已知的既有安裝基礎（無人回報安裝過、無下載紀錄追蹤），此後果可接受，記錄於此供未來查證。
- **決定（打包鏈與工具全面跟進，範圍大於原規格明列項目）**：任務要求「全 repo 逐檔判斷」，實際 grep 後發現 `setup_win.bat`／`release_win.ps1`／`create_shortcut.ps1`／`build_win.py`／`tools/launcher.cs`／`tools/get_portable_python.ps1`／`.gitignore`／`tests/test_smoke.py` 都含 `VoiceType4TW` 的路徑或檔名語意引用（模型下載目的地、編譯輸出檔名、release staging 資料夾排除樣式等），部分是第一階段的「六項程式面改動」清單裡沒列到的散落點（如 `main.py`/`ui/app.py` 的啟動 log 橫幅、`self_check.py`/`tools/doctor.py`/`utils/diagnostics.py` 的診斷輸出、`ui/settings_window.py` 側欄 logo 死碼旁的重複宣告）。判斷依據：凡是「決定升級偵測、檔名比對、grep 樣式匹配」等會被程式或測試實際讀取比對的字面量，屬路徑/檔名語意，一律跟著改；凡是描述「上游是誰、fork 自哪裡、以前叫什麼名字」的敘述性文字，判定為歷史沿革語意，保留原名（`NOTICE.md`／`LICENSE`／`pyproject.toml` description／README 開頭 fork 出處／`ui/about_window.py` 的「Derived from VoiceType4TW」署名段落／`main.py:89-91` 與 `tests/test_config.py:7` 描述「這行程式碼過去長什麼樣子」的重構註解與 docstring／`CHANGELOG.md`／`VERSIONS.md`／本檔既有的歷史版本條目）。
- **決定（`ui/settings_window.py:229-235` 死碼一併清掉，而非只改文字）**：第一階段「意外發現並一併修正」條目當時明確記錄「此次不修這個既有小 bug，只更新其文字」——第一次宣告的 `QLabel` 從未加入 layout。本次任務清單明確授權「移除死碼那個，保留實際使用的」，故補做：刪除未使用的第一個 `lbl_en = QLabel("VoxProse")` 宣告，只留下實際 `addWidget` 的第二個。純刪除，不影響任何已接線的行為。
- **決定（`AGENTS.md`／`SKILL.md` 的過時「雙軌授權」措辭改寫）**：`NOTICE.md` 在稍早的 LICENSE 全面改版決策（見下方「LICENSE 全面改版為全 MIT」條目）中已正確更新為「上游已於 2026-07-20 補齊 MIT，本 fork 全 MIT，舊雙軌查證僅作背景記錄」，但 `AGENTS.md:14` 與 `SKILL.md:20` 兩處硬性邊界說明當時未同步，仍寫著「不宣稱上游有正式授權——見雙軌說明」，與現況矛盾、且會誤導後續 agent 以為現在仍是雙軌狀態。改為與 `NOTICE.md` 一致的現況描述。
- **驗證**：`python -m pytest tests/ -v` 266 passed / 10 skipped（與任務起始基準一致）；全 repo `py_compile` 0 錯誤；scratchpad 臨時腳本 `import paths` 印出 `APP_DATA_DIR`/`SYNC_BASE_DIR` 等確認為新路徑值，`paths.initialize_paths()` 在乾淨環境成功建立 `%APPDATA%\VoxProse` 與 `Documents\VoxProse_Sync\soul` 完整目錄樹後，已刪除測試建立的目錄與檔案，環境維持乾淨。
- **意外發現（非本次任務範圍，記錄供維護者參考）**：驗證前 grep 發現 `%APPDATA%\VoiceType4TW\{memory,stats,vocab}` 仍存在，含一份預設種子 `custom_vocab.json`（內容為程式內建的常用詞範例，非個人真實資料），時間戳為本次任務執行當天，研判是先前品牌改名任務驗證過程留下的測試殘留，並非「維護者確認不存在」的真實使用資料被打臉——只是同一天稍早的另一個 agent session 曾實際 import/執行過 `paths`/`vocab.manager` 留下的痕跡。與本次「不寫遷移邏輯」的決策不衝突（這不是需要遷移的使用者資料，是舊路徑下的測試殘留），故未刪除、未處理，留給維護者自行決定是否清理。

## 2026-07-21 — GitHub repo 更名為 `SanHsien/voxprose`

維護者在本次品牌改名任務進行中途通知：GitHub repo 已由 `SanHsien/voicetype` 更名為 `SanHsien/voxprose`（GitHub 對舊名會自動 302 轉址，但文件不應繼續寫舊名）。本機 remote URL 已由維護者在另一個 session 更新為 `https://github.com/SanHsien/voxprose.git`，本次任務不需要、也沒有動 git remote 設定。

- **事實記錄**：repo 更名日期 2026-07-21。全 repo `.md` 檔內對 `SanHsien/voicetype` 的引用（compare 連結、clone 指令、下載連結，約 11 處）已改為 `SanHsien/voxprose`；`LICENSE` 內的 fork 自我引用（`` `SanHsien/voicetype` ``，中英各一處）同步更新。已 grep 全 repo（`.py`／`.ps1`／`.bat`／`.iss`／`.yml`）確認沒有其他非 `.md` 檔引用 `SanHsien/voicetype` 這個 GitHub 路徑字串。
- **決定（`pyproject.toml` 的 `name` 一併改為 `voxprose`）**：原值 `name = "voicetype"` 純粹是 packaging metadata（`dependencies = []`，不驅動實際安裝，見既有註解），grep 全 repo 確認沒有任何程式碼或測試讀取這個欄位值（`tools/check_dependency_freshness.py` 用的是 `importlib.metadata.version(package_name)`，`package_name` 來自 requirements 檔解析而非 `pyproject.toml` 自身的 `name`），故隨品牌改名一併更新，零風險。`version` 同時推進至 `3.2.0`（見版本推進批次）。
- **維持不動（本機目錄名稱）**：本機工作目錄仍是 `C:\Users\SanHsien\OneDrive\文件\GitHub\voicetype`，維護者尚未指示更名本機資料夾，本次任務未變更。**提醒**：未來若本機資料夾更名為 `voxprose`，需同步檢查 IDE/編輯器的 workspace 設定、任何寫死本機路徑字串的個人腳本（如捷徑、`.bat` 啟動器）、以及 Claude Code / 其他 AI agent 工具的專案索引設定，避免路徑對不上。

## 2026-07-21 — 品牌改名「聲成文 VoxProse」＋署名補正（go-mask）

維護者拍板完整品牌規格：中文品牌「聲成文」、英文品牌「VoxProse」、組合呈現「聲成文 VoxProse」、標語「自然開口，清楚成文。」／"Speak naturally. Write clearly."。同時指出過去一直遺漏的署名缺口：上游 Windows 專用版維護者 **go-mask**（`win-go-mask-202607` 分支，該分支 README 明載「Windows 專用版維護：go-mask ｜ 協助開發：Claude Code」）過去在本 repo 只被當成分支名稱使用，從未在 `NOTICE.md`／`README.md`／About 視窗等處以「維護者」身分列名。

- **決定（視窗標題／系統匣改動的實際落點與規格描述不完全一致，依實際程式碼結構落地）**：規格寫「系統匣：聲成文（`ui/tray_manager.py` 相關顯示字串／tooltip）」，但實際查證 `ui/tray_manager.py:TrayManager.__init__` 只接收呼叫端傳入的 `title` 參數並直接 `setToolTip(self.title)`，檔案本身不含任何品牌字面量；真正的字串來源是 `ui/app.py:112`（`TrayManager(title="VoiceType4TW", ...)`）。已在正確落點修改（`ui/app.py:112` → `title="聲成文"`），效果與規格描述一致，僅記錄檔案路徑差異供未來查證。
- **意外發現並一併修正（`ui/settings_window.py` 側欄 logo）**：規格六項只列「視窗標題」（`setWindowTitle`），但檢視 `ui/settings_window.py:229,233` 發現設定視窗側欄有兩個 `QLabel("VoiceType4TW")`（同一段程式碼重複宣告兩次，第一個從未加入任何 layout、是既有的死碼，此次不修這個既有小 bug，只更新其文字），是視窗內另一處可見的品牌字樣，若不改會讓「視窗標題已改、側欄 logo 卻還是舊名」的半調子改名出現在同一個視窗裡。已一併改為 `QLabel("VoxProse")`（英文單字，比照側欄原本的英文單字風格，與正下方 `Windows Version` 字型/語言一致）。
- **決定（About 視窗放大尺寸）**：新增標語與完整署名鏈文字後，原 `300×350` 固定尺寸有裁切風險，調整為 `320×430`（`ui/about_window.py`），僅尺寸調整，佈局邏輯不變。
- **決定（release_win.ps1 ZIP 命名的版本號來源改用 `pyproject.toml`，不用 `paths.py` 的 `BUILD_ID`）**：舊命名 `VoiceType4TW_Win_Portable_*_V<digits>` 的版本號取自 `paths.py` 的 `BUILD_ID`（如 `BUILD-3200-STABLE` 取 `3200`），格式是純數字、不含小數點，與規格範例 `ShengChengWen-Windows-Lite-v3.2.zip` 的 `v3.2`（主.次版號，含小數點）不吻合。改為從 `pyproject.toml` 的 `version = "X.Y.Z"` 動態解析出 `X.Y`（如 `3.2.0` → `3.2`），透過 PowerShell regex `'version = "(\d+)\.(\d+)\.\d+"'` 取前兩段，符合規格「版本號跟著版本走，不要寫死」的要求，同時格式與範例完全一致。`BUILD_ID` 仍保留在 console 輸出中供內部識別（`聲成文 VoxProse Portable Packager v3.2 (BUILD-3200)`），未刪除。
- **決定（`.github/workflows/release.yml` 核實後判定無需改動）**：規格要求「同步更新 `.github/workflows/release.yml` 內引用 ZIP 檔名的步驟」，但實際讀取該檔案發現所有步驟（SHA256 產生、artifact 上傳、Release 附檔）都用 `dist/*.zip` 萬用字元操作，沒有任何步驟寫死具體 ZIP 檔名字面量——`release_win.ps1` 改名後這個 workflow 不需要任何改動即可正確運作。記錄於此以示已查證而非遺漏。
- **決定（`voicetype_installer.iss` 只改規格明列的兩個欄位）**：規格在「版本推進 3.2.0」項下明確只點名 `MyAppVersion` 與 `OutputBaseFilename` 兩個欄位；`MyAppName`（`"VoiceType4TW"`，同時決定 Start Menu／桌面捷徑的安裝後顯示名稱與 `DefaultDirName`）與 `AppId`（GUID，決定升級偵測）不在此次授權範圍內，維持原樣不動。這代表 Inno Setup 安裝版目前會出現「安裝檔案名叫 `ShengChengWen-Windows-Setup-v3.2.exe`，但安裝後 Start Menu／桌面捷徑仍顯示 `VoiceType4TW`」的不一致狀態——這是刻意的範圍邊界（照規格逐字執行），不是遺漏，若要讓安裝版品牌完全一致，需要維護者另外拍板是否要改 `MyAppName`（連帶影響既有使用者的安裝目錄/解除安裝機制，風險層級更高，故本次不擅自擴大範圍）。
- **決定（`main.py` 硬編 APPDATA 路徑改用 `paths.APP_DATA_DIR`，純重構）**：`main.py` 原本有一行獨立寫死的 `os.path.join(os.environ.get('APPDATA', ''), 'VoiceType4TW')` 只為了算 crash log 目錄，與 `paths.py` 的 `APP_DATA_DIR` 各自定義同一個值、從未共用。該行程式碼位置緊接在 `from paths import initialize_paths, APP_DATA_DIR, VERSION_NAME, BUILD_ID` 之後，`APP_DATA_DIR` 已在作用域內，故直接改用 `str(APP_DATA_DIR)`。**驗證行為不變**：`APP_DATA_DIR = Path(os.environ.get("APPDATA", str(HOME / "AppData" / "Roaming"))) / "VoiceType4TW"`（`paths.py`）與原本 `main.py` 寫死的 `os.path.join(os.environ.get('APPDATA', ''), 'VoiceType4TW')` 在 `APPDATA` 環境變數存在時算出完全相同的路徑字串；差異只在 `APPDATA` 不存在的極端情況（`paths.py` 有 fallback 到 `~/AppData/Roaming`，舊的 `main.py` 寫死版本 fallback 到空字串導致 `os.makedirs('')` 拋錯）——這代表本次重構同時**修正**了一個原本存在但幾乎不會觸發的邊界 bug（Windows 環境下 `APPDATA` 環境變數幾乎不可能缺失），純屬重構的良性副作用，非刻意修 bug。
- **決定（不改 `%APPDATA%\VoiceType4TW` 與 `Documents\VoiceType4TW_Sync` 實際路徑值）**：維護者明確指示第一階段不動這兩個實際路徑。已用 `grep -n "APP_DATA_DIR\s*=" paths.py` 與 `grep -n "VoiceType4TW_Sync"` 核對：`paths.py:APP_DATA_DIR` 的值仍是 `.../AppData/Roaming/VoiceType4TW`、預設同步目錄仍是 `Documents/VoiceType4TW_Sync`，兩者字面量本次未被任何 Edit 觸碰。第二階段遷移計畫見 `docs/BRANDING.md`。
- **決定（全 repo `.md` 逐檔檢視後的處置）**：`git ls-files "*.md"` 列出的每個檔案都已個別檢視，處置摘要見 `VERSIONS.md` [V3.2.0] 條目與本次任務回報；`soul/**/*.md`（8 個範本檔）用 `grep -riE "VoiceType4TW|嘴炮輸入法|吉米丘|CC58TW"` 確認零匹配，判定不需改（這些是 AI 靈魂/情境範本內容，與品牌名稱無關）。`docs/UPSTREAM.md`／`docs/mac-mainline-absorption-analysis.md`／`CLAUDE.md`（本 repo 專屬薄補丁）同樣 grep 確認不含產品自稱字樣，不需改。`REVIEW.md` 僅改標題（署名/名稱），問題總帳的技術結論與修復狀態欄一字未動。

## 2026-07-21 — 上游更新自動檢查：`last_merged`／`last_reviewed` 雙欄設計

維護者交辦：除了既有的依賴新鮮度月檢，也要定期檢查來源上游 `jfamily4tw/voicetype4tw-mac` 是否有新 commit，比照 `tools/check_dependency_freshness.py` + `.github/workflows/dependency-freshness.yml` 的範本改寫。

- **決定（雙欄設計，而非單一「已檢查到哪」指標）**：`docs/UPSTREAM.md` 新增機器可讀的「同步狀態標記區塊」，每個追蹤分支（`win-go-mask-202607`／`win-stable`／`main`）記兩個獨立欄位：`last_merged`（已合併進本 fork 的最後一個上游 commit，等同 `git merge-base HEAD upstream/<branch>` 可驗證的那個 commit）與 `last_reviewed`（已審視過的最後一個上游 commit，含審視後決定不採用者）。理由：上游 Mac 線常有不適用本 fork 的 commit（如 macOS 專屬修復），若每次自動檢查都用「有沒有合併」當判準，這些 commit 會被永遠重複回報成雜訊；若用「有沒有審視過」當判準又會漏記「這個 commit 到底有沒有真的併進來」的事實。兩個欄位獨立記錄，`tools/check_upstream_updates.py` 只依 `last_reviewed` 判斷要不要回報，`last_merged` 純粹留給人類讀「目前程式碼實際同步到哪」。
- **決定（Skipped 表防決策失憶）**：`last_reviewed` 推進後，該 commit 就不會再出現在檢查報告裡——但這代表「當初審視為不適用、但日後情勢改變可能變得該採用」的 commit 會從此消失在視野外。因此在標記區塊之後新增人類可讀（不需機器解析）的「Skipped（審視後未採用）」表，記錄分支／commit／標題／審視日期／未採用理由。規則明訂：**每次審視後決定「不採用」，除了推進 `last_reviewed`，必須同時在 Skipped 表補一列**——`last_reviewed` 負責「不再重複騷擾」，Skipped 表負責「不失憶」，兩者職責不同，缺一不可。已知的兩筆（`0ed0c47` 應用程式退出清理、`10b2fc8` 熱鍵 watchdog 復原）都是 macOS 專屬（AppKit／CGEventTap），本 fork 為 Win32 `GetAsyncKeyState` 輪詢架構，先行記錄；日後若熱鍵或退出流程做架構級重構，應先回掃此表。
- **決定（術語：捨棄「水位」比喻，改用 `last_merged`／`last_reviewed`）**：最初草稿用「水位線」比喻兩個同步指標，維護者反映這個自創術語沒有業界共識、跨行不容易看懂，要求改用工程界通用語彙——`last_merged` 直接對應 `git merge-base` 這個所有工程師都認得的概念，`last_reviewed` 是純白話「上次看到哪」，不需要額外查術語表。原本的「已評估未引進」附錄標題也一併改名為「Skipped（審視後未採用）」，呼應 fork 維護圈常見的 cherry-pick 取捨語感與 GitHub `wontfix` 標籤的通用語感。全部程式識別碼（JSON 鍵名、Python 變數/函式名）、報告文案、`AGENTS.md` 流程說明同步改名，新增守門測試 `test_no_watermark_jargon_in_source_module`（`tests/test_upstream_check.py`）防止舊詞回流。
- **決定（compare API 而非 `git log` 手動比對）**：`tools/check_upstream_updates.py` 用 GitHub REST compare API（`/repos/{repo}/compare/{last_reviewed}...{branch}`）取得新 commit，而非在 CI runner 上 `git fetch upstream` 做全歷史 clone——避免在 `ubuntu-latest` runner 上把整個上游 repo（含大型 assets）都抓下來，且 compare API 天生回傳的就是「head 可達、base 不可達」的 commit 清單，語意與需求完全對應。支援 `GITHUB_TOKEN` 環境變數提高 rate limit，匿名也能跑（額度較低但這個查詢頻率低，週期性檢查足夠）。
- **決定（解析失敗必須非 0 退出，不可靜默視為無更新）**：`parse_sync_points()` 找不到標記區塊、JSON 語法錯誤、缺少必要分支或欄位，一律拋出 `UpstreamParseError` 並讓 `main()` 回傳非 0——若靜默吞掉當成「沒有更新」，會讓維護者誤以為上游真的沒有新東西，而實際上是文件被改壞了根本沒查到，這是比「沒有更新」更危險的靜默失敗模式。同理，任一分支的 API 查詢失敗（網路、rate limit）也會讓整體 exit code 非 0，即使其他分支查詢成功——不讓部分失敗被平均成一個看似正常的整體結果。
- **意外發現**：本機實跑後，`main`（Mac 線）分支比對出 2 筆「新」commit——`0ed0c47`（已記在 Skipped 表）與 `46346d3`（LICENSE 取用來源，`license_source` 已記錄）。這代表 GitHub 上這兩個 commit 在 `main` 分支的 compare 拓樸關係裡並非 `10b2fc8`（目前 `last_reviewed`）的祖先，而是在其之後（或位於其他不含 `10b2fc8` 的路徑上）——`last_reviewed=10b2fc8` 這個既有值本身在拓樸序上可能不是 `main` 分支目前最新的已審視 commit。本次任務範圍是照維護者指定的既有值建立機制，不擅自變更 `docs/UPSTREAM.md` 既有記錄的 `last_reviewed` 值；建議維護者下次審視 `main` 分支時一併確認 `last_reviewed` 是否該推進到 `46346d3`（目前 tip），並視情況調整。

## 2026-07-21 — `ui/settings_window.py` god file 拆分（REVIEW.md #7）

維護者交辦：前一個 agent 已建立 `ui/settings/` 子套件的部分頁面（`common.py`／
`dashboard_page.py`／`engine_page.py`）但未接線進主檔就因額度中斷；本次先驗證
半成品可信度，再完成剩餘頁面拆分並接線。

- **驗證半成品**：用 `ast` 逐一抽取 `common.py`／`dashboard_page.py`／
  `engine_page.py` 裡的每個函式/方法，與 `ui/settings_window.py` 原始碼裡對應
  區塊做 `difflib` 逐行比對——三個檔案全部通過，僅有的差異是空白行的尾端空格
  被清掉（純格式，非邏輯）。判定：**半成品可信、忠實、完整**，可以直接沿用，
  不需重做。
- **決定（用多重繼承 mixin 而非組合/委派）**：`SettingsWindow` 目前的所有
  `_create_*_page` 方法內部大量互相依賴同一個 `self`（例如 `_create_stt_llm_page`
  呼叫 `self._add_grid_row`、`self._populate_whisper_models`；`_load_data`/
  `_save_action` 直接讀寫十幾個分頁建立的 widget 屬性）。若改成「每頁一個獨立
  物件、組合進 SettingsWindow」，等於要把這些方法簽章全部改寫成跨物件呼叫，
  屬於「順手優化」而非「機械搬移」，且範圍會大幅超出本次任務（純拆分，不改
  行為）。多重繼承 mixin 讓每個分頁類別只多出 `XxxPageMixin` 這一層，方法定義
  搬到別的檔案，但 `self.xxx` 呼叫方式完全不變——這是唯一能同時滿足「純機械
  搬移」與「god file 拆分」兩個要求的做法。
- **決定（`STT_ENGINES` 常數搬到 `common.py`，同步改測試解析目標而非留在殼裡
  重複宣告）**：`tests/test_stt_engine_dispatch.py` 原本用正則從
  `ui/settings_window.py` 的原始碼文字裡抓 `STT_ENGINES = [...]` 這行字面量
  （刻意不 import 該模組，因為它頂層 import PyQt6）。常數的唯一正確歸屬是
  `ui/settings/common.py`（其他分頁 mixin 從那裡 import），若為了不動測試而在
  殼檔裡重複宣告一份字面量，會製造「兩份 STT_ENGINES 定義，改一個忘改另一個」
  的新技術債。改為讓測試的解析目標跟著常數搬——`SETTINGS_COMMON_SRC` 讀
  `ui/settings/common.py`，正則與 `ast.literal_eval` 解析邏輯不變，防護力（UI
  引擎清單 ↔ `stt.get_stt()` 分派一致性）沒有被弱化。
- **意外發現並修正（`_run_self_check` 的 `__file__` 路徑計算）**：原本
  `os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "self_check.py")`
  依賴 `__file__` 是 `ui/settings_window.py`（往上兩層 `dirname` = repo root）。
  搬到 `ui/settings/general_page.py` 後，同樣的兩層 `dirname` 會變成 repo root
  的 `ui/`，導致 `self_check.py` 路徑算錯（永遠找不到檔案，按鈕會跳「找不到
  檢測程式」錯誤視窗）。這是純機械搬移必然會踩到的陷阱——檔案換位置但邏輯
  沒跟著調整就會壞掉，因此補了一次 `os.path.dirname()`（改三層），行為與拆分
  前完全一致（本機驗證：`self_check.py` 確實在 repo root）。用 `ast` 逐一比對
  原始檔與新檔的每個函式/方法/模組常數（共 63 個項目）後，這是**唯一**一處
  必要的非空白差異，其餘全部逐字相同。
- **對外契約**：`from ui.settings_window import SettingsWindow` 不變；
  `git diff ui/app.py` 為空（`ui/app.py` 只 `from ui.settings_window import
  SettingsWindow`，未引用任何被搬移的內部符號）。
- **原方法 → 新檔對應表**：

  | 原本在 `ui/settings_window.py` | 現在在 |
  |---|---|
  | `GlassCard`／`SidebarButton`／`SNSButton`／`HotkeyRecorderButton`／`PermissionLight`／`ModelStatusLight`／`translate_key_string`／`CODE_TO_MAC_NAME`／`CODE_TO_WIN_NAME`／`STT_ENGINES`／`LLM_ENGINES`／`WHISPER_MODELS`／`TRIGGER_MODES`／`HOTKEYS`／`LLM_MODES` | `ui/settings/common.py`（模組層級元件/常數）+ `CommonPageMixin`（`_page_section_header`／`_add_grid_row`） |
  | `_create_dashboard_page`／`_update_dashboard_status`／`update_download_progress`／`_check_all_permissions`／`_check_local_models`／`_is_model_present` | `ui/settings/dashboard_page.py`（`DashboardPageMixin`） |
  | `_create_stt_llm_page`／`_populate_whisper_models`／`_check_mic_devices_changed`／`_populate_mic_devices` | `ui/settings/engine_page.py`（`EnginePageMixin`） |
  | `_create_soul_page`／`_create_file_list_tab` | `ui/settings/soul_page.py`（`SoulPageMixin`） |
  | `_create_vocab_mem_page`／`_refresh_vocab`／`_refresh_learned_vocab`／`_promote_vocab`／`_delete_learned_word`／`_refresh_memory`／`_delete_memory_entry`／`_purge_memory`／`_add_vocab`／`_del_vocab` | `ui/settings/vocab_mem_page.py`（`VocabMemPageMixin`） |
  | `_create_sync_page`／`_set_sync_directory`／`_migrate_to_sync`／`_clear_sync_directory` | `ui/settings/sync_page.py`（`SyncPageMixin`） |
  | `_create_stats_page`／`_refresh_stats` | `ui/settings/stats_page.py`（`StatsPageMixin`） |
  | `_create_general_page`／`_run_self_check`（含 `__file__` 路徑修正）／`_run_export_diagnostics`／`_view_debug_log`／`_view_keystrike_log`／`_open_data_folder`／`_run_mic_test` | `ui/settings/general_page.py`（`GeneralPageMixin`） |
  | `__init__`／`_setup_ui`／`_on_sidebar_changed`／`_load_data`／`refresh_config`／`_save_action`／`run`／`has_api_key`／`if __name__ == "__main__":` | 留在 `ui/settings_window.py`（薄殼，`SettingsWindow` 組裝所有 mixin） |

- **測試**：`python -m pytest tests/ -v`：**246 passed, 10 skipped**（拆分前
  241 passed；+5 為新增 5 個分頁檔被 `tests/test_smoke.py` 全 repo
  `py_compile` 掃描一併計入，非新增測試案例）。全 repo `py_compile` 通過。
  PyQt6 實機建構煙霧測試：在 scratchpad 建乾淨 venv（Python 3.11.15，僅
  `pip install PyQt6`，不裝 CUDA/faster-whisper/sounddevice），把 repo 加進
  `sys.path` 後直接 import 真正的 `ui.settings_window.SettingsWindow`，用
  `load_config()` 的真實預設設定建構視窗、逐一切換全部 7 個分頁（用
  `win.stack.currentIndex() == i` 斷言，非僅呼叫不驗證）、存取各頁關鍵 widget
  （`stt_engine`／`whisper_model`／`soul_prompt`／`vocab_list`／`mem_tree`／
  `sync_status_lbl`／`stats_tree`／`btn_ptt`／`btn_mic_test`／
  `_mic_poll_timer`），最後正常 `close()`。**exit code 0**，`ctranslate2`／
  `sounddevice` 缺失時的既有例外處理分支也正確觸發（非崩潰），符合設計預期。
  腳本存於本機 scratchpad（session 隔離目錄，非 repo 一部分）。
- **commit**：`1252a68`（`ui/settings/` 子套件 + 薄殼 `ui/settings_window.py` +
  `tests/test_stt_engine_dispatch.py` 解析目標更新，單一 atomic commit）。

## 2026-07-20 — v3.1.0 發版工程收尾（UPSTREAM 追蹤、-NoModel 打包、release/dependency-freshness workflow、版本推進）

維護者指示：v3.1.0 發版前最後一批工程項，完成後主 session 會把 fork 全部 commit squash 成單一 v3.1.0。

- **決定（`docs/UPSTREAM.md` 記錄雙上游祖先鏈而非只記單一 upstream）**：本 fork 實際上同時追蹤 Windows 線（`win-stable`／`win-go-mask-202607`）與 Mac 主線（`main`，僅分析吸收、不併程式碼）兩條祖先鏈。Squash 成單一 v3.1.0 commit 後，若只記錄一條上游關係，日後任一邊有新變更時 `git merge`/`git log A..upstream/B` 會找不到正確的共同祖先。因此本檔明訂 squash commit 應保留雙親（`51094bf` Mac 分岔點＋`e5ddc02` Windows 線最新併入點），並記錄「檢查上游更新」標準流程與慣例——每次同步後回來更新同步點，避免文件與實際狀態漂移。
- **決定（installer 版本字串不採用上游 `win-go-mask-202607` 的值）**：查證 `git show e5ddc02:voicetype_installer.iss` 發現上游該分支的 `MyAppVersion` 是 `"2.8.27_V90"`——早於本 fork 當時的 3.0.1，判斷為上游誤植降版（可能是分支基底較舊、未同步更新這個欄位），故合併 `win-go-mask-202607` 時未採用這個值，本 fork 版本號自行管理，已記錄進 `docs/UPSTREAM.md` 的同步狀態表供未來查核。
- **決定（`release_win.ps1` 新增 `-NoModel` 而非只有 Lite/Full 兩選項）**：維護者核准動打包鏈，需求是「有 CUDA 加速但不want 綁 medium 模型」的中間選項（滿足吃 GPU 但介意 ZIP 體積、或想首次啟動自行選模型大小的使用者）。實作上只改動最小必要範圍：CUDA 安裝條件維持 `-not $Lite` 不變（`-NoModel` 單獨開啟時仍會裝 CUDA），模型隨附條件改為 `-not $Lite -and -not $NoModel`；資料夾/ZIP 命名獨立一支 `VoiceType4TW_Win_Portable_NoModel_V$Build`，避免和既有 Lite/Full 命名撞在一起。三種組合（預設/`-Lite`/`-NoModel`）皆做過乾跑邏輯驗證（模擬變數，不真的跑完整建置）。
- **決定（release workflow 只打包 Lite + NoModel，不含 Full）**：`.github/workflows/release.yml` 比照 `yt_fetch` 的 release.yml 模式（push tag `v*` 發佈、`workflow_dispatch` 手動僅 artifact）。Full 版含 medium 模型需要本機事先下載模型快取到 `%APPDATA%`，CI runner 上沒有這個快取、且模型本身體積會讓 ZIP 逼近或超過 GitHub Releases 單檔 2GB 上限，不適合在 CI 環境建置；Lite（無 CUDA 無模型）與 NoModel（有 CUDA 無模型）兩版已涵蓋「先讓使用者跑起來、首次啟動再選擇下載內容」的主要發版情境。
- **決定（`tools/check_dependency_freshness.py` 改用「requirements 檔宣告的最低版本」而非強制安裝全部依賴比對）**：移植自 `yt_fetch` 同名工具時發現差異——`yt_fetch` 只追蹤 2 個套件且都跨平台，可以 `pip install -e .` 後用 `importlib.metadata` 查已安裝版本；本 repo 的 `requirements-win.txt` 含 `pywin32`（Windows-only wheel），若比照在 `ubuntu-latest` 上執行 `pip install -r requirements-win.txt` 會直接安裝失敗。改為優先用目前環境已安裝版本（如果剛好有裝），未安裝則退回解析 requirements 檔案 `>=` 宣告的最低版本作為比較基準——這樣不需要完整安裝依賴就能判斷「版本下限是否落後 PyPI 最新版」，`dependency-freshness.yml` workflow 因此可以留在較便宜的 `ubuntu-latest`，不必換成 `windows-latest`。
- **測試**：`python -m pytest tests/ -v`：233 passed, 10 skipped（較上一批的 232 passed 多 1，`tests/test_smoke.py` 的全 repo py_compile 掃描新增計入 `tools/check_dependency_freshness.py`）。`release_win.ps1` 用 `[System.Management.Automation.Language.Parser]::ParseFile` 語法解析通過；三種旗標組合（預設/`-Lite`/`-NoModel`）的資料夾命名／CUDA 安裝／模型隨附條件邏輯乾跑驗證正確。`.github/workflows/release.yml`、`.github/workflows/dependency-freshness.yml` 用 `yaml.safe_load` 驗證語法有效。`tools/check_dependency_freshness.py` 本機實跑成功（含真實 PyPI JSON API 查詢，17 個套件的版本比對報告輸出至 scratchpad，未落 repo）。

## 2026-07-20 — 上游同步（win-go-mask-202607 三步驟安裝＋MIT 補授權）與雙軌授權收斂為全 MIT

維護者指示：v3.1.0 發版前最後一批內容變更，合併上游 `win-go-mask-202607` 分支新增的 3 個 commit，並隨上游 `main` 分支補齊 MIT 授權（commit `46346d3`）同步收斂本 fork 的授權聲明。

- **決定（合併用 merge commit，保留歷史）**：`git merge --no-ff upstream/win-go-mask-202607`。實際只有 `README.md` 產生衝突（7 張截圖與 `VERSIONS.md` 因本 fork 未曾改動這些檔案，直接乾淨採上游版；`paths.py`／`voicetype_installer.iss` 因本 fork 已各自獨立演進，merge 未產生變更，維持本 fork 版本，與原定「衝突時採我們版」的預期一致，只是實際上未進入衝突狀態）。
- **決定（README.md 衝突解法）**：保留本 fork 版本為骨架（Windows 開發版定位、LICENSE 段、fork 文件索引、「以原專案最新說明為準」導引語），把上游「🚀 快速安裝（三步驟）」整合進頂部，**下載連結改指向本 fork**（`SanHsien/voicetype` 而非上游 zip），因本 fork 定位為 Windows 版本的實際維護來源；另外吸收上游新增的「辨識與 AI 設定」畫面導覽段（對應既有的 `assets/screenshot-pc-02.jpg`，本 fork 先前遺漏未收錄）與「🛠️ 安裝失敗排除」章節。刻意不引入上游 README 的下載販售連結／YouTube 影片／贊助段落，這些內容與本 fork 的開發版定位不符。
- **決定（LICENSE 全面改版為全 MIT）**：上游已正式補齊 MIT 授權，先前因「上游無正式授權」而採的雙軌授權聲明（上游程式碼不宣稱授權＋本 fork 新增部分單獨 MIT）失去存在理由。改寫 `LICENSE` 為單一 MIT 授權文件：上游 MIT 全文（含 `Copyright (c) 2026 Jimmy Chiou, CC58TW, and VoiceType4TW contributors` 版權行）之後，附加一段「本 fork 新增部分 © 2026 SanHsien，同採 MIT 條款」的聲明。`NOTICE.md` 的「授權狀態」節同步改寫：先講清楚現況（上游已於 2026-07-20 採 MIT），原本的查證過程（GitHub License API 404、口語聲明非正式授權文字等）保留為背景記錄而非刪除，避免抹去先前查證的工作紀錄。`README.md`／`README.en.md` 的授權敘述行同步更新為指向全 MIT。
- **測試**：合併後與 LICENSE/NOTICE 改寫後皆執行 `python -m pytest tests/ -v`，232 passed, 10 skipped，與改動前一致（本批不涉及任何 `.py` 邏輯變更）。

## 2026-07-20 — Mac 主線吸收收尾批次（13-1／7-5／7-6／11-3）＋剩餘 bug/死碼清理

維護者指示「剩餘 bug＋剩餘 Mac 版可吸收項全部做完」，依 `docs/mac-mainline-absorption-analysis.md` 逐項處理。

- **決定（推翻先前「13-1 刻意不搬」的批次範圍限制，非推翻其技術判斷）**：本檔案 2026-07-20「Mac 主線功能吸收第 2-5 項」條目原本寫「刻意不搬 13-1，本次任務範圍明訂只做建議吸收順序第 2-5 項」——那是當時任務範圍的批次界線，不是「13-1 不值得做」的技術結論。本次維護者明確要求全部做完，13-1（`llm/prompts.py`）已吸收（`19017c8`）。`refine()` 簽章維持 `(text, prompt)` 不變，只加 `prompt or get_default_system_prompt(self.language)` 防禦性 fallback，不改介面契約，與先前決策的「不改介面」精神一致。
- **決定（7-5 輕量版靈魂規則的接線位置）**：現樹 `ui/app.py:_process_audio` 只有在 `is_llm_used` 為 True 時才做任何文字後處理；LLM 關閉時 `output_content = text`（原始 STT 文字）直接進 `self.injector.inject()`，完全沒有贅詞清理路徑。比照 Mac 版 `main.py` 在 `if not is_llm_used: final_text = self._apply_basic_soul_rules(final_text)` 的位置（標點轉換之前、注入之前），在現樹對應位置插入同等邏輯，只是現樹要同時處理 `output_content`（實際注入內容）與 `final_text`（用於 stats/memory 記錄）兩個變數，故兩者都套用清理結果。純字串解析/刪除邏輯抽到 `utils/soul_rules.py`（不放 `ui/app.py` 內），理由與 `audio/gain.py`、`stt/hallucination_filter.py` 一致：`ui/app.py` 頂層 import PyQt6，純邏輯抽出才能在無 PyQt6 環境單元測試。
- **決定（11-3 診斷包 Windows 化改寫的取捨）**：Mac 版用 `sysctl`/`system_profiler` 取 CPU brand/RAM/GPU，Windows 對應改用 `platform.win32_ver()` + ctypes `GlobalMemoryStatusEx`（不額外依賴 `psutil`，`requirements-win.txt` 目前沒有這個套件，用內建 `ctypes` 呼叫 Win32 API 零成本）；不含 GPU 型號查詢（現樹無對應痛點，CUDA 由 `requirements-cuda-win.txt` 另外處理）。Mac 版的 macOS crash reports 目錄改收現樹既有的 `main_crash.log`（`main.py` 的 `faulthandler.enable()` 輸出，原本就存在但從未被打包匯出過）。新增 `collect_device_info()` 沿用 `diagnose_mic.py` 已驗證過的 `sd.query_devices()` 邏輯，sounddevice 未安裝時給明確訊息而非讓整包匯出失敗。
- **決定（順手修復假 stub，非任務外加碼）**：`ui/settings_window.py:_run_mic_test` 內發現一段「非 macOS 一律拒絕」的擋板，但擋板之後的實際測試程式碼（`sd.rec()` + numpy RMS）本來就不含任何 macOS API、連錯誤訊息文案都已經是寫給「Windows 隱私權設定」看的——這代表擋板本身是誤植/遺留死碼，不是刻意設計。這正是任務指定的 2a 項目（settings_window.py 附近的診斷按鈕 stub），移除擋板 + 取消 Windows 隱藏是修 bug而非新功能。**`🔍 系統自我檢測`按鈕維持原本的 Windows 隱藏**——雖然 `self_check.py` 本身邏輯也跨平台，但它不在任務指定範圍內（任務只點名麥克風測試/系統診斷 stub），且該按鈕會下載真實 whisper 模型執行完整轉錄測試、耗時較長，是否該在 Windows 開放是需要另外評估的產品決策，此次不擅自變更，僅在回報中提出留維護者決定。
- **決定（2b/2c 死碼清理，收尾 2026-07-19 當時暫留的尾巴）**：`paths.py:AI_PERMANENT_MEMORY_PATH` 與先前已清掉的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 同一批死碼（皆指向 `SYNC_BASE_DIR`、皆零引用），當時因不在指定範圍暫留，本次一併移除（`53a4ef3`）。`vocab/manager.py` 的本機常數 `VOCAB_DIR`（`get_data_dir("vocab")`）與已移除的雲端同步死碼常數同名，REVIEW 曾點出此撞名風險，改名 `_VOCAB_DATA_DIR` 並加註解釐清（`27d93c8`），純改名不改行為。
- **維持不動（依報告「建議不吸收清單」與既有決策，非本次遺漏）**：
  - **8-1 MiniMax 引擎、13-4 default `llm_engine` 改 openrouter**：報告本身列為「產品決策，依維護者實際使用習慣而定」，技術上可攜但預設值/新引擎需維護者拍板，非技術問題，不擅自變更。
  - **10-1 target_pid 精準注入**：報告建議「等使用者實際回報貼錯視窗再立項」——概念值得但需全新 Win32 實作且有 `SetForegroundWindow` 限制地雷，非現在就該做的項目。
  - **7-7 設定頁版面 QGridLayout 對齊**：報告本身建議「只在做 7-1 時順手參考版面，不單獨吸收」——7-1 已完成（`b54697e`），且現樹設定頁已用自己的 `_add_grid_row`/`QCheckBox` 慣例，無需再單獨補這項。
  - **16-4 PROVIDER_MODELS 逐模型下拉選單**：延續 `146f104` 當時的既有決策（現樹目前對任何 LLM 供應商都沒有逐模型下拉選單的 UI 慣例），非本次任務重新評估的對象。
  - 本次重新檢視以上四類項目，**沒有發現任何「情勢改變、現在值得做」的新事證**，維持原判斷。
- **誠實聲明（未實機驗證範圍）**：本次開發機仍沒有 `PyQt6`/`sounddevice`（`faster_whisper`/`ctypes`/Win32 API 可用，因本機本身是 Windows 11）。`ui/settings_window.py` 新按鈕（📦 匯出診斷包）與麥克風測試擋板移除後的實際行為、`utils/diagnostics.py` 的 `collect_device_info()` 在「真的裝了 sounddevice 且有麥克風」情境下的輸出，均未在完整 PyQt6 環境下實機驗證，僅過 `py_compile` + 單元測試（`export_diagnostic_bundle`/`collect_env_info` 等函式本身已在真實 Windows 環境下直接執行過，非 mock）。
- **測試**：`python -m pytest tests/ -v`：232 passed, 10 skipped（起始 193 passed；本批新增 `tests/test_llm_prompts.py`（9 個）、`tests/test_soul_rules.py`（11 個）、`tests/test_diagnostics.py`（13 個），另有數個新檔被 `tests/test_smoke.py` 的全 repo py_compile 掃描一併計入；`tests/test_llm_config_keys.py` 排除 `prompts.py` 不列入 provider 掃描對象）。

## 2026-07-20 — subprocess_whisper worker 補讀詞彙庫 prompt 欄位（既有 bug 修復）

- **問題**：`stt/subprocess_whisper.py` client 端 `SubprocessWhisperSTT.transcribe()` 把 `vocab.manager.build_vocab_prompt()` 的結果放進 IPC 訊息的 `"prompt"` 欄位送給子行程 worker，但 worker 端 `_stt_worker` 迴圈自 `486ef3f`（13-2 抗幻覺參數移植）把轉錄呼叫抽成 `_run_transcribe()` 之後，一直是硬編字串「以下是繁體中文的語音內容：」當 `initial_prompt`，從未讀取 IPC 訊息裡的 `"prompt"` 欄位。實際效果：使用者在詞彙庫學到的專有名詞（自訂詞彙＋自動學習高頻詞）從未真正影響本地 Whisper 的辨識偏向，智慧詞彙學習功能只剩「事後文字修正」那半套，「餵給模型當上下文提示」的那半套形同虛設。
- **決定（修法）**：`_run_transcribe()` 新增 `initial_prompt` 參數（預設值沿用既有硬編字串 `DEFAULT_INITIAL_PROMPT`，向下相容）；`_stt_worker` 收到 `"transcribe"` 訊息時讀取 `msg.get("prompt")`，空/缺一律 fallback 回 `DEFAULT_INITIAL_PROMPT`，再轉交 `_run_transcribe()`。不改 client 端送出訊息的邏輯（本來就已經在送）、不改 IPC 訊息格式的鍵名。
- **決定（比照 Mac 版語義，取代而非串接）**：查證 Mac 主線 `stt/mlx_whisper.py`（`git show 960f5e6:stt/mlx_whisper.py:128-129,154`；docs/mac-mainline-absorption-analysis.md 引用的 `51094bf` 是 Mac 原始碼庫的 commit hash，在本 repo 的 git 歷史中不可達，無法直接 `git show`）：Mac 版是 `prompt = build_vocab_prompt()` 之後直接 `initial_prompt=prompt`，單一參數位、無額外串接。而 `vocab/manager.py:build_vocab_prompt()` 本身的回傳值就已經是完整語句——無自訂/高頻詞彙時回傳預設語境句本身，有詞彙時回傳「以下是繁體中文的語音內容，常用詞彙包含：X、Y、Z。」這種擴充後的完整句子。因此正確語義是「用 prompt 欄位整個取代 initial_prompt」，不是「預設句 + 詞彙句」兩段拼接——`stt/local_whisper.py:40-51` 本來就是這樣接的（`initial_prompt=prompt` 直接用），此次只是讓 `subprocess_whisper.py` 追上同一套語義。
- **檢查範圍**：`stt/local_whisper.py`（非 Windows fallback 路徑）比對後確認本來就正確——`transcribe()` 一開始就 `prompt = build_vocab_prompt()` 並直接當 `initial_prompt=prompt` 傳入 `model.transcribe()`，無需修改。
- **測試**：`tests/test_stt_transcribe_params.py` 新增 4 個測試：`test_default_initial_prompt_when_not_specified`（未傳參數時沿用預設字串）、`test_custom_vocab_prompt_passed_through`（自訂詞彙 prompt 正確透傳到 `model.transcribe()` 的 `initial_prompt` kwarg）、`test_empty_or_none_prompt_falls_back_to_default`（空字串/`None` 都 fallback 回預設字串，不把空值直接餵給模型）、`test_worker_source_reads_prompt_field_from_ipc_message`（`_stt_worker` 需要真實子行程環境無法直接呼叫測試，改用 `inspect.getsource()` 靜態檢查原始碼確實含 `msg.get("prompt")` 與正確的 `_run_transcribe()` 呼叫參數，防未來重構時再度遺漏這個欄位）。`python -m pytest tests/ -v`：193 passed, 10 skipped（原 189 passed，含此次新增 4 個測試）。
- **意外發現（已記錄，未另修）**：`docs/mac-mainline-absorption-analysis.md` 與 `stt/subprocess_whisper.py`/`stt/local_whisper.py` 程式碼註解裡引用的 `51094bf:stt/mlx_whisper.py` commit hash，在本 repo（`SanHsien/voicetype`）的 git 歷史中實際指向一個無關的 README 修訂 commit（`Revise README contributors and version info`），而非 mlx_whisper.py 的任何版本。`git log --all --grep="51094bf"` 顯示這個 hash 是先前 review/absorption 分析引用「Mac 原始碼庫」（另一個獨立 repo）的 commit，在本 repo 裡本來就不可達，不是本次任務造成或範圍內的問題，此處僅記錄以免下次有人誤用 `git show 51094bf` 撲空。

## 2026-07-20 — Mac 主線功能吸收第 2-5 項（13-2／16-4／7-1~7-3／7-4）

依 `docs/mac-mainline-absorption-analysis.md`「建議吸收順序」第 2-5 項，逐項 atomic commit（`486ef3f`／`146f104`／`b54697e`／`6565fad`）。

- **決定（13-2 抗幻覺轉錄參數）**：`stt/subprocess_whisper.py`／`stt/local_whisper.py` 的 faster-whisper `transcribe()` 呼叫加 `no_speech_threshold=0.6` + `condition_on_previous_text=False`，比照 `51094bf:stt/mlx_whisper.py` 數值原封不動搬。`subprocess_whisper.py` 的呼叫點在龐大的 `_stt_worker` 子行程入口函式內（依賴真實 WhisperModel/子行程環境，無法整函式單元測試），抽成獨立的 `_run_transcribe(model, audio_np, language)` 供 mock 驗證，行為不變。
- **決定（16-4 OpenRouter fallback＋預設模型）**：搬 `OPENROUTER_FALLBACK_MODELS`/`_is_missing_model_error()`/`_candidate_models()`，預設模型改 `google/gemini-2.5-flash`（Mac 版落地選定值，未自行上網猜新模型）。**刻意不搬 13-1（`llm/prompts.py` 集中化）**——本次任務範圍明訂只做「建議吸收順序」第 2-5 項，13-1 屬次梯隊；`refine()` 簽章維持現樹既有的「呼叫端傳入 prompt」設計，不改介面。也**刻意保留現樹既有的 payload 差異**（`temperature: 0.1`、`[指令：嚴禁回答內容...]` 注入前綴）而非對齊 Mac 版拿掉 temperature——這是現樹既有的獨立決策，非本次任務要處理的分岔。STT 側 OpenRouter（`stt/openrouter_stt.py`）比對 Mac 版後確認雙方都是固定 `openai/whisper-large-v3`、無 fallback 邏輯，故不動。
- **決定（7-1/7-2/7-3 麥克風裝置/增益/AGC，架構層面最大取捨）**：現樹 `audio/recorder.py` 是 **callback-based**（`sd.InputStream(callback=self._callback)`，PortAudio 自己開執行緒呼叫），Mac 版 `51094bf` 已改寫成 **polling-thread**（`stream.read()` 在自建的 `_poll_thread` 迴圈裡跑）。兩種架構互斥，選擇「把 device/gain/AGC 功能織進現樹的 callback 架構」而非改用 Mac 版的 polling 架構整檔覆蓋——理由：(1) 現樹 callback 架構已跑穩，`_poll_audio` 反而是現樹裡從未被呼叫的死碼，貿然換架構風險遠高於加參數；(2) 兩種架構在「加 device 參數、對 indata 做放大、算 RMS 更新 AGC」這幾個切入點完全等價，功能可以 1:1 對應搬過去,不需要連架構一起搬。純數學（`apply_gain`/`update_agc_factor`/`rms_of`）抽成新檔 `audio/gain.py`——因為 `audio/recorder.py` 頂層 `import sounddevice as sd`，在沒裝 PortAudio 的環境（包含本次開發機）連 import 都會失敗，抽出無 sounddevice 依賴的純函式是這幾項邏輯唯一能在本機被單元測試覆蓋的方式。`mic_device`/`mic_gain`/`mic_gain_auto` 三個新 config 欄位全部列入 `LOCAL_KEYS`（機器特定，不雲端同步），與 Mac 版一致。**`audio/auto_trigger.py`（VAD 全時模式）刻意不碰**——它有自己獨立的 `sd.InputStream`，不共用 `AudioRecorder` 實例，任務範圍也明訂只動 `audio/recorder.py`；`tests/test_recording_mutex.py` 驗證過 PTT/VAD 互斥狀態機不受影響。Settings UI 用現樹既有的 `_add_grid_row`/`QCheckBox` 慣例（現樹沒有 Mac 版的 `ToggleSwitch`/`QSlider` 自訂元件慣例，僅新增標準 `QSlider`），未仿造 Mac 版整個 `PROVIDER_MODELS` 式的複雜 QGridLayout 卡片佈局。
- **決定（7-4 靜音預檢）**：`AudioRecorder.stop()` 計算峰值 RMS（`audio.gain.peak_rms`/`is_silent`，門檻沿用 Mac 版 0.3%），設 `self.is_silent`；`ui/app.py:_on_audio_complete`（對應 Mac 版 `main.py:_on_record_stop`）在派工到 `_process_audio` 前檢查，靜音就跳過整段 STT。放在 `_on_audio_complete` 而非 `_process_audio` 內部，是因為 `_process_audio` 同時被 VAD 段落佇列（`_ensure_segment_worker`）呼叫，而 VAD 路徑不經過這個 `AudioRecorder` 實例、也已有自己的 `min_speech_sec` 靜音把關，把檢查放在 `_process_audio` 裡會誤判 VAD 呼叫也要看 `recorder.is_silent`（屆時該屬性其實是上一次 PTT 錄音的殘留狀態，非 VAD 這次的）。
- **誠實聲明（未實機驗證範圍）**：本次開發機沒有 `PyQt6`、`sounddevice`、`faster_whisper`（後者其實有裝，但無法起真實模型）。`ui/settings_window.py` 的裝置下拉選單/插拔輪詢、`audio/recorder.py` 的 `sd.InputStream` 實際接線、STT 抗幻覺參數在真實 Whisper 模型上的效果，全部只過 `py_compile` 語法檢查，未在 Windows 實機驗證行為。純邏輯部分（`audio/gain.py` 全部函式、`llm/openrouter.py` fallback 判斷、`stt/subprocess_whisper.py._run_transcribe` 參數傳遞）有 mock/純函式單元測試覆蓋。

## 2026-07-19 — llm/claude.py 欄位名不一致修復（追加，六項修復時的意外發現）

- **決定**：`llm/claude.py` 讀 `claude_api_key`/`claude_model`，但 `config.py:DEFAULT_CONFIG` 與設定視窗（`ui/settings_window.py:1601,1898`）實際儲存的是 `anthropic_api_key`/`anthropic_model`——修法採「改 `llm/claude.py` 對齊 config/UI 既有欄位名」而非反向改 config：使用者已存的設定資料用的是 `anthropic_*`，改引擎端零遷移成本；反向改則要動 DEFAULT_CONFIG、UI 讀寫兩處、LOCAL_KEYS 收集邏輯還得加資料遷移，風險面完全不成比例。此 bug 的實際效果是 Claude LLM 引擎自始拿到空 key，`refine()` 的空 key 防護直接回傳原文——使用者選了 Claude 引擎會以為有潤飾，實際從未呼叫過 API（靜默失敗，與 Gemini STT 選單死路徑同一類「UI 有選項、後端不通」問題）。
- **全 provider 檢查**：grep 全部 `llm/*.py` 與 `stt/*.py` 的 `config.get(...)` 逐一比對 DEFAULT_CONFIG——其餘 provider（openai/gemini/openrouter/qwen/deepseek/ollama、groq/gemini/openrouter STT）欄位名全部一致，僅 claude 一處中雷。`stt/subprocess_whisper.py` 讀的 `whisper_device`/`whisper_compute_type` 不在 DEFAULT_CONFIG 但屬「進階選項、預設 auto、UI 本來就不寫」的刻意設計，非同型 bug，不動。
- **防回歸**：新增 `tests/test_llm_config_keys.py`，用 AST 靜態掃描（不需安裝 provider SDK、任何環境都能跑）驗證每個 LLM provider 讀的 config 欄位名存在於 DEFAULT_CONFIG，未來新增 provider 打錯欄位名會直接紅燈。

## 2026-07-19 — REVIEW.md 風險表六項修復（API Key 同步／逾時／PTT-VAD 互斥／eval／diagnose_mic／Monaco）

- **決定（API Key 本地化＋一次性遷移，風險表 #4）**：`config.py` 把所有 `*_api_key` 欄位（以 `endswith("_api_key")` 動態收集，新增 provider 自動涵蓋）併入 `LOCAL_KEYS`，金鑰從此只落 `config_local.json`。既有使用者的 `config_global.json` 可能已含金鑰且位於雲端同步資料夾，故 `load_config()` 做一次性遷移：偵測到全域檔含現屬 LOCAL_KEYS 的欄位就搬進本機檔並「立即改寫全域檔落盤」——不等下一次 `save_config()`，避免載入後、儲存前的空窗期金鑰仍躺在同步資料夾。遷移值同時直接寫入 `config_local.json`，確保重開程式不遺失。選「遷移」而非「僅改白名單」：僅改白名單會讓舊金鑰永遠殘留在同步目錄（load 端只是不再讀它），洩漏面沒有真正關閉。
- **決定（逾時統一常數，REVIEW 3 節）**：只補「完全沒有明確 timeout」的兩個 SDK 呼叫點（`llm/claude.py` anthropic、`stt/groq_whisper.py` groq，SDK 預設皆 600s），統一走新檔 `net_config.py` 的 `CLOUD_REQUEST_TIMEOUT_SECONDS = 60`（語音上傳/LLM 回應取 30-120s 建議區間折衷）。已各自帶 timeout 的 9 個 httpx/requests 呼叫點刻意不動——它們的值（5-30s）是作者依各服務特性調過的，硬改成統一值反而是行為變更。
- **決定（PTT/VAD 互斥採 PTT 優先，風險表 #10）**：新增 `audio/mutex.py:PttVadMutex` 純邏輯狀態機（無 sounddevice/PyQt6 依賴，可在任何環境單元測試），`ui/app.py` 接線。政策選 PTT 優先而非先來先贏：PTT 是使用者主動按鍵、意圖明確；VAD 是背景被動偵測，可能被環境雜音誤觸發。對使用者最不意外的行為是「我按了鍵，就照我按的來」——PTT 按下時捨棄進行中的 VAD 段落；PTT 錄音中 VAD 觸發被忽略、其遲到的音訊一併丟棄（避免多冒出一份來路不明的輸出）。VAD 串流本身不關閉（全時模式不中斷），只丟段落。
- **決定（eval → ast 白名單，風險表 #11）**：`actions/builtins.py:run_calculator` 移除 `eval()`，改 `ast.parse(mode="eval")` 後逐節點白名單檢查（常數、`+ - * / ** % //`、正負號），`Name`/`Call`/`Attribute` 等節點在解析階段直接 `ValueError`——擋的是節點類型而非字串黑名單，`__import__` 這類繞法在結構上就不可能通過。另設次方指數上限 1000 防 `9**9**9` 卡死行程。守門測試用 AST 檢查模組內不得再有 `eval`/`exec` 呼叫節點。
- **決定（diagnose_mic.py 重寫而非刪除，風險表 #9）**：二選一中選重寫。理由：(1) `release_win.ps1:61` 的可攜版打包清單按檔名複製本檔，刪檔會斷打包鏈，而本次任務明令不動 `release_win.ps1`；(2) 麥克風無聲是語音輸入軟體最常見的使用者支援問題，一支真的能在 Windows 跑的診斷腳本有實際價值。新版：sounddevice 檢查（未裝給明確訊息）→ `query_devices()` 列輸入裝置＋標示預設 → 以 `audio/recorder.py` 同參數實錄 0.5 秒回報 RMS，近 0 時提示隱私權/裝置/靜音三方向。已實機驗證可執行。
- **決定（Monaco → Consolas，風險表 #12）**：`ui/settings_window.py:1086,1154` 兩處靈魂/情境編輯區選 `Consolas` 而非檔案他處慣用的 `Microsoft JhengHei`——這兩處是編輯 prompt/markdown 的文字區，等寬字型比黑體合適（REVIEW.md 建議 #4 也傾向此選項），且 Consolas 為 Windows 內建、無 fallback 風險。

## 2026-07-19 — REVIEW.md 四項修復（installer 死引用／Gemini STT／幻覺過濾／paths 死碼）

- **決定（installer）**：`voicetype_installer.iss:44` 引用不存在的 `platform_layer\*`，直接移除該行，不補建空目錄或加 `skipifsourcedoesntexist` 旗標。理由：找不到任何歷史紀錄或文件顯示這個目錄曾經規劃過具體用途，判斷是打包腳本重構到一半的殘留，移除比留著一個「未來可能有用」的空引用更誠實。已寫一次性檢查腳本核對其餘 12 條 `Source:` 引用全數存在於樹中。
- **決定（Gemini STT）**：`stt/gemini_stt.py:GeminiSTT` 這個類別本身已經存在（且 `config.py` 的 `gemini_api_key`/`gemini_stt_model` 欄位也已對齊），只是 `stt/__init__.py:get_stt()` 沒有對應分支——採「補分派分支」而非「移除 UI 選項」，因為現成實作邏輯平台無關（純 httpx API 呼叫，不含任何 macOS/MLX 相依）。順手修正 `GeminiSTT.transcribe()` 本身兩個既有 bug：函式簽章與呼叫端 `ui/app.py`（`self.stt.transcribe(audio_data, language=lang)`）不符（會 TypeError）、以及用 `soundfile.write()` 把呼叫端已經是完整 WAV 容器的 bytes 當裸 PCM 陣列重新編碼（必定 `IndexError`，被 broad except 吞掉後永遠回傳空字串）。只修到讓 Gemini 這條路徑本身正確為止，沒有連帶修正 `stt/openrouter_stt.py` 裡幾乎一模一樣的 WAV 重複編碼問題（同一個模式、同一種 bug，但不在本次任務範圍內）——留給下一次任務處理，見下方「意外發現」。
- **決定（幻覺過濾）**：把舊版 Mac 主線（`51094bf`）`stt/mlx_whisper.py` 裡的 `_is_hallucination`/`_has_dominant_repetition` 抽成新的、不依賴任何 STT 引擎實作的 `stt/hallucination_filter.py`，接在 `ui/app.py:_process_audio` 收到 STT 文字之後的統一路徑呼叫，對本地（`subprocess_whisper.py`）與雲端（groq/openrouter/gemini）引擎一視同仁生效。刻意不放進 `subprocess_whisper.py` 的子行程內，避免增加子行程與主行程之間的 IPC 訊息格式複雜度。這個決定推翻了本檔案 2026-07-19「11 項開發鷹架落地」條目裡「`test_stt_hallucination_filter.py` 測試對象在現行樹中已不存在，跳過」的舊決策——當時只是沒空重新設計接線位置，並非邏輯真的用不上。
- **決定（paths.py 死碼）**：`paths.py:56-58` 宣告的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`（指向 `SYNC_BASE_DIR` 雲端同步目錄）已用 grep 驗證全 repo 沒有任何地方引用，`vocab/manager.py`/`memory/manager.py`/`stats/tracker.py` 實際上各自呼叫 `get_data_dir()`（本機 `APP_DATA_DIR`）。採清理而非補實作：直接移除三個宣告並加註解說明現狀，不把「詞彙/記憶/統計真的跨裝置同步」這個功能一併做掉——那是需求變更＋資料遷移，需要另外討論範圍與資料搬遷方式。`paths.py:59` 的 `AI_PERMANENT_MEMORY_PATH` 同樣未被引用，但不在本次任務指定範圍（僅 56-58 行），暫不處理，留意日後若清理死碼可一併檢查。
- **意外發現（已處理，維護者追加授權後同批修復）**：`stt/openrouter_stt.py:transcribe()` 有和修復前的 `GeminiSTT` 完全相同的 bug——`soundfile.write(buf, audio_data, sample_rate, format="WAV")` 把呼叫端傳入的完整 WAV bytes 當作裸樣本陣列重新編碼，必定 `IndexError`，導致選擇 OpenRouter STT 引擎此前也是永遠回傳空字串；且簽章 `(audio_data, sample_rate=16000)` 與呼叫端 `ui/app.py` 的 `transcribe(audio_data, language=lang)` 不符（TypeError）。已比照 `GeminiSTT` 修法處理：拿掉 `soundfile` 重新編碼、直接把原始 WAV bytes 包 `BytesIO` 上傳（此 API 走 multipart 檔案上傳，非 base64）、簽章對齊 `BaseSTT` 的 `(audio_bytes, language="zh")` 並讓呼叫端傳入的 `language` 優先於 config 預設值。新增 `tests/test_openrouter_stt.py`（httpx.post 全 mock）。

## 2026-07-19 — README Windows 化改寫

- **決定**：`README.md`/`README.en.md` 改寫為「本 repo 只做 Windows 10/11」的定位說明，功能特色、安裝步驟（`requirements-win.txt`/`requirements-cuda-win.txt`）、設定欄位表全部對照現行 `config.py`/`paths.py` 實際內容重寫，不再沿用上游可能含 macOS 敘述的版本。
- **理由**：README 是使用者第一入口，必須誠實反映「這是哪個平台、怎麼裝、裝完設定長怎樣」，避免使用者照著 macOS 步驟在 Windows 上卡關，或反過來誤以為這裡有 macOS 支援。

## 2026-07-19 — 11 項開發鷹架落地（依 `dev-env-best-practices.md` 範本）

- **決定**：依維護者先前掃描 `C:\Users\SanHsien\OneDrive\文件\GitHub\` 下活躍 repo（`gpt-ai-assistant`、`openshelf`、`sticker-forge`、`yt_fetch` 等）歸納出的「開發環境鷹架最佳範本」，把 voicetype 落地缺口全部補齊：`CLAUDE.md`（新建，薄補丁指回 `AGENTS.md`）、`pyproject.toml`（套件 metadata + pytest 設定）、`tests/` + pytest（`test_smoke.py` 全 repo `py_compile` + 純邏輯模組匯入、`test_config.py` 設定讀寫回圈）、`CHANGELOG.md`（Keep a Changelog 格式，`VERSIONS.md` 保留不動、兩者並存）、`.gitattributes`（`.bat`/`.cmd`/`.ps1` 強制 CRLF）、`.github/workflows/ci.yml`（`windows-latest` + Python 3.12，`py_compile` + `pytest` 子集，不裝 CUDA/大模型）。同時全面改寫 `AGENTS.md`/`SKILL.md`/`docs/DEVELOPMENT.md`，清除「Mac 純化版 main」時代遺留的錯誤描述（`mlx_whisper.py`、`requirements.txt` 的 `pyobjc-*`、`pynput`、`.aicore` submodule、`openspec/`、已不存在的 `HANDOVER.md`/`AI_MEMORY.md` 引用）。
- **決定（測試移植策略）**：從舊版 Mac 主線（`git show 51094bf`）撈回的 6 支根目錄 `test_*.py`，逐一檢查測試對象模組是否仍存在於現行 Windows-only 工作樹——只有 `test_save.py`（→ `tests/test_config.py`）與 `test_qkey.py`（→ `tests/manual/manual_qkey_check.py`，非 pytest 收集）可移植；`test_stt_hallucination_filter.py`、`test_stt_language_selection.py`、`test_openrouter_fallback.py`、`test_path.py` 的測試對象模組/邏輯在現行樹中已不存在或已簡化，跳過並在 `docs/DEVELOPMENT.md` 逐項記明原因，不硬套會對著不存在行為斷言的測試。
- **理由**：`AGENTS.md`/`SKILL.md` 都寫著「Claude Code 專屬補充見 `CLAUDE.md`」但檔案不存在，是文件對外承諾與實際不符的直接缺口；`docs/DEVELOPMENT.md` 舊版測試章節列的 6 支腳本在現行工作樹中一支都不存在（Windows 專用化的 `v3.0.0` 整理已移除），繼續照抄等於教下一個 AI/開發者跑不存在的檔案。補上 `pytest` 骨架與誠實的移植/跳過紀錄，比「宣稱有測試」但實際手動腳本已全滅更符合 AI 協作核心規則裡「不模擬、完成必附證據」的要求。

## 2026-07-19 — 雙軌授權聲明 + 引入上游 win-stable 分支

- **決定（授權）**：維護者拍板採雙軌 `LICENSE`：上游程式碼維持「無正式授權、著作權屬原作者」的誠實揭露；SanHsien 在本 fork 新增的原創部分掛 MIT（© 2026 SanHsien）。MIT 僅覆蓋新增部分。`NOTICE.md` 同步更新。
- **決定（Windows 路線）**：專案目標是 Windows 版。查證上游 `win-stable` 分支仍活躍（2026-07-08 v3.0.1，含 `requirements-win.txt`、`setup_win.bat`、`voicetype_installer.iss` 等完整 Windows 工具鏈），已 fetch 進本 fork 並推至 `origin/win-stable`。不走「把 Mac 純化的 main 修回跨平台」路線。
- **理由**：main 分支自 v2.9.0 起被 Mac 純化（REVIEW.md 2026-07-19 版結論，Windows 健康分數 2/10），以活躍維護的 win-stable 為 Windows 開發基底成本低、風險小。

## 2026-07-19 — 建立開發鷹架，比照 sticker-forge / gpt-ai-assistant

- **決定**：為此 fork 補上 AI 接手與維護文件——`AGENTS.md`、`NOTICE.md`、`SKILL.md`、`docs/DEVELOPMENT.md`、`docs/DECISIONS.md`（本檔）、`README.en.md`，格式比照既有的 `SanHsien/sticker-forge` 與 `SanHsien/gpt-ai-assistant` 兩個 repo。既有檔案（`README.md`、`CLAUDE.md`、`HANDOVER.md`、`AI_MEMORY.md`、`VERSIONS.md`、`config.py` 等）不變動。
- **Review 採 latest-only**：比照另兩個 repo 的慣例，`REVIEW.md` 只放最新一次專案覆核於根目錄，不逐版累積歷史；本次鷹架建立不含 `REVIEW.md`（由另一個 agent 負責）。
- **授權誠實揭露**：查證後確認上游 `jfamily4tw/voicetype4tw-mac` 與本 fork 都沒有正式的 `LICENSE` 檔（`gh api .../license` 回 404、`licenseInfo: null`）。上游 README 僅以口語聲稱「開源」、「完全免費」，不構成正式授權條款。因此 `NOTICE.md` 誠實記錄查證過程與結論，不捏造 MIT/Apache 等授權聲明，本 fork 定位為個人研究與改良用途。
- **理由**：讓 Claude Code / Codex 等 agent 接手時有一致的專案定位、架構速覽與驗證方式；本 fork 的維護環境（Windows 11 原生）與上游原生平台（macOS）不同，文件需明確標註平台差異（尤其 `requirements.txt` 的 macOS 專屬套件、`windows_cuda_qt_crash_postmortem.md` 記錄的已知地雷）。
