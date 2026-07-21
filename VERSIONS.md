# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）開發版本全紀錄 (面向物件分析)

本檔案用於精確紀錄「使用者需求」與「實際變更」的對照，並連結至 Git 提交與備份紀錄。最新版本置頂。

---

## [V3.2.0 補充二] - 2026-07-22 (品牌殘留全面清掃＋原作者個人網址移除)
> 維護者實機驗證時發現：品牌雖已改名「聲成文 VoxProse」，程式 UI 仍多處顯示舊名「嘴炮輸入法」，`REVIEW.md` 也混入簡體字（「個人」一詞誤植為簡體）。任務進行中追加規格：移除程式 UI 裡所有指向原作者個人社群/贊助頁的連結（保留署名文字）。純文字/資產清掃，版本號／`BUILD_ID` 不變。詳細判斷理由見 `docs/DECISIONS.md` 2026-07-22 條目。

### UI 品牌殘留（使用者可見字串）
- `ui/menu_bar.py:36,63`：浮動選單/系統匣選單頂部標籤「嘴炮輸入法」→「聲成文 VoxProse」。
- `ui/settings/dashboard_page.py:40`：Dashboard 頁中文標題 `QLabel` 改「聲成文」。
- `ui/settings_window.py:467`／`ui/settings/vocab_mem_page.py:154`／`ui/settings/soul_page.py:194`：三處 `QMessageBox` 標題改「聲成文」。
- `ui/app.py:98`：歷史版本註解裡的雙關舊名字面量拿掉（為了讓守門測試可對 `ui/**` 做無例外掃描）。
- `vocab/manager.py:206`：docstring 範例改用新品牌同音示範（聲成文／生成文）。

### 檔名更名
- `啟動嘴炮輸入法.bat` → `啟動聲成文.bat`（`git mv`），同步更新引用：`release_win.ps1:68`、`docs/DEVELOPMENT.md:66,143`。
- `run_voicetype.bat`／`voicetype_installer.iss` 檔名本身**維持不變**——評估後判斷風險/文件維護成本大於使用者可見效益，理由見 `docs/DECISIONS.md`。

### 原作者個人網址移除（維護者中途追加規格）
- `ui/settings_window.py`：移除側欄 SNS 按鈕區塊（YouTube／Facebook／Instagram／TikTok／Threads／個人網站六個連結），保留作者署名文字；連帶清掉未使用的 `import os`／`Path`／`SNSButton` import。
- `ui/settings/common.py`：`SNSButton` 類別刪除（唯一使用處已移除），連帶清掉只被它使用的 `QIcon`／`QSize`／`QUrl`／`QDesktopServices` import。
- `voicetype_installer.iss:7`：`MyAppURL` 從上游 repo 改為本 fork repo（`AppSupportURL`／`AppUpdatesURL` 透過巨集自動跟著改）。
- `llm/openrouter.py:53`：`HTTP-Referer`／`X-Title` 從舊網址/舊品牌名改為本 fork repo／`VoxProse`。
- 孤兒資產 `git rm`：`assets/sns-{youtube,facebook,instagram,tiktok,threads,4tw}.png`、`assets/donate-linepay.jpg`（全 repo 零引用確認後刪除）。

### 簡體字清掃（Python 逐字元比對，非 grep 位元組比對）
- 共 6 處誤植的簡體字，皆為打字疏漏，逐字改回繁體對應字：`REVIEW.md:14`（「個人」一詞）、`VERSIONS.md:226`（「問題」一詞）、`docs/DECISIONS.md:86`／`:132`（「換」字）、`docs/DECISIONS.md:213`（「補」字）、`tests/test_stt_engine_dispatch.py:9`（docstring 內「靜」字）。修正後全 repo 零殘留。

### 新增守門測試
- `tests/test_brand_and_charset_guard.py`：三個 pytest 測試——全 repo 簡體字掃描、`ui/**` 舊品牌字串掃描、`ui/**` 原作者個人網域字串掃描。

### 驗證
- `python -m pytest tests/ -v`：270 passed（266 基準 + 3 新守門測試 + 1 個 `test_smoke.py` 自動為新測試檔產生的 `test_py_compile` 參數化案例）、10 skipped，與基準一致。全 repo `py_compile` 0 錯誤。

### 待辦（非本次任務範圍，供下次安排）
- `assets/` 內 7 張截圖仍顯示舊品牌 UI（視窗標題／選單會出現「嘴炮輸入法」），需要在有 PyQt6 的 Windows 實機環境重新截圖替換。

## [V3.2.0 補充] - 2026-07-21 (品牌改名第二階段：資料路徑正名)
> 第一階段（下方 [V3.2.0] 條目）刻意保留 `%APPDATA%\VoiceType4TW`／`Documents\VoiceType4TW_Sync` 兩個實際路徑值不動，理由是「怕有真實使用者資料」。維護者事後確認本機從未實際使用過本程式，兩個目錄查證皆不存在，不需要顧慮 v3.1.0 release ZIP 是否有人下載安裝過——第一階段規劃的「遷移邏輯六原則」（`docs/DECISIONS.md`／`docs/BRANDING.md`）因此整批作廢，未實作、也不會實作。改為直接把路徑常數與所有字面量改名，不留 old→new 搬移/備份/fallback 程式碼（那會是永遠不會執行到的死碼）。版本號／`BUILD_ID` 不變（純資料路徑正名，非功能變更）。

### 路徑改動
- `paths.py:9`：`APP_DATA_DIR` 目錄名 `VoiceType4TW` → `VoxProse`。
- `paths.py:35`：`get_sync_base_dir()` 預設值 `Documents\VoiceType4TW_Sync` → `Documents\VoxProse_Sync`。
- `whisper_models`、`config_local.json`、`config_global.json`、`soul/`、`keystrike.log`、`debug.log`、`sync_path.txt` 等全部子項透過 `APP_DATA_DIR`/`SYNC_BASE_DIR`/`get_data_dir()` 常數跟著走，無需個別修改。

### 打包鏈與工具同步
- `setup_win.bat`：`MODEL_DEST` 改 `%APPDATA%\VoxProse\whisper_models`；console 標題/banner；`csc` 編譯輸出 `VoxProse.exe`。
- `release_win.ps1`：`$ModelSrc`/`$ModelDest` 改 `%APPDATA%\VoxProse\...`；隨附啟動器與可攜版說明文字改名。
- `create_shortcut.ps1`：偵測的原生啟動器檔名 `VoxProse.exe`。
- `build_win.py`：PyInstaller `APP_NAME` 改 `VoxProse`（決定 `dist/` 輸出資料夾與 exe 名稱）。
- `tools/launcher.cs`：三處 MessageBox 標題、頂部註解。
- `tools/get_portable_python.ps1`：console banner。
- `.gitignore`：打包輸出樣式 `VoiceType4TW_Win_Stable_V*/` → `VoxProse_Win_Stable_V*/`。
- `tests/test_smoke.py`：release staging 資料夾排除樣式同步改名（與上面 `.gitignore` 樣式一致）。

### `voicetype_installer.iss`（授權範圍擴大，補做第一階段未做的兩項）
- `MyAppName`：`VoiceType4TW` → `VoxProse`（連帶 Start Menu／桌面捷徑安裝後顯示名稱、`DefaultDirName`）。
- `AppId`：換發新 GUID（`C3912B98-0808-4B52-84F5-F5BB7A040B9A`）。換 `AppId` 等同視為新程式，舊版安裝不會被偵測升級——本專案無既有安裝基礎（維護者從未安裝過任何版本），可接受，見 `docs/DECISIONS.md`。

### 散落品牌字樣（stage 1 遺漏，本次一併掃到）
- 啟動/診斷 log：`main.py:114`、`ui/app.py:139`（`log.info` 啟動橫幅）、`self_check.py:47`、`tools/doctor.py:11`、`tools/download_models.py:40`、`tools/check_dependency_freshness.py`（docstring/argparse description）、`utils/diagnostics.py:93,223`（診斷報告標題／桌面 ZIP 檔名）、`ui/settings/dashboard_page.py:315`（註解）、`啟動嘴炮輸入法.bat:2`、`run_voicetype.bat:3,45`。
- 文件內對應路徑：`README.md:160`、`README.en.md:160`、`AGENTS.md:45`、`SKILL.md:54`、`docs/DEVELOPMENT.md:81,98`、`quality_control_checklist.md:32,34`、`安裝下載教學.md`（全檔 6 處路徑）。

### 死碼修正
- `ui/settings_window.py:229-235`：側欄 logo 連續宣告兩次 `QLabel("VoxProse")`，第一次的物件從未加入 layout。移除未使用的第一個宣告。

### `AGENTS.md`／`SKILL.md` 過時敘述修正
- 兩處「不宣稱上游程式碼有正式開源授權／雙軌說明」的舊措辭已過時（`NOTICE.md` 早已正確反映上游 2026-07-20 補齊 MIT、本 fork 全 MIT），改為指向現況，舊雙軌查證過程僅作背景記錄註明。

### 刻意保留原名（上游沿革/歷史敘述，未動）
- `NOTICE.md`、`LICENSE`（含上游授權全文版權行）、`pyproject.toml` 的 `description`、`README.md`/`README.en.md`/`REVIEW.md`/`SKILL.md`/`AGENTS.md` 開頭的 fork 出處敘述、`ui/about_window.py` 的「Derived from VoiceType4TW」署名段落、`main.py:89-91` 與 `tests/test_config.py:7` 描述「這行程式碼過去長什麼樣子」的重構註解/docstring、`docs/DECISIONS.md`／`CHANGELOG.md`／`VERSIONS.md` 既有的歷史版本條目（描述當時決策事實，不可回溯竄改）。

### 驗證
- `python -m pytest tests/ -v`：266 passed, 10 skipped（與基準一致）。
- 全 repo `py_compile`：0 錯誤。
- 臨時腳本 `import paths` 後印出常數確認為新路徑；`paths.initialize_paths()` 在乾淨環境成功建立 `%APPDATA%\VoxProse` 完整目錄樹與 `Documents\VoxProse_Sync\soul`；驗證後已刪除測試建立的目錄，環境維持乾淨。
- 全 repo grep `VoiceType4TW` 的路徑語意殘留為零（僅餘上述刻意保留的歷史/沿革敘述）。

### 意外發現
- 驗證前 grep 發現 `%APPDATA%\VoiceType4TW\{memory,stats,vocab}` 仍存在（含一份預設種子 `custom_vocab.json`，時間戳為本次任務執行當天），研判是先前品牌改名任務驗證過程留下的測試殘留，非真實使用者資料；不在本次路徑正名範圍內，未刪除，留給維護者自行決定是否清理。

## [V3.2.0] - 2026-07-21 (Rebrand: 聲成文 VoxProse, BUILD-3200-STABLE)
> 品牌改名＋署名補正批次：完整規格由維護者拍板，本版把工作樹內所有「VoiceType4TW／嘴炮輸入法」自稱改為新品牌「聲成文 VoxProse」，並補齊過去一直遺漏的 go-mask 署名層。

### 品牌規格
- 中文品牌「聲成文」／英文品牌「VoxProse」／組合呈現「聲成文 VoxProse」；完整名稱「聲成文｜本地優先 AI 語音輸入工具」；英文副標「Local-first AI Voice Typing for Traditional Chinese」；標語「自然開口，清楚成文。」／"Speak naturally. Write clearly."

### 署名補正
- 完整署名鏈補齊至所有出現作者/致謝之處：原創作者吉米丘（Jimmy）、CC58TW → 上游 Windows 專用版維護 **go-mask**（查證：上游 `win-go-mask-202607` 分支 README 明載「Windows 專用版維護：go-mask ｜ 協助開發：Claude Code」，本 repo 過去只把 go-mask 當分支名使用，從未當署名列出）→ 本 fork（Windows）維護 SanHsien。已補於 `NOTICE.md`、`README.md`／`README.en.md`、`LICENSE` fork 附加段、`ui/about_window.py`、`AGENTS.md` 專案宗旨。

### 程式面品牌改動（六項，附檔案:行號）
- 視窗標題：`ui/settings_window.py:81,83,92`（`聲成文 {VERSION_NAME}` / `VoxProse {VERSION_NAME}` 兩支路徑）；連帶發現並修正側欄 logo `ui/settings_window.py:229,233`（`QLabel("VoiceType4TW")` → `QLabel("VoxProse")`，未在原規格六項內但屬同一視窗的可見品牌字串）。
- 系統匣：字串實際來源在 `ui/app.py:112`（`TrayManager(title=...)` 呼叫端），而非 `ui/tray_manager.py`——後者只透傳呼叫端傳入的 `title` 參數，本身無品牌字面量；已改 `title="聲成文"`。
- 桌面捷徑：`create_shortcut.ps1:3-4`（十六進位字元碼 `聲成文` = `0x8072,0x6210,0x6587`）、`create_shortcut.ps1:28`（`Description` 改 `VoxProse - AI Voice Typing`）；`setup_win.bat` 本身未硬編捷徑名稱（呼叫 `create_shortcut.ps1` 產生），無需改動。
- About 視窗：`ui/about_window.py` 全面改寫（標題、品牌名、標語、署名鏈段落），對話框由 300×350 放大到 320×430 容納新增文字。
- Windows AppUserModelID：`utils/branding.py:9` 由 `jfamily.voicetype4tw.v87.ultimate.stable` 改為 `tw.sanhsien.VoxProse.windows`。
- Release ZIP 命名：`release_win.ps1:21-40`（版本號改自 `pyproject.toml` 動態解析主.次版號，資料夾/ZIP 命名改為 `ShengChengWen-Windows-<Edition>-v<major.minor>`）；`.github/workflows/release.yml` 核實為 `dist/*.zip` 萬用字元，無需改動。

### 版本推進（五處一致 3.2.0 / BUILD-3200）
- `paths.py`：`VERSION_NAME` → `"V3.2.0 Windows Edition (BUILD-3200-STABLE)"`，`BUILD_ID` → `"BUILD-3200-STABLE"`。
- `pyproject.toml`：`version` → `"3.2.0"`；另把 `name` 由 `voicetype` 改為 `voxprose`（純 packaging metadata，不影響 `requirements-win.txt` 安裝鏈，已 grep 確認無程式碼依賴此欄位值）。
- `voicetype_installer.iss`：`MyAppVersion` → `"3.2.0"`、`OutputBaseFilename` → `ShengChengWen-Windows-Setup-v3.2`（`MyAppName`/`AppId`/安裝捷徑名稱不在本次授權範圍，維持原樣）。

### 安全重構
- `main.py`：移除與 `paths.APP_DATA_DIR` 重複定義同一路徑值的寫死字面量（`os.path.join(os.environ.get('APPDATA', ''), 'VoiceType4TW')`），改直接引用已 import 的 `APP_DATA_DIR`。純重構，行為零變化，實際路徑值仍是 `%APPDATA%\VoiceType4TW`。

### 刻意不變
- `%APPDATA%\VoiceType4TW`（`paths.py:APP_DATA_DIR`）與 `Documents\VoiceType4TW_Sync`（預設同步目錄）兩個實際路徑值本次不動——設定、同步指標、模型、日誌、詞彙、統計多處直接使用，貿然改名會造成設定與日誌分裂。第二階段遷移計畫（六原則）已記錄於 `docs/DECISIONS.md`。

### 全 repo 文件改寫
- 逐檔檢視 `git ls-files "*.md"`：`README.md`／`README.en.md`／`AGENTS.md`／`SKILL.md`／`NOTICE.md`／`REVIEW.md`（僅署名/名稱字句）／`CHANGELOG.md`／`VERSIONS.md`（本檔）／`安裝下載教學.md`／`docs/DEVELOPMENT.md`／`docs/DECISIONS.md`／`docs/UPSTREAM.md`／`docs/REFERENCES.md`／`docs/mac-mainline-absorption-analysis.md`／`quality_control_checklist.md`／`windows_cuda_qt_crash_postmortem.md`／`LICENSE`。`soul/**/*.md` 逐檔 grep 確認不含產品名稱引用，判定不需改。GitHub repo 已由維護者更名為 `SanHsien/voxprose`（原 `SanHsien/voicetype`），全部 repo 內連結／clone 指令同步更新為新 repo 路徑；本機工作目錄名稱維持 `voicetype`（維護者尚未指示更名本機資料夾）。

### 驗證
- `python -m pytest tests/ -v`：見本檔提交紀錄與 `docs/DECISIONS.md` 對應條目的即時驗證結果。
- 全 repo `py_compile` 通過。

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
- **托盤選單修復**：解決 Windows 下儲存設定後圖示選單更新失敗的問題。

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
