# Changelog

本檔案採用 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，是對外快速掃描用的精簡摘要，記錄從本 fork（SanHsien）建立開發鷹架起的變更。

本檔案自 2026-07-24 起單一記錄全部版本歷史（維護者同日授權，原逐版詳細紀錄
`VERSIONS.md` 已併入本檔：fork 後版本併入對應版本區塊，pre-fork 上游繼承版本
精簡為底部「上游繼承版本史」一節）。版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

> **關於歷史 commit hash**：v3.1.0 發版時已把 fork 開發歷史 squash 成單一 commit（`84d1b28`，見 `docs/UPSTREAM.md`）。本檔與 `docs/DECISIONS.md`、`REVIEW.md` 引用的更早 hash 屬 squash 前紀錄，已不存在於 git 歷史，僅作文件內識別碼保留。

## [Unreleased]

- 依賴新鮮度檢查加上「已核准暫緩」機制：`.github/dependency-deferrals.json` 讓判斷過、暫時不升的套件停止每月復發，但暫緩綁定當初判斷的版本，上游一發新版就自動失效並重新提醒。首筆是 `anthropic`（1.x 移除 `messages.create` 的 `temperature`，理由見 `docs/DECISIONS.md`）。

- 依賴：`openai` 上限自 `<3` 開到 `<4`，實裝解析為 3.6.0（`chat.completions.create` 用到的 `model`／`messages`／`max_tokens`／`temperature`／`timeout` 五個參數在 3.6.0 全數仍在，經 SDK 內省確認；481 條測試全過）。`anthropic` 維持 `<1`：1.x 移除了 `messages.create` 的 `temperature`，而 `llm/claude.py` 的潤飾功能依賴 `temperature=0.1`，照升會 `TypeError`；理由與重評條件見 `docs/DECISIONS.md`。

### Added

- **依賴與安全自動維護**：新增 Dependabot 每週 Python／GitHub Actions 更新、CodeQL `security-extended` 每週掃描；GitHub repo 啟用 Issues、vulnerability alerts 與 Dependabot security updates。Windows／CUDA／Release 相關更新一律人工審查，不自動合併。

### Changed

- **README 公開入口**：中英文 README 對齊專案首頁結構，新增 Release／CI／Windows Release／MIT／Python／Windows／local-first／pytest 徽章、雙向語言連結、正式版下載指引、專案結構、文件索引、來源致謝與授權分節。
- **依賴新鮮度追蹤**：checker 改為只比較 repo 宣告與 PyPI，不再受執行機器已安裝套件影響；workflow 會彙整 open Dependabot PR、避免舊 SHA 覆寫、重開／更新／自動關閉同一個維護 issue。
- **上游 main 審視**：`4269178`（Apple Local prompt leak hotfix）只涉及 Apple Foundation Models、Swift helper 與 macOS 打包／版本資料，本 Windows-only fork 無對應模組，記入 `docs/UPSTREAM.md` Skipped 並推進 `last_reviewed`，不移植程式碼。

### Fixed

- **排程提醒無法建立 issue**：GitHub Issues 原先關閉，2026-07-27 上游更新檢查找到新 commit 後因此失敗；現已啟用 Issues，恢復依賴與上游兩條提醒 workflow 的寫入目標。

## [3.4.4] - 2026-07-26

### Changed

- **文件整理**：`docs/BRANDING.md` 併入 `docs/DECISIONS.md`、`quality_control_checklist.md` 併入（原）`docs/RELEASE_VERIFICATION.md` 附錄（現已隨該檔一併併入 `docs/DEVELOPMENT.md`，見下方文件整理第三批），兩份孤兒文件刪除，關鍵事實無遺失。
- **文件整理（第二批之一）**：`docs/mac-mainline-absorption-analysis.md` 的「建議不吸收清單」（含前瞻價值的 8-1／13-4／10-1／7-7 等項）精簡後併入 `docs/UPSTREAM.md` 新增小節「Mac 主線分析：評估後不吸收」；9 個檔案的程式碼註解/docstring 出處引用簡化為版本號（如「Mac 主線 v2.9.7」），移除檔名路徑與項目編號；分析檔刪除。
- **文件整理（第二批之二）**：根目錄 `windows_cuda_qt_crash_postmortem.md`（PyQt6/CUDA 崩潰 postmortem）併入 `docs/DEVELOPMENT.md`「Windows 已知地雷」章節，`AGENTS.md`/`CLAUDE.md`/`SKILL.md`/`docs/REFERENCES.md`/`tests/manual/manual_qkey_check.py` 的引用同步改指向；原檔刪除。
- **文件整理（第二批之三）**：`docs/RELEASE_VERIFICATION.md`（含前批併入的 QC checklist 附錄）併入 `docs/DEVELOPMENT.md`「Windows Release 實機驗證」章節，README/README.en 連結目標改指 `docs/DEVELOPMENT.md`（敘述文字不動），REVIEW/docs/DECISIONS 引用同步更新；原檔刪除。
- **文件整理（第二批之四，最終批）**：`VERSIONS.md` 併入 `CHANGELOG.md`：fork 後版本（v3.1.0+）獨有的驗證證據補進對應版本區塊，pre-fork 上游繼承版本史（v2.7.24–win-go-mask v3.0.1）精簡為底部新增一節；`AGENTS.md`「CHANGELOG／VERSIONS 兩者並存」制度決定改為單一 CHANGELOG（維護者 2026-07-24 授權），`CLAUDE.md`/`SKILL.md`/`docs/DECISIONS.md`/`docs/DEVELOPMENT.md`/`tests/test_brand_and_charset_guard.py` 的引用同步更新；原檔刪除。

### Added

- **真人 VAD 對照驗證器**：新增 `tests/manual/manual_audio_vad_check.py`，讓正常說話、咳嗽、呼吸與環境雜音各只錄一次，再以同一份 PCM 公平比較 RMS／真 Silero，輸出不含原始音訊的 JSON／Markdown 證據；指定 release root 時會反查實際 module 來源，避免誤用 checkout 產生假 PASS。

### Fixed

- **CI action runtime**：四個 workflow 升級至 Node 24 世代的 `checkout/setup-python/upload-artifact v7` 與 `action-gh-release v3`，移除 GitHub runner 的 Node 20 淘汰警告。
- **前景程式倒數不再凍結 UI**：「偵測目前前景程式」改用 `QTimer` 非阻塞倒數，使用者可在 3 秒內正常切換視窗，並在關閉倒數視窗前先抓取 process。
- **前景倒數不再搶回焦點**：真機覆核發現非阻塞 `QProgressDialog` 仍會在更新時把設定視窗拉回前景，導致最終偵測到 `python.exe`；改成原按鈕文字倒數，不再建立 modal 頂層視窗。新增真 Windows callback 驗證器。
- **系統匣選單動作與清理**：修正 QAction 迴圈晚綁定造成 callback 收到錯誤動作，並改用正確的 `QSystemTrayIcon` hide/deleteLater 關閉流程。
- **設定儲存假成功**：基底靈魂檔無法寫入時不再靜默忽略；現在會中止儲存並顯示實際錯誤。
- **麥克風測試不再凍結 UI**：設定頁的三秒錄音倒數改用 `QTimer`，錄音期間仍可更新畫面並正常回應 Windows 視窗事件。
- **bare-except 防回歸**：收窄主程式最後一個 bare `except:`，並新增全 repo AST guard。

## [3.4.3] - 2026-07-23

### Fixed

- **Windows 系統匣實際啟動**：修正 `VoiceTypeApp.run()` 只進入 Qt event loop、卻從未呼叫 `TrayManager.start()`，導致系統匣圖示與「聲成文」選單不會建立；現在先啟動 tray，再啟動全域熱鍵監聽。
- **主選單與設定視窗喚回**：品牌列「聲成文 VoxProse」現在會開啟設定；設定／About 從 tray callback 顯示時延後到 menu 關閉後再取回前景，About 改為非 modal，避免互相阻塞。
- **About 視窗版面**：由固定 320×430 改為可縮放 680×720＋捲動內容，移除重複文案並把完整上游／fork／協作署名整理成卡片，不再裁字或互相覆蓋。
- **VoxProse 品牌圖示**：換成透明背景的語音泡泡＋麥克風＋波形標誌，同步更新主 PNG、tray PNG 與 Windows 多尺寸 ICO。
- **實機驗證**：新增 `tests/test_app_startup.py` 鎖定 tray/hotkey/event loop 呼叫順序（423 passed, 10 skipped）；Windows 內嵌 runtime 實測 log 出現 `QSystemTrayIcon shown successfully`。正式 Release 重新下載 Lite（238,977,563 bytes，SHA-256 `d7b7616b…`）與 NoModel（1,609,366,776 bytes，SHA-256 `953bf9a8…`），CRC／UTF-8 中文資源驗證通過。

## [3.4.2] - 2026-07-23

### Added

- **驗證暫存清理手冊**：（原）`docs/RELEASE_VERIFICATION.md`（現併入 `docs/DEVELOPMENT.md`）新增安全清理方式，刪除前必須確認完整路徑位於 `%TEMP%`；另記錄受控自動化環境攔截 `Remove-Item -Recurse` 時的 .NET fallback。

### Fixed

- **STT 啟動 readiness 誤報**：Windows subprocess `warmup()` 過去只送出 IPC 就返回，UI 因而在模型尚未載入／warmup 前誤報 ready。現改為等待帶成功狀態的 `warmup_done`；worker error、程序死亡與 pipe 中斷均撤銷 ready。首次大型模型下載不設絕對 timeout，避免慢網路超時後永久卡住。新增 8 項回歸測試＋`tests/manual/manual_stt_warmup_check.py`（Windows 真 worker tiny CPU int8 驗證只在 ready＋warmup complete 後返回）。

## [3.4.1] - 2026-07-23

### Fixed

- **Windows Release ZIP 中文檔名損毀**：v3.4.0 的 release workflow 使用 Windows `tar.exe -a` 建 ZIP；英文 runner 的 ANSI code page 無法表示中文，導致 7 個檔名在壓縮當下被替換成 literal `?`，Windows `Expand-Archive` 因非法檔名直接失敗。改用 .NET `ZipArchive` 明確寫 UTF-8 entry name，新增 `tools/verify_release_zip.py` 與 CI 上傳前 gate，檢查 CRC、重複／損壞檔名、UTF-8 flag 及 7 個必要中文資源。驗證方法見 `docs/DEVELOPMENT.md`「Windows Release 實機驗證」。
- **Patch 版產物名稱**：可攜包檔名改採完整 semver，v3.4.1 產物不再沿用容易與 v3.4.0 混淆的 `v3.4` 名稱。

## [3.4.0] - 2026-07-23

兩個新功能（Silero VAD、前景視窗自動情境切換，皆預設不改變現行行為、待實機驗證）＋隱私與加固審查（log 輪替、broad except 清查、權限檢查實質化）＋正式支援 Python 3.13/3.14＋keystrike 死碼清除。

### Added

- **`utils/log_rotation.py`**：`debug.log`／`worker_debug.log` 改用 `RotatingFileHandler`（5MB×2 備份），修正原本無上限附加寫入會無限增長的問題。新增 `tests/test_log_rotation.py`。
- **`utils/permissions.py` 麥克風權限真實檢查**：`check_microphone()` 改讀 Windows 隱私權登錄檔，`ensure_all_permissions()` 補上啟動時的實際呼叫（過去 import 了卻從未被呼叫，是死碼）。新增 `tests/test_permissions.py`。
- **CI Python 版本矩陣**：`.github/workflows/ci.yml` 改測 3.10/3.11/3.12（比照 `pyproject.toml` 宣告範圍），過去只測 3.12。新增 `tests/test_ci_workflow.py`。
- **Silero VAD 全時模式引擎（選用）**：新增 `audio/vad/`（`BaseVAD` 介面＋`RmsVAD`/`SileroVAD`），設定新增 `vad_engine`（`rms`預設／`silero`），onnxruntime 缺席或模型下載失敗優雅降級回 RMS；設定頁新增偵測引擎下拉。🔍 待實機驗證，見 `REVIEW.md` 27-1。
- **前景視窗自動情境切換（選用，`docs/REFERENCES.md` Wispr Flow 調研條目落地）**：新增 `utils/foreground.py`（純 ctypes Win32，取得目前前景視窗程序執行檔名稱，非 Windows/失敗回 `None`），設定新增 `auto_scenario_enabled`（預設 `False`）／`auto_scenario_rules`（程式檔名→情境模板，預設空）；`ui/app.py` 於錄音開始那一刻（PTT/Toggle/VAD 段落開始）偵測一次前景程式，命中規則時該次辨識套用對應情境，不覆寫使用者手動選定的 `active_scenario`。靈魂設定頁新增對應 UI 區塊（啟用勾選框、規則清單、偵測前景程式按鈕）。🔍 待實機驗證，見 `REVIEW.md` 27-2。

### Changed

- **正式支援 Python 3.13/3.14**：`pyproject.toml` 的 `requires-python` 由 `>=3.10,<3.13` 放寬為 `>=3.10,<3.15`；CI matrix 同步擴充為 3.10–3.14（PyPI 實查 `PyQt6`/`faster-whisper`/`ctranslate2`/`sounddevice`/`opencc-python-reimplemented` 等關鍵依賴在 Windows 上皆有 3.13/3.14 wheel）；`setup_win.bat` 的 py-launcher 偵測鏈擴充為 `3.14→3.13→3.12→3.11→3.10`。可攜包內嵌式 Python（`tools/get_portable_python.ps1`）維持 3.12 不動。本機系統 Python 3.14.6 實跑 `pytest` 全綠（326 passed, 11 skipped）作為相容性證據。詳見 `docs/DECISIONS.md`。

### Fixed

- **broad except 靜默吞噬清查**：全 repo 掃描後修正 43 處會隱藏真實錯誤的 `except`（補 log 或收窄型別），涵蓋設定檔/記憶/統計損毀時完全靜默、LLM prompt 注入失敗無痕跡等與歷史「引擎自始壞掉」同類的風險點；不改變任何 fallback 行為語義。詳見 `docs/DECISIONS.md`。新增 `tests/test_broad_except_logging.py`。

### Removed

- **keystrike 死碼清除**：移除 `paths.KEYSTRIKE_LOG_PATH`／`touch()` 佔位、`config.py` 的 `separate_keystrike_log` 死開關、`main.py` 啟動記錄、`ui/settings/general_page.py` 的勾選框與「檢視熱鍵紀錄」按鈕、`utils/diagnostics.py` 的 `keystrike.log` 收集項。推翻 `REVIEW.md` 26-4 原「決定不做」判定（維護者 2026-07-23 明示指示清除），詳見 `docs/DECISIONS.md`。

### Investigated (no change)

- **keystrike.log 隱私審查**：確認 `hotkey/listener.py` 只監控使用者自訂的三個熱鍵 VK 碼、且目前無任何 handler 實際寫入 `keystrike.log`（檔案永遠是空的 touch 占位），診斷包因此不會打包到任何按鍵資料；`separate_keystrike_log` 設定開關本身也是死碼（見 `docs/DECISIONS.md`）。無隱私疑慮，未修改行為。
- **`utils/permissions.py` Windows 化**：確認早於 `b4094b7`（v2.9.6）已移除全部 macOS 專屬邏輯；本輪只補強麥克風檢查的實質功能（見上方 Added），未發現需要移除的殘留。

## [3.3.0] - 2026-07-22

上游 `jfamily4tw/voicetype4tw-mac` `main` 分支新 commit `805b007`（v2.9.18）審視完成：Apple Foundation Models 整套 macOS 專屬功能不適用（詳見 `docs/UPSTREAM.md` Skipped 表），吸收其中 3 項平台無關修正，詳見 `docs/DECISIONS.md` 2026-07-22 條目。**本輪新增驗證**：裝 `requirements-cuda-win.txt` 後 CUDA 加速確實生效（GPU 0.55s vs CPU 8.57s，約 15.6 倍），`release_win.ps1 -Lite` 端到端建置與啟動實測成功。

### Added

- **STT 後簡體→繁體轉換**：新增 `utils/zh_convert.py`，用 OpenCC `s2t` 修正 Whisper 偶爾把中文誤判成簡體輸出的問題（概念吸收自上游 `805b007` 的 `llm/apple_local.py:_to_traditional()`，獨立成不依賴 macOS 的通用後處理步驟）。新設定開關 `zh_convert_enabled`（預設 `True`）、新依賴 `opencc-python-reimplemented`，未安裝時優雅降級。新增 `tests/test_zh_convert.py`。

### Fixed

- **`vocab/manager.py` 模糊比對誤改短 ASCII 縮寫**：4 字以下純 ASCII 縮寫（STT/PTT/API）不再做模糊修正，移植自上游 `805b007` 的守衛條件。新增 `tests/test_vocab_manager.py`。

### Changed

- **`vocab/manager.py:load_all_learned_words()` 排序穩定化**：排序 key 改為 `(-count, word.casefold(), word)`，次數相同時不再依賴 dict 插入順序。移植自上游 `805b007`。

## [3.2.0] - 2026-07-22

品牌改名：中文品牌「聲成文」／英文品牌「VoxProse」，標語「自然開口，清楚成文。」同時補齊過去遺漏的署名鏈：原創作者吉米丘（Jimmy）／CC58TW → 上游 Windows 專用版維護 go-mask → 本 fork（Windows）維護 SanHsien。

**實機驗證（2026-07-21～22）**：本版是本 fork 第一次在真實 Windows 桌面環境完整跑過整條鏈路——乾淨 venv 安裝、`self_check.py` 子行程實際辨識、`diagnose_mic.py` 列出 19 個真實裝置、Windows SAPI 合成語音經真實 Whisper 引擎正確辨識出中文文字、`python main.py` 兩次啟動皆無崩潰、SettingsWindow 七分頁全數通過。過程中發現並修復 4 個真實 bug（見下方 Fixed）。

### Added

- **上游更新自動檢查**：`tools/check_upstream_updates.py` ＋ `.github/workflows/upstream-check.yml`，每週檢查上游三個追蹤分支是否有新 commit，透過 `docs/UPSTREAM.md` 的同步狀態標記區塊（JSON）記錄 `last_reviewed`/`last_merged`，有更新時開/更新 issue。新增 `tests/test_upstream_check.py`（18 個測試）。
- `docs/BRANDING.md`：記錄品牌規格與資料路徑遷移規劃。
- **`tests/test_brand_and_charset_guard.py`**：三個守門測試，防止舊品牌名稱／簡體字／原作者個人網址回流。
- **`stt/cuda_check.py`**：新增 `probe_cuda()` 共用 CUDA 加速判定函式，供 Dashboard 與 STT worker 共用同一真相源。新增 `tests/test_cuda_check.py`。

### Changed

- **資料路徑正名**：`%APPDATA%\VoiceType4TW` → `%APPDATA%\VoxProse`、`Documents\VoiceType4TW_Sync` → `Documents\VoxProse_Sync`。維護者確認本機從未有真實使用資料，不寫任何遷移/備份/fallback 邏輯，直接改常數與字面量；打包鏈與診斷 log 全部落點同步更新，實機驗證確認新路徑生效。
- **`voicetype_installer.iss` 補齊安裝版品牌**：`MyAppName`（→`VoxProse`）與 `AppId`（換發新 GUID）一併改名，等同視為新程式（本專案無既有安裝基礎，可接受）。
- **`AGENTS.md`／`SKILL.md` 雙軌授權敘述過時修正**：改為指向現況（全 MIT）。
- **視窗標題／系統匣／About 視窗／桌面捷徑品牌字串**：全面改為「聲成文」／「VoxProse」，署名鏈同步更新。
- **Windows AppUserModelID**：改為 `tw.sanhsien.VoxProse.windows`。
- **Release ZIP／安裝檔命名改用新品牌**：版本號改自 `pyproject.toml` 動態解析，不寫死。
- **版本推進 3.2.0**：`paths.py`／`pyproject.toml`／`voicetype_installer.iss` 版本號同步。
- **`main.py` 路徑重複定義消除**（純重構）：改為直接引用 `paths.APP_DATA_DIR`，實際路徑值不變。
- **全 repo 文件品牌改寫與署名補正**：`README.md` 等全部文件逐檔改寫產品自稱為「聲成文 VoxProse」，描述歷史沿革的既有事實敘述保留原名不竄改。GitHub repo 同步更名為 `SanHsien/voxprose`。
- **`ui/settings_window.py` god file 拆分**（REVIEW.md #7）：拆成 `ui/settings/` 子套件，七個分頁各一個 mixin 檔，對外契約不變。
- **`requirements-win.txt`／`requirements-cuda-win.txt` 加主版本上限鎖定**（REVIEW.md #8）。

### Fixed

- **清理 pystray 技術債殘留**（REVIEW.md #23、24-2）：`ui/menu_bar.py` 死分支與 `requirements-win.txt` 多餘依賴移除。
- **`ui/settings_window.py` 側欄 logo 重複宣告死碼**：移除未使用的重複宣告。
- **UI 品牌殘留全面清掃**：舊名「嘴炮輸入法」全數改為新品牌，`啟動嘴炮輸入法.bat` 更名為 `啟動聲成文.bat`。
- **簡體字清掃**：6 處打字疏漏修正為繁體。
- **移除原作者個人社群/贊助連結**：SNS 按鈕區塊與孤兒圖示資產移除，署名文字保留不動。
- **啟動/自檢日誌 `BUILD_ID`／`VERSION_NAME` 重複顯示**：移除多餘疊加輸出。
- **設定視窗署名鏈框架錯誤且不完整**：改為完整四層署名。
- **CUDA Dashboard 文案與實際加速行為矛盾**：抽出 `stt/cuda_check.py:probe_cuda()` 共用判定邏輯，文案改為三態。
- **`tests/test_diagnostics.py` 一個斷言在特定 Python 建置上必然失敗**：改為篩選特定呼叫，不再對總呼叫次數斷言。

## [3.1.0] - 2026-07-20

以 `win-stable` 分支 v3.0.1 為基底，建立 fork 的開發鷹架。發版工程收尾：新增 `docs/UPSTREAM.md` 上游追蹤、`release_win.ps1` `-NoModel` 打包選項、`.github/workflows/release.yml` 與 `dependency-freshness.yml` 兩條 CI workflow、`tools/check_dependency_freshness.py`，版本推進至 3.1.0。

### Added

- `LICENSE`：初版雙軌授權（上游無正式授權／SanHsien 新增部分 MIT），2026-07-20 上游補齊 MIT 後改寫為全 MIT。
- `CLAUDE.md`、`CHANGELOG.md`（本檔）、`pyproject.toml`：開發鷹架基礎文件。
- `tests/test_smoke.py`、`tests/test_config.py`：全 repo `py_compile` + 設定讀寫回圈測試。
- `.gitattributes`／`.github/workflows/ci.yml`：CRLF 規則、CI 跑 `py_compile` + `pytest`。
- **麥克風裝置選擇＋增益＋AGC**（比照 Mac 主線 v2.9.7）：`audio/recorder.py` 新增 device/gain/AGC 參數，純數學抽成 `audio/gain.py`。新增 `tests/test_audio_gain.py`。
- **錄音靜音預檢跳過 STT**（比照 Mac 主線 v2.9.7）：峰值 RMS 低於門檻即跳過整段 STT 呼叫。
- **Whisper 抗幻覺轉錄參數**（比照 Mac 主線 v2.9.13）：加入 `no_speech_threshold=0.6` + `condition_on_previous_text=False`。
- **OpenRouter fallback 鏈＋預設模型更新**（比照 Mac 主線 v2.9.16）。
- **LLM system prompt 集中化**（比照 Mac 主線 v2.9.13）：新增 `llm/prompts.py`。
- **LLM 未啟用時的輕量版靈魂規則**（比照 Mac 主線 v2.9.7）：新增 `utils/soul_rules.py`。
- **Windows 診斷包匯出**（比照 Mac 主線 v2.9.11）：新增 `utils/diagnostics.py`，一鍵打包環境資訊到桌面 zip。
- `docs/UPSTREAM.md`：記錄雙上游祖先鏈的同步狀態與檢查流程。
- `release_win.ps1` 新增 `-NoModel` 打包選項；`.github/workflows/release.yml`（Lite/NoModel 兩版）；`tools/check_dependency_freshness.py` 依賴新鮮度檢查。

### Changed

- **上游同步（2026-07-20）**：合併 `win-go-mask-202607` 分支 3 個 commit（三步驟安裝、README 改寫、7 張截圖）。
- **LICENSE 全面改版為全 MIT**：上游補齊 MIT 授權後改寫為單一授權文件。
- **文件全面改寫，統一稱謂**：移除擬人化維護者稱呼，改用中性用語。
- `README.md`／`README.en.md`／`AGENTS.md`／`SKILL.md`／`docs/DEVELOPMENT.md`：改寫為反映現行 Windows-only 工作樹的內容。
- `vocab/manager.py`：本機常數 `VOCAB_DIR` 改名為 `_VOCAB_DATA_DIR`，避免撞名混淆。

### Fixed

- **API Key 不再進雲端同步資料夾**：`*_api_key` 欄位加入 `LOCAL_KEYS`，並做一次性遷移。
- 網路逾時補齊：`llm/claude.py`／`stt/groq_whisper.py` 補上統一常數逾時。
- PTT 與 VAD 全時模式互斥：新增 `audio/mutex.py`，PTT 優先。
- **智慧詞彙學習對本地辨識無效**：worker 改讀 IPC `"prompt"` 欄位。
- 計算機移除 `eval()`：改用 `ast` 白名單解析。
- `diagnose_mic.py` 從 macOS 空殼重寫為 Windows 實用診斷。
- `ui/settings_window.py` 靈魂編輯區字型改 `Consolas`。
- `llm/claude.py` 欄位名不一致：改以 config/UI 既有欄位名為準，新增 AST 靜態掃描防回歸。
- `voicetype_installer.iss`：移除引用不存在的 `platform_layer\*`。
- `stt/__init__.py`／`stt/gemini_stt.py`：補上 Gemini 分派分支，並修正簽章與 WAV 重複編碼問題。
- STT 幻覺過濾：移植平台無關的 `stt/hallucination_filter.py`，接進統一 STT 結果處理路徑。
- `paths.py`：移除死碼常數 `VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`/`AI_PERMANENT_MEMORY_PATH`。
- `stt/openrouter_stt.py`：修正與 `GeminiSTT` 同型的簽章與 WAV 重複編碼 bug。
- STT 語言 hint 被翻譯目標語言污染：移植 `stt/language.py:get_transcription_language()`。
- `ui/settings_window.py:_run_mic_test`：移除誤植的「非 macOS 拒絕」假擋板。

### 驗證證據

- `release_win.ps1` 通過 PowerShell 語法解析與 `-NoModel` 邏輯乾跑驗證；兩條新 workflow YAML 語法通過 `yaml.safe_load` 驗證；`check_dependency_freshness.py` 本機實跑成功（含 PyPI 查詢）。

## 上游繼承版本史（pre-fork，沿用上游紀錄）

以下為 SanHsien fork（v3.1.0）建立前，上游 `jfamily4tw/voicetype4tw-mac` 主線與其
`win-go-mask-202607` 分支的版本沿革精簡摘要，完整逐項細節原見已移除的
`VERSIONS.md`，此處僅留版本號與一句重點；日期、版本號、commit 碼均照原紀錄
保留、不竄改。

- **win-go-mask v3.0.1**（2026-07-08，`BUILD-3010-STABLE`）：真可攜版——`release_win.ps1` 全面改寫為自建完整可攜環境（內嵌 Python + 全部依賴 + medium 模型 + Starter EXE），UTF-8 with BOM 編碼修正。
- **v3.0.0**（2026-07-07，`BUILD-3000-STABLE`）：正式定義為 Windows 專用版，移除 51 個 macOS 遺留檔案（打包鏈、`stt/mlx_whisper.py`、`ui/vocab_editor.py` 等），文件全面改寫為 Windows-only。
- **v2.9.10**（2026-07-07）：設定頁各分頁細節修正（勾選框可辨識度、Windows 檔案總管開啟資料夾、記憶刪除/壓縮按鈕、署名改為 Claude Code）。
- **v2.9.9**（2026-07-07）：Dashboard 版面重整，修正模型偵測路徑真 bug（原查錯 `~/.cache/huggingface/hub`）與內容截斷問題。
- **v2.9.8**（2026-07-07）：新增全時自動觸發（`audio/auto_trigger.py` VAD 控制器）與多螢幕浮動視窗位置記憶。
- **v2.9.7**（2026-07-07）：Windows 安裝流程強化與 Starter EXE（`tools/launcher.cs`），Python 偵測加固、CUDA 條件安裝、補齊漏列依賴。
- **v2.8.2**（2026-03-04）：Mac 版旗艦功能對齊（處理耗時顯示、執行日誌系統）、API Key 預檢、雙層設定架構（`config_local.json`/`config_global.json`）。
- **v2.8.1-dev**（2026-03-04）：跨平台雲端同步開發起點——`get_sync_base_dir()` 指標重定向、`LOCAL_KEYS` 白名單雛形。
- **v2.8.0**（2026-03-03，Build B19）：瀏覽器輸入修復（移除注入攔截）、極簡托盤選單、浮動按鈕開關、解決 OpenMP 衝突與 Pystray 死鎖。
- **v2.7.32 B15**（2026-03-03）：托盤選單圖示更新失敗修復。
- **v2.7.32 B14**（2026-03-03）：日誌淨化，關閉 Debug 時不再輸出大量熱鍵日誌。
- **v2.7.32 B8-B13**（2026-03-03）：`keystrike.log` 職責分離、動態情境前綴、Build ID 追蹤系統、`<Draft>` XML 記憶保護雙層架構，B13 修正 SettingsWindow 崩潰。
- **v2.7.32 B7**（2026-03-03）：Prompt 結構優化，規則前置、資料後置，格式風格鎖定。
- **v2.7.32 B2-B6**（2026-03-03）：Demo 模式變數修復、`[底層靈魂]` 標籤格式校準、Demo 控制項整合、情境遍歷測試模式。
- **v2.7.32 beta**（2026-03-02）：Windows 移植起點——`KMP_DUPLICATE_LIB_OK=TRUE`、延遲導入、資料路徑導向 `%APPDATA%/VoiceType4TW`。
- **v2.7.24-pc-stable**（2026-03-01）：Windows 初心版，建立 PC 穩定執行環境基準與 Inno Setup 安裝配置。

[Unreleased]: https://github.com/SanHsien/voxprose/compare/v3.4.4...HEAD
[3.4.4]: https://github.com/SanHsien/voxprose/compare/v3.4.3...v3.4.4
[3.4.3]: https://github.com/SanHsien/voxprose/compare/v3.4.2...v3.4.3
[3.4.2]: https://github.com/SanHsien/voxprose/compare/v3.4.1...v3.4.2
[3.4.1]: https://github.com/SanHsien/voxprose/compare/v3.4.0...v3.4.1
[3.4.0]: https://github.com/SanHsien/voxprose/compare/v3.3.0...v3.4.0
[3.3.0]: https://github.com/SanHsien/voxprose/compare/v3.2.0...v3.3.0
[3.2.0]: https://github.com/SanHsien/voxprose/compare/v3.1.0...v3.2.0
[3.1.0]: https://github.com/SanHsien/voxprose/compare/b694e40...v3.1.0
