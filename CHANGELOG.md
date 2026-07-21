# Changelog

本檔案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，是**對外快速掃描用的精簡摘要**，記錄從本 fork（SanHsien）建立開發鷹架起的變更。

完整的、逐版對照使用者需求與驗證證據的詳細歷史，見 [`VERSIONS.md`](VERSIONS.md)（本 fork 沿用上游既有格式，兩份文件並存、各司其職：`CHANGELOG.md` 給快速掃描，`VERSIONS.md` 給深入回溯）。版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

> **關於歷史 commit hash**：v3.1.0 發版時已把 fork 的開發歷史 squash 成單一 commit（`84d1b28`，見 `docs/UPSTREAM.md`）。本檔與 `docs/DECISIONS.md`、`REVIEW.md` 中引用的更早 hash（如 `04d82cc`、`aee3973` 等）屬 squash 前的開發過程紀錄，**已不存在於 git 歷史**，僅作為文件內的變更對照識別碼保留，無法 `git show`。

## [Unreleased]

## [3.2.0] - 2026-07-22

品牌改名：中文品牌「聲成文」／英文品牌「VoxProse」（組合呈現「聲成文 VoxProse」），標語「自然開口，清楚成文。」／"Speak naturally. Write clearly."。同時補正過去一直遺漏的署名鏈——上游 Windows 專用版維護者 **go-mask** 過去只被本 repo 當成分支名（`win-go-mask-202607`）使用，從未在 NOTICE／README／About 視窗等處以「維護者」身分列名；本版起在所有出現作者/致謝的地方補齊完整鏈：原創作者吉米丘（Jimmy）／CC58TW → 上游 Windows 專用版維護 go-mask → 本 fork（Windows）維護 SanHsien。

**實機驗證（2026-07-21～22）**：本版是本 fork 第一次在真實 Windows 桌面環境（有 PyQt6/sounddevice/真實麥克風/RTX 3060 的機器）完整跑過整條鏈路——乾淨 venv 安裝 `requirements-win.txt`、`self_check.py` 子行程實際辨識、`diagnose_mic.py` 列出 19 個真實裝置、Windows SAPI 合成語音經真實 Whisper 引擎正確辨識出中文文字（repo 史上首次）、`python main.py` 兩次啟動皆無崩潰（`windows_cuda_qt_crash_postmortem.md` 記載的 PyQt6/CUDA 崩潰未發生）、SettingsWindow 七分頁在含 sounddevice 的完整環境全數通過。過程中發現並修復 4 個真實 bug（見下方 Fixed）。未能驗證的邊界（真人語音音量、單獨語氣詞音訊往返、系統匣圖示像素辨識、真實雲端 API key、真實 CUDA 加速）見 `REVIEW.md` 第 7 節。

### Added

- **上游更新自動檢查**：`tools/check_upstream_updates.py` ＋ `.github/workflows/upstream-check.yml`——每週一 02:00 UTC（另支援 `workflow_dispatch`）檢查上游 `jfamily4tw/voicetype4tw-mac` 的三個追蹤分支（`win-go-mask-202607`／`win-stable`／`main`）是否有新 commit，透過 GitHub compare API 比對 `docs/UPSTREAM.md` 新增的「同步狀態標記區塊」（`<!-- sync-points:start/end -->` 內的 JSON，唯一真相源）記錄的 `last_reviewed`（已審視過的最新上游 commit），只回報比它新的變更；有更新時開/更新「上游更新檢查」issue（比照既有 `dependency-freshness.yml` 的 search-or-create 邏輯）。每個分支同時記 `last_merged`（已實際併入本 fork 的上游 commit，等同 `git merge-base`）。新增「Skipped（審視後未採用）」表記錄審視後決定不採用的 commit 與理由，避免 `last_reviewed` 推進後這些決策消失在視野外。`AGENTS.md` 開發約定補一條處理流程；新增 `tests/test_upstream_check.py`（18 個測試，含真實 `docs/UPSTREAM.md` 解析、解析失敗防護、mock API 的報告產生，不打真網路）。
- `docs/BRANDING.md`：記錄第二階段 `%APPDATA%` 遷移計畫（新舊路徑並存、遷移六原則），本階段僅寫文件、不實作。
- **`tests/test_brand_and_charset_guard.py`**：新增三個守門測試，防止舊品牌名稱／簡體字／原作者個人網址回流——分別掃描全 repo 簡體字、`ui/**` 舊品牌字串、`ui/**` 原作者個人網域字串。
- **`stt/cuda_check.py`**：新增 `probe_cuda()` 共用 CUDA 加速判定函式，供 `ui/settings/dashboard_page.py`（Dashboard 顯示）與 `stt/subprocess_whisper.py`（實際 worker fallback 判斷）共用同一真相源，不再各說各話；新增 `tests/test_cuda_check.py`（6 種情境全 mock，不打真實硬體）。

### Changed

- **資料路徑正名（品牌改名第二階段）**：`%APPDATA%\VoiceType4TW` → `%APPDATA%\VoxProse`、`Documents\VoiceType4TW_Sync` → `Documents\VoxProse_Sync`（`paths.py:APP_DATA_DIR`／`get_sync_base_dir()` 預設值），`whisper_models` 等所有子目錄跟著走。維護者確認本機從未有真實使用資料，**不寫任何 old→new 遷移／備份／fallback 邏輯**，直接改常數與字面量。連帶更新走同一路徑的所有落點：`setup_win.bat`（`MODEL_DEST`、編譯輸出 `VoxProse.exe`）、`release_win.ps1`（`$ModelSrc`/`$ModelDest`、隨附啟動器改名、可攜版說明文字）、`create_shortcut.ps1`（偵測的啟動器檔名）、`tools/launcher.cs`（MessageBox 標題）、`build_win.py`（PyInstaller `APP_NAME`）、`.gitignore` 打包輸出樣式、`tests/test_smoke.py` 的 staging 資料夾排除樣式；以及散落在啟動/診斷 log 的品牌字樣（`main.py`、`ui/app.py`、`self_check.py`、`tools/doctor.py`、`tools/download_models.py`、`tools/check_dependency_freshness.py`、`tools/get_portable_python.ps1`、`utils/diagnostics.py`、`ui/settings/dashboard_page.py`）與文件內對應路徑（`README.md`／`README.en.md`／`AGENTS.md`／`SKILL.md`／`docs/DEVELOPMENT.md`／`quality_control_checklist.md`／`安裝下載教學.md`）。實機驗證確認新路徑確實生效（模型下載到 `%APPDATA%\VoxProse\whisper_models`）。上游專案名／fork 沿革敘述（`NOTICE.md`、`LICENSE`、`pyproject.toml` description 等）維持原名不動。
- **`voicetype_installer.iss` 補齊安裝版品牌（授權範圍擴大）**：第一階段刻意保留的 `MyAppName`（`VoiceType4TW` → `VoxProse`）與 `AppId`（換發新 GUID）本次一併改名，`DefaultDirName` 隨 `MyAppName` 巨集自動跟著換。換 `AppId` 等同視為新程式（舊版不會被升級覆蓋）——本專案無既有安裝基礎，可接受，見 `docs/DECISIONS.md`。
- **`AGENTS.md`／`SKILL.md` 雙軌授權敘述過時修正**：上游已於 2026-07-20 補齊 MIT、本 fork 早已收斂為全 MIT（`NOTICE.md` 已正確反映），但這兩處仍殘留舊版「不宣稱上游有正式授權／雙軌說明」的措辭，改為指向現況（全 MIT）並註明舊雙軌查證僅作背景記錄。
- **視窗標題／系統匣／About 視窗／桌面捷徑品牌字串**：`ui/settings_window.py`（2 處 `setWindowTitle` 改「聲成文」/「VoxProse」，側欄 logo `QLabel` 改「VoxProse」）、`ui/app.py`（系統匣 tooltip 改「聲成文」——實際字串來源在 `ui/app.py:112` 而非 `ui/tray_manager.py`，後者只透傳呼叫端傳入的 `title` 參數）、`ui/about_window.py`（標題／品牌名／標語／署名鏈全面改寫）、`create_shortcut.ps1`（桌面捷徑名稱與 Description 改為新品牌；`setup_win.bat` 本身未硬編捷徑名稱，無需改動）。
- **Windows AppUserModelID**：`utils/branding.py` 的 `APP_USER_MODEL_ID` 由 `jfamily.voicetype4tw.v87.ultimate.stable` 改為 `tw.sanhsien.VoxProse.windows`，同時讓 Windows 把新版視為獨立的工作列群組。
- **Release ZIP／安裝檔命名改用新品牌**：`release_win.ps1` 的可攜版資料夾/ZIP 命名由 `VoiceType4TW_Win_Portable_*_V<BUILD>` 改為 `ShengChengWen-Windows-<Edition>-v<major.minor>`（版本號改自 `pyproject.toml` 動態解析，不寫死）；`voicetype_installer.iss` 的 `OutputBaseFilename` 同步改為 `ShengChengWen-Windows-Setup-v3.2`（`MyAppName`/`AppId`/捷徑安裝名稱本次不在授權範圍內，維持 `VoiceType4TW` 原樣，見 `docs/DECISIONS.md`）。`.github/workflows/release.yml` 全部用 `dist/*.zip` 萬用字元，未硬編 ZIP 檔名，核實後無需改動。
- **版本推進 3.2.0**：`paths.py`（`VERSION_NAME`/`BUILD_ID` → `V3.2.0 Windows Edition (BUILD-3200-STABLE)`）、`pyproject.toml`（`version` → `3.2.0`；`name` 由 `voicetype` 改為 `voxprose`，純 packaging metadata，不影響 `requirements-win.txt` 安裝鏈）、`voicetype_installer.iss`（`MyAppVersion` → `3.2.0`）。
- **`main.py` 路徑重複定義消除（純重構，行為零變化）**：`main.py` 內原本寫死一份 `os.path.join(os.environ.get('APPDATA', ''), 'VoiceType4TW')` 計算 crash log 目錄，與 `paths.APP_DATA_DIR` 各自獨立定義同一個值；改為直接引用已 import 的 `APP_DATA_DIR`，實際路徑值完全不變（仍是 `%APPDATA%\VoiceType4TW`），為第二階段 `%APPDATA%` 遷移鋪路。`%APPDATA%\VoiceType4TW`（`paths.APP_DATA_DIR`）與 `Documents\VoiceType4TW_Sync`（預設同步目錄）兩個實際路徑值本次**不變**——遷移計畫見 `docs/DECISIONS.md`「第二階段」。
- **全 repo 文件品牌改寫與署名補正**：`README.md`／`README.en.md`／`AGENTS.md`／`NOTICE.md`／`SKILL.md`／`REVIEW.md`（僅署名/名稱字句，技術結論與問題總帳狀態不動）／`VERSIONS.md`／`安裝下載教學.md`／`docs/DEVELOPMENT.md`／`docs/UPSTREAM.md`／`docs/REFERENCES.md`／`docs/mac-mainline-absorption-analysis.md`／`quality_control_checklist.md`／`windows_cuda_qt_crash_postmortem.md`／`LICENSE` 逐檔改寫產品自稱為「聲成文 VoxProse」，並在提及作者/致謝之處補上 go-mask 這一層署名；描述「衍生自何處」「上游分支名」「歷史沿革」的既有事實敘述（`VoiceType4TW`／`voicetype4tw-mac`／`嘴炮輸入法`）保留原名不竄改。GitHub repo 已由維護者更名為 `SanHsien/voxprose`（原 `SanHsien/voicetype`），全 repo 文件內對應連結／clone 指令同步更新；本機工作目錄名稱維持 `voicetype` 不變（維護者尚未指示更名本機資料夾）。
- **`ui/settings_window.py` god file 拆分**（REVIEW.md #7）：原本 2164 行的單一設定視窗檔拆成 `ui/settings/` 子套件——七個分頁各一個 mixin 檔（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`）+ 共用元件與常數 `common.py`；`ui/settings_window.py` 收斂為 ~490 行薄殼，`SettingsWindow` 用多重繼承混入所有分頁 mixin，對外 `from ui.settings_window import SettingsWindow` 契約不變（`ui/app.py` 零 diff）。純機械搬移，無邏輯／UI 字串變動；唯一的例外是 `_run_self_check` 內用 `__file__` 反推 repo root 的路徑計算——檔案搬到更深一層目錄後補了一次 `os.path.dirname()`，否則會找錯 `self_check.py` 的路徑。`tests/test_stt_engine_dispatch.py` 的 `STT_ENGINES` 靜態原始碼解析目標同步從 `ui/settings_window.py` 改指向 `ui/settings/common.py`（常數搬去哪、測試就跟去哪，防護力不變）。
- **`requirements-win.txt`／`requirements-cuda-win.txt` 加主版本上限鎖定**（REVIEW.md #8）：每個套件宣告補上一個主版本上限（如 `PyQt6>=6.6.0,<7`），下限維持不變；基準版本取自 `tools/check_dependency_freshness.py` 查得的目前 PyPI 最新版（一般 semver 套件鎖「最新主版本 + 1」）。`pywin32` 無傳統 major.minor.patch 語意（單一遞增 build number，目前 312），改鎖 `<400` 作為寬鬆上限並加註說明；`certifi` 採日曆版本（YYYY.MM.DD），以年份鎖 `<2027`。`docs/DEVELOPMENT.md` 補一句依賴管理策略說明。

### Fixed

- **清理 pystray 技術債殘留**（REVIEW.md #23、24-2）：`ui/menu_bar.py:_get_sender_text` 移除兩處 pystray 時代死分支——一處與前一個 `if` 條件完全相同永遠不可達，一處用 `and False` 自我短路且註解自承 unused；`requirements-win.txt` 移除多餘的 `pystray>=0.19.5`（UI 已全面改用 `QSystemTrayIcon`）。全 repo grep `pystray` 確認零 import；`release_win.ps1` 與 `tools/check_dependency_freshness.py` 皆未引用 `pystray`，無需同步。
- **`ui/settings_window.py` 側欄 logo 重複宣告死碼**：`:229-235` 原本連續宣告兩次 `lbl_en = QLabel("VoxProse")`，第一次的物件從未加入 layout、純屬第一階段品牌改名時新增文字但未清掉的既有死碼。移除未使用的第一個宣告，保留實際加入 layout 的第二個。
- **UI 品牌殘留全面清掃**：`ui/menu_bar.py`（浮動選單/系統匣選單頂部標籤）、`ui/settings/dashboard_page.py`（Dashboard 中文標題）、`ui/settings_window.py`／`ui/settings/vocab_mem_page.py`／`ui/settings/soul_page.py`（三處 `QMessageBox` 標題）殘留的舊名「嘴炮輸入法」全數改為「聲成文」/「聲成文 VoxProse」；`ui/app.py` 一處歷史版本註解裡的雙關舊名字面量一併清掉。`vocab/manager.py` docstring 範例改用新品牌的同音示範（聲成文／生成文）。`啟動嘴炮輸入法.bat` `git mv` 更名為 `啟動聲成文.bat`，並同步更新 `release_win.ps1`／`docs/DEVELOPMENT.md` 的引用。詳見 `docs/DECISIONS.md` 2026-07-22 條目。
- **簡體字清掃**：`REVIEW.md`／`VERSIONS.md`／`docs/DECISIONS.md`（×2）／`tests/test_stt_engine_dispatch.py` 共 6 處簡體字打字疏漏修正為繁體。改用 Python 逐字元對照表掃描全 repo（非 grep 位元組比對），修正後零殘留。
- **移除原作者個人社群/贊助連結**：`ui/settings_window.py` 側欄的 SNS 按鈕區塊（YouTube／Facebook／Instagram／TikTok／Threads／個人網站六個連結）全數移除，作者署名文字保留不動；`ui/settings/common.py` 的 `SNSButton` 類別隨之刪除；孤兒圖示資產（6 個 SNS icon＋`donate-linepay.jpg`）`git rm`。`voicetype_installer.iss` 的 `MyAppURL`、`llm/openrouter.py` 的 `HTTP-Referer`/`X-Title` 改指向本 fork 而非上游或個人網址。詳見 `docs/DECISIONS.md`。
- **啟動/自檢日誌 `BUILD_ID` 與 `VERSION_NAME` 重複顯示**：實機驗證跑 `self_check.py`／`python main.py` 時發現 `VERSION_NAME`（本身已內含 `(BUILD-3200-STABLE)`）與 `BUILD_ID` 被 `main.py`（2 處）、`ui/app.py`（1 處）、`self_check.py`（1 處）疊加輸出，`debug.log` 出現 `V3.2.0 Windows Edition (BUILD-3200-STABLE) (BUILD-3200-STABLE)` 重複字樣。移除多餘的 `BUILD_ID` 疊加輸出（並清掉因此未使用的 import）；`self_check.py` 改為明確標註兩個常數各自的值，維持原本版本常數 `NameError` 迴歸驗證的用意。
- **設定視窗署名鏈框架錯誤且不完整**：`ui/settings_window.py:274` 側欄署名把原創作者（吉米丘、CC58TW）誤植為本 fork 的「主要開發者」，且漏列上游 Windows 專用版維護者 go-mask 與本 fork 維護者 SanHsien。改為完整四層（原創／上游 Win 版／本 fork／協助），比照 `NOTICE.md`／`README.md`／`about_window.py` 既有措辭；`about_window.py` 核實本來就俱全，未改動。
- **CUDA Dashboard 文案與實際加速行為矛盾**：`ui/settings/dashboard_page.py` 原本只用 `ctranslate2.get_cuda_device_count() > 0` 判斷「加速可用」，但這只反映驅動層級「有沒有裝置」，不代表 `stt/subprocess_whisper.py` 的 worker 實際載入 `cublas64_12.dll` 會成功——實機查證本機有 RTX 3060、`get_cuda_device_count()` 回報 1，但因未安裝 `requirements-cuda-win.txt` 導致 worker 靜默降級回 CPU，Dashboard 卻仍顯示「✅ 加速可用」。抽出 `stt/cuda_check.py:probe_cuda()` 供 Dashboard 與 worker 共用同一判定邏輯，文案改為三態（可用／偵測到 GPU 但缺函式庫／未偵測到 GPU）。
- **`tests/test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗**：`test_opens_explorer_to_highlight_zip_on_windows` 對 `subprocess.Popen` 的 mock 會一併攔截到 `platform.win32_ver()` 內部呼叫的 `subprocess.check_output("ver", ...)`，在部分 Python 建置（如 uv 安裝的 embeddable 3.11.15）上導致呼叫次數斷言失效。已用 `git stash` 在未改動的 HEAD 上重現，確認是既有缺陷、與本次改動無關。改為篩選 `call_args_list` 裡開頭是 `"explorer"` 的呼叫、斷言恰好一次，不再對總呼叫次數斷言。

## [3.1.0] - 2026-07-20

以 `win-stable` 分支 v3.0.1（`win-go-mask`，`BUILD-3010-STABLE`）為基底，建立 fork 的開發鷹架（比照 `SanHsien/sticker-forge`、`SanHsien/gpt-ai-assistant` 的既有範本）。發版工程收尾：新增 `docs/UPSTREAM.md` 上游追蹤、`release_win.ps1` `-NoModel` 打包選項、`.github/workflows/release.yml` 與 `dependency-freshness.yml` 兩條 CI workflow、`tools/check_dependency_freshness.py` 依賴新鮮度檢查工具，版本推進至 3.1.0（`BUILD-3100-STABLE`）。

### Added

- `LICENSE`：初版為雙軌授權聲明——上游程式碼誠實揭露「無正式授權、著作權屬吉米丘/CC58TW」；SanHsien 在本 fork 新增的原創部分採 MIT License（© 2026）。2026-07-20 隨上游正式補齊 MIT 授權後改寫為全 MIT，見下方 2026-07-20 條目。
- `CLAUDE.md`：Claude Code 專屬薄補丁，指回 `AGENTS.md` 為單一真相源。
- `CHANGELOG.md`（本檔）：Keep a Changelog 格式的精簡對外摘要。
- `pyproject.toml`：套件 metadata（`requires-python = ">=3.10,<3.13"`）與 `[tool.pytest.ini_options]`（`testpaths`/`pythonpath`），不取代 `requirements-win.txt`/`requirements-cuda-win.txt` 的實際安裝鏈。
- `tests/test_smoke.py`：全 repo `py_compile` + 純邏輯模組匯入驗證（optional 依賴模組匯入失敗即跳過）。
- `tests/test_config.py`：從歷史（`git show 51094bf:test_save.py`）移植並改寫的 `config.py` 讀寫回圈測試，改用 `tmp_path`/`monkeypatch` 隔離，不再觸碰開發者真實的 `%APPDATA%\VoiceType4TW\`。
- `tests/manual/manual_qkey_check.py`：從歷史（`git show 51094bf:test_qkey.py`）移植的手動腳本（需可顯示視窗環境，不被 pytest 收集）。
- `.gitattributes`：`* text=auto eol=lf`，但 `.bat`/`.cmd`/`.ps1` 強制 `eol=crlf`（避免 Windows batch 腳本因 LF 換行出現解析地雷）。
- `.github/workflows/ci.yml`：GitHub Actions，`windows-latest` + Python 3.12，安裝 `requirements-win.txt`（不含 CUDA、不下載模型）後跑全 repo `py_compile` + `pytest tests/`。
- `docs/DECISIONS.md` 追加本次鷹架落地的決策記錄。
- **麥克風裝置選擇＋增益＋AGC**（比照 Mac 主線 v2.9.7，`docs/mac-mainline-absorption-analysis.md` 項目 7-1/7-2/7-3）：`audio/recorder.py` 新增 `device`/`gain`/`gain_auto` 參數，`sd.InputStream` 指定輸入裝置（裝置消失時 fallback 回系統預設）；手動增益（50~300%）為實際 PCM 放大（非純視覺）；AGC 用獨立 `_agc_factor`（0.1~8.0×）依近期峰值動態調整、不覆蓋手動 gain。純數學抽成 `audio/gain.py`（無 sounddevice 依賴，可獨立單元測試）。`config.py` 新增 `mic_device`/`mic_gain`/`mic_gain_auto`（機器特定，列入 `LOCAL_KEYS`）。`ui/settings_window.py` 新增裝置下拉選單（含 2 秒插拔輪詢）+ 增益 slider + AGC 勾選框。新增 `tests/test_audio_gain.py`。⚠️ UI/錄音接線未在 Windows 實機驗證（本機無 PyQt6/sounddevice）。
- **錄音靜音預檢跳過 STT**（比照 Mac 主線 v2.9.7，項目 7-4）：`audio/recorder.py:stop()` 計算整段錄音峰值 RMS，低於門檻 0.3%（`audio.gain.SILENCE_THRESHOLD`）即設 `is_silent = True`；`ui/app.py:_on_audio_complete` 據此跳過整段 STT 呼叫，與既有幻覺過濾互補。僅涵蓋 PTT/toggle 路徑，VAD 全時模式不受影響。
- **Whisper 抗幻覺轉錄參數**（比照 Mac 主線 v2.9.13，項目 13-2）：faster-whisper 的 `transcribe()` 呼叫（`stt/subprocess_whisper.py`、`stt/local_whisper.py`）加入 `no_speech_threshold=0.6` + `condition_on_previous_text=False`，從幻覺源頭抑制。新增 `tests/test_stt_transcribe_params.py`。
- **OpenRouter fallback 鏈＋預設模型更新**（比照 Mac 主線 v2.9.16，項目 16-4）：`llm/openrouter.py` 新增 `OPENROUTER_FALLBACK_MODELS` 依序重試機制（`_is_missing_model_error()` 判斷 400/404 模型不存在類回應才觸發）；預設模型由具下架風險的 `google/gemini-2.0-flash-001` 改為 `google/gemini-2.5-flash`。新增 `tests/test_openrouter_fallback.py`。
- **LLM system prompt 集中化**（比照 Mac 主線 v2.9.13，項目 13-1）：新增 `llm/prompts.py`（`SYSTEM_PROMPTS` zh/en/ja + `get_default_system_prompt()`），7 個引擎的 `refine()` 統一改用 `prompt or get_default_system_prompt(self.language)` 防禦性 fallback，避免空 prompt 直接送進 API。清掉 4 個引擎檔重複的硬編中文 `self.prompt` 死屬性。`refine()` 簽章與既有 payload 差異（temperature、指令前綴）不變。新增 `tests/test_llm_prompts.py`。
- **LLM 未啟用時的輕量版靈魂規則**（比照 Mac 主線 v2.9.7，項目 7-5）：新增 `utils/soul_rules.py`（純函式 `extract_filler_words`/`strip_filler_words`/`apply_basic_soul_rules`），`ui/app.py:_apply_basic_soul_rules` 在 LLM 未啟用（且非 showcase/action/demo）時動態解析 soul md 的「贅詞清除規則」區段清除贅詞，不需呼叫任何 LLM API。新增 `tests/test_soul_rules.py`。
- `soul/scenario/default.md` 贅詞清單補「所以說」「就是說」（比照 Mac 主線 v2.9.7，項目 7-6）。
- **Windows 診斷包匯出**（比照 Mac 主線 v2.9.11 崩潰診斷管道，項目 11-3）：新增 `utils/diagnostics.py`，一鍵打包 Windows 環境資訊（`platform.win32_ver()` + ctypes `GlobalMemoryStatusEx` 總 RAM）、音訊裝置清單、debug.log/keystrike.log/main_crash.log 尾段、脫敏設定摘要到桌面 zip。設定頁新增「📦 匯出診斷包」按鈕。新增 `tests/test_diagnostics.py`（13 個測試，在真實 Windows 開發機上對環境收集函式直接驗證）。
- `docs/UPSTREAM.md`：記錄雙上游祖先鏈（`win-stable`／`win-go-mask-202607`／Mac 主線 `main`）的同步狀態與檢查上游更新標準流程，供 squash 後的單一 commit 保留正確 merge base。
- `release_win.ps1` 新增 `-NoModel` 打包選項：保留 CUDA 加速函式庫，但不隨附 medium 模型（首次啟動線上下載），資料夾／ZIP 命名 `VoiceType4TW_Win_Portable_NoModel_V$Build`。
- `.github/workflows/release.yml`：push tag `v*` 觸發並發佈 Release（`workflow_dispatch` 手動觸發僅產生 artifact），建置 Lite 與 NoModel 兩版可攜 ZIP 並附 sha256 校驗檔。
- `tools/check_dependency_freshness.py` ＋ `.github/workflows/dependency-freshness.yml`：解析 `requirements-win.txt`／`requirements-cuda-win.txt`，用 PyPI JSON API 比對最新版，每月 1 日排程檢查，落後時自動開/更新維護提醒 issue。

### Changed

- **上游同步（2026-07-20）**：合併上游 `win-go-mask-202607` 分支新增的 3 個 commit（三步驟快速安裝、README 全面改寫、7 張新截圖）。`README.md` 保留本 fork 骨架，頂部整合上游「🚀 快速安裝（三步驟）」（下載連結改指向本 fork）並吸收「辨識與 AI 設定」畫面導覽段與「安裝失敗排除」章節，未引入下載販售/YouTube/贊助連結。7 張截圖與 `VERSIONS.md` 採上游版；`paths.py`／`voicetype_installer.iss` 未受影響。
- **LICENSE 全面改版為全 MIT（2026-07-20）**：上游正式補齊 MIT 授權（`jfamily4tw/voicetype4tw-mac` main 分支 commit `46346d3`）後，本 fork 的雙軌授權聲明失去存在理由，改寫為單一 MIT 授權文件（上游 MIT 全文＋本 fork 新增部分 © 2026 SanHsien 同採 MIT 條款的附加聲明）。`NOTICE.md` 授權狀態節、`README.md`／`README.en.md` 授權敘述行同步更新，`docs/DECISIONS.md` 新增決策條目記錄沿革。
- **文件全面改寫，統一稱謂（2026-07-20）**：`安裝下載教學.MD` 更名為 `安裝下載教學.md`（副檔名小寫，內容已是最新，未需配合三步驟安裝更新）；全 repo `.md` 檔逐檔檢討，移除舊有的擬人化維護者稱呼與 AI 助理自稱，統一改用中性用語（「維護者」、「Claude Code」或改寫句子），僅涉及稱謂與語氣、不動技術內容與決策語義。受影響檔案：`REVIEW.md`（Reviewer 欄與結論段落）、`docs/DECISIONS.md`、`docs/mac-mainline-absorption-analysis.md`。
- `README.md` / `README.en.md`：改寫為 Windows 專注版說明（fork 定位、安裝方式、設定欄位對照現行 `config.py`）。
- `AGENTS.md`：全面改寫——舊版內容是照「Mac 純化版 main」寫的（提及 `mlx_whisper.py`、`requirements.txt` 的 `pyobjc-*`、`pynput`、`.aicore` submodule、`openspec/`、`HANDOVER.md`/`AI_MEMORY.md` 等現已不存在的檔案/依賴），實際瀏覽現行 Windows-only 程式碼樹後重寫架構速覽、模組職責表、開發約定與硬性邊界。
- `SKILL.md`：同步更新為 Windows 版現況（怎麼跑、怎麼驗、快速定位路徑）。
- `docs/DEVELOPMENT.md`：修正大量與實際工作樹不符的殘留描述（MLX、`pynput`、`requirements.txt` 的 macOS 依賴段落、macOS 打包鏈仍需維護的說法），改為準確反映目前 Windows-only 工作樹的內容；新增「測試」章節（pytest 使用方式 + 舊測試腳本逐一處置紀錄）與目錄結構更新。
- `.gitignore`：追加 `.pytest_cache/`（新增 pytest 使用後的暫存目錄）。
- `vocab/manager.py`：本機常數 `VOCAB_DIR` 改名為 `_VOCAB_DATA_DIR`，避免與先前已移除、曾指向雲端同步目錄的死碼常數 `VOCAB_DIR`（`paths.py`）撞名混淆（REVIEW 提醒事項）。純改名不改行為。

### Fixed

- **API Key 不再進雲端同步資料夾**（`config.py`）：所有 `*_api_key` 欄位加入 `LOCAL_KEYS` 白名單，只存本機 `config_local.json`；`load_config()` 新增一次性遷移，偵測到既有使用者的 `config_global.json`（可能位於 iCloud/Google Drive/NAS 同步目錄）殘留金鑰時自動搬進本機並從全域檔移除，無感升級。設定視窗同步頁的警語文字同步修正。新增 `tests/test_config.py` 遷移與不洩漏測試。
- 網路逾時補齊：`llm/claude.py`（anthropic SDK）與 `stt/groq_whisper.py`（groq SDK）此前未設定 timeout，落回 SDK 預設 600 秒；補上統一常數 `net_config.CLOUD_REQUEST_TIMEOUT_SECONDS`（60s）。其餘 httpx/requests 呼叫點原本已各自帶合理 timeout，維持不動。新增 `tests/test_provider_timeouts.py`。
- PTT 與 VAD 全時模式互斥（`audio/mutex.py` + `ui/app.py`）：兩模式同時啟用時不再可能疊加兩路錄音——PTT 優先，按下 PTT 會捨棄進行中的 VAD 段落；PTT 錄音中的 VAD 觸發被忽略且對應音訊丟棄。新增 `tests/test_recording_mutex.py`。
- **智慧詞彙學習對本地辨識無效**（`stt/subprocess_whisper.py`）：子行程 worker 過去從未讀取 IPC 訊息的 `"prompt"` 欄位，永遠用硬編預設字串當 `initial_prompt`，詞彙庫學到的專有名詞從未真正餵進本地 Whisper。worker 迴圈改讀 `"prompt"` 欄位並轉交 `_run_transcribe()`（空/缺 fallback 回預設字串），比照 Mac 版語義（`build_vocab_prompt()` 結果取代而非串接預設 prompt）。`stt/local_whisper.py` 本來就正確接線，無需修改。新增 4 個回歸測試於 `tests/test_stt_transcribe_params.py`。
- 計算機移除 `eval()`（`actions/builtins.py`）：改用 `ast` 白名單解析（數字、`+ - * / ** % //`、括號、正負號），名稱/呼叫/屬性存取等節點一律拒絕，並限制次方指數上限；輸出格式不變，另支援 `^` 次方。新增 `tests/test_calculator.py`。
- `diagnose_mic.py` 從 macOS 空殼（Windows 上只印「Not macOS」）重寫為 Windows 實用診斷：列出輸入裝置與預設裝置、以 `audio/recorder.py` 同參數實測 0.5 秒音量、無 sounddevice 時給明確安裝指引。
- `ui/settings_window.py` 靈魂編輯區硬編碼 macOS 字型 `Monaco` 改為 Windows 內建等寬字型 `Consolas`。
- `llm/claude.py` 欄位名不一致：引擎讀 `claude_api_key`/`claude_model`，但 `DEFAULT_CONFIG` 與設定 UI 存的是 `anthropic_api_key`/`anthropic_model`——Claude 引擎因此永遠拿到空 key，`refine()` 靜默回傳原文、從未真的呼叫過 API。改以 config/UI 既有欄位名為準。已 grep 全部 LLM/STT provider 確認僅此一處同型問題，並新增 `tests/test_llm_config_keys.py`（AST 靜態掃描每個 provider 讀的 config 欄位名必須存在於 `DEFAULT_CONFIG`）防回歸。
- `AGENTS.md`/`SKILL.md` 過去宣稱「Claude Code 專屬補充見 `CLAUDE.md`」但該檔案不存在——現已補上。
- `voicetype_installer.iss`：移除引用不存在的 `platform_layer\*` 的 `Source:` 條目——Inno Setup 對缺失來源預設編譯失敗，此前打包鏈實際上是斷的；已寫檢查腳本核對其餘 12 條 `Source:` 引用全數存在。
- `stt/__init__.py`／`stt/gemini_stt.py`：STT 引擎下拉選單的「Gemini (雲端 API)」選項此前選了會靜默 fallback 成本地 Whisper（`get_stt()` 沒有對應分支）；補上分派分支，並修正 `GeminiSTT.transcribe()` 本身兩個會讓它「接上了也還是壞的」的簽章不符與 WAV bytes 重複編碼問題。新增 `tests/test_stt_engine_dispatch.py`／`tests/test_gemini_stt.py`。
- STT 幻覺過濾：win-stable 相對舊版 Mac 主線（`main`, `51094bf`）完全沒有 Whisper 常見幻覺句（「請訂閱」「感謝觀看」等 YouTube 結尾片語、長尾重複）的過濾，是功能倒退。移植出平台無關的 `stt/hallucination_filter.py`，接進 `ui/app.py:_process_audio` 的統一 STT 結果處理路徑，對本地與雲端引擎都生效。新增 `tests/test_stt_hallucination_filter.py`。
- `paths.py`：移除從未被實際使用、容易誤導的死碼常數 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`（宣告指向雲端同步目錄，但 `vocab/manager.py`/`memory/manager.py`/`stats/tracker.py` 實際上只寫本機 `APP_DATA_DIR`，兩者從未接線）。
- `stt/openrouter_stt.py`：修正與修復前 `GeminiSTT` 同型的兩個 bug——函式簽章與呼叫端 `ui/app.py` 不符（TypeError）、以及把完整 WAV bytes 用 `soundfile` 當裸 PCM 重新編碼（必定 `IndexError` 被吞掉，引擎永遠回傳空字串）。改為直接上傳原始 WAV bytes，簽章對齊 `BaseSTT`。新增 `tests/test_openrouter_stt.py`。
- STT 語言 hint 被翻譯目標語言污染：`ui/app.py:_process_audio` 此前把 `translation_lang` 直接餵給 `self.stt.transcribe(language=lang)`，使用者用過一次「翻譯成英文」後，之後所有中文錄音的 STT 語言 hint 都被污染成 `en`。比照 Mac 主線 v2.9.16（`51094bf:stt/language.py`）移植 `stt/language.py:get_transcription_language()`，STT 語言改回讀使用者實際設定的 `config["language"]`，翻譯只影響 LLM 輸出層，不干擾辨識。新增 `tests/test_stt_language_selection.py`。
- `ui/settings_window.py:_run_mic_test`：麥克風測試按鈕內有一段「非 macOS 一律拒絕」的假擋板（`if platform.system() != "Darwin": 彈窗「此診斷功能目前專為 macOS 設計」`），但擋板之後的實際測試邏輯（`sd.rec()` + numpy RMS）本來就是跨平台程式碼、錯誤訊息本來就是寫給 Windows 隱私權設定看的，擋板本身是誤植死碼——導致 Windows 使用者連按鈕都被藏起來，完全用不到一個其實能動的功能。已移除擋板並取消 Windows 隱藏。
- `paths.py`：移除從未被實際使用的死碼常數 `AI_PERMANENT_MEMORY_PATH`（指向雲端同步目錄，與先前已清掉的 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR` 同一批，之前因不在指定範圍暫留）。

[Unreleased]: https://github.com/SanHsien/voxprose/compare/v3.2.0...HEAD
[3.2.0]: https://github.com/SanHsien/voxprose/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/SanHsien/voxprose/compare/b694e40...v3.1.0
