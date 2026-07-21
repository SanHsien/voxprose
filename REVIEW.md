# 聲成文 VoxProse（前身 VoiceType4TW／嘴炮輸入法）Review

- **日期**：2026-07-20
- **Reviewer**：Claude Code（fresh-context 靜態 review，不承襲舊版 REVIEW.md 的敘事與判斷，僅取其「哪些問題曾被發現、哪個 commit 修的」事實）
- **Review 對象**：`main` 分支 @ `84d1b28`（v3.1.0，merge 兩個上游祖先 `51094bf` Mac 分岔點 + `e5ddc02` Windows 線最新併入點，squash 收斂為單一 commit）
- **方法與限制**：全樹靜態讀碼＋`python -m pytest tests/ -v` 實跑；未實機啟動 `python main.py`、未接真實麥克風/PyQt6 UI/雲端 API key 驗證行為（本機開發環境無 PyQt6/sounddevice，見第 7 節）

---

## 總評

**健康分數：7.6 / 10（原 7.5，2026-07-21 微調＋0.1）。**

這是一個把「个人 fork 的 Windows 語音輸入法」按照正規工程紀律整理過一輪的專案：233 個自動化測試、GitHub Actions CI（`windows-latest` 跑 py_compile + pytest）、每月依賴新鮮度檢查、`docs/DECISIONS.md`/`docs/UPSTREAM.md`/`CHANGELOG.md`/`AGENTS.md` 形成完整的決策留痕鏈，且本次 review 抽查的 15 項「已修」聲稱，逐一讀碼核實全部屬實（見第 3 節問題總帳）——這不是一份自我感覺良好的變更記錄，是真的改了程式碼。三個 STT/LLM 引擎（Gemini STT、OpenRouter STT、Claude LLM）曾經「使用者選了但完全沒作用、靜默失敗」的死路徑已修好並補了防回歸測試（AST 靜態掃描鎖欄位名），這類問題最容易被忽略也最傷使用者信任，能主動挖出三個同型 bug 說明整理過程有紮實的交叉檢查，而不是頭痛醫頭。

健康分數沒有給到 8 以上，原因原本有三個結構性缺口，其中一項已在本輪（2026-07-21）解決：**(1) 全部這些修復與新功能，沒有一項在真實 Windows 桌面環境跑過**——本次 review 與過去多輪修復都誠實承認「本機無 PyQt6/sounddevice，僅過 py_compile/單元測試」，對一個核心價值是「錄音→辨識→貼字」即時互動體驗的桌面程式，這仍是目前最大的未知數，**尚未解決**；**(2)（已解決）`ui/settings_window.py`（原 2164 行）god file 已於 `1252a68` 拆分**為 ~492 行薄殼＋`ui/settings/` 七分頁子套件，並跑過乾淨 venv 的實機建構煙霧測試（見問題總帳 #7）；**(3)（已解決）曾有一個文件治理缺口**——squash 成單一 v3.1.0 commit 後，`CHANGELOG.md`/`docs/DECISIONS.md` 裡引用的近 20 個「修復 commit hash」（`04d82cc`、`19017c8`、`aee3973` 等）已經不是目前 `HEAD` 的祖先，只殘留在本機 `reflog`（未來 `git gc` 或重新 clone 都會查無此 commit）；已於 `4278ff8` 在 `CHANGELOG.md:7`／`docs/DECISIONS.md:5` 補免責聲明說明此現象，詳見第 4 節 24-1。健康分數因 (2)(3) 已解決而從 7.5 微調至 7.6——微調而非大幅上修，是因為 (1) 真機驗證空白仍是最大且未變動的缺口，且 (2) 的修復本身也還只在乾淨 venv 煙霧測試層級驗證過，未涵蓋完整使用情境。整體而言：這是一個「紙面工程紀律做得很好、god file 這類程式碼結構債也已清理，但最後一哩實機驗證完全空白」的專案，下一步的第一優先序應該是真機跑通整條鏈路，而不是再繼續往上疊功能。

---

## 問題總帳

> 狀態標記：✅ 已修（附出處；squash 後 commit hash 多數已不在目前 `git log` 可達範圍內，一律註明「引自 CHANGELOG/DECISIONS，hash 現況見第 4 節」）｜⏳ 待修（附建議優先序）｜🚫 決定不做（附理由出處）｜🔍 需實機驗證。
> 編號延續舊版 REVIEW.md 風險排序表 1-12（該表對應的是 win-stable 分支尚未併入 main 前的狀態），13 起為 CHANGELOG/DECISIONS 記載的後續發現，24 起為本次 review 新發現（見第 4 節）。

| # | 問題 | 嚴重度 | 狀態 | 備註 |
|---|---|---|---|---|
| 1 | `voicetype_installer.iss` 引用不存在的 `platform_layer\*`，Inno Setup 打包大機率編譯失敗 | 高（打包鏈斷裂） | ✅ 已修（引自 CHANGELOG「Fixed」節，hash `04d82cc`，2026-07-19） | 本次核實：`voicetype_installer.iss` 全檔搜尋 `platform_layer` 已無結果 |
| 2 | STT 引擎選單「Gemini」選項無對應分派分支，選了會靜默 fallback 成本地 Whisper | 中高（使用者可見功能性 bug） | ✅ 已修（`71f0cbe`，2026-07-19） | 本次核實：`stt/__init__.py:16-18` 已有 `elif engine == "gemini": from .gemini_stt import GeminiSTT; return GeminiSTT(config)`；`tests/test_stt_engine_dispatch.py::test_every_ui_engine_option_has_a_real_dispatch_branch` 通過 |
| 3 | 完全沒有 Whisper 幻覺過濾機制，相對 Mac 主線是功能倒退 | 中高（辨識品質風險） | ✅ 已修（`7bf8592`，2026-07-19） | 本次核實：`stt/hallucination_filter.py`（112 行，三階段判定＋長尾重複偵測）存在，接線於 `ui/app.py:338-339`；`tests/test_stt_hallucination_filter.py` 7 個測試通過 |
| 4 | API Key 明碼且設計上會同步到第三方雲端資料夾（iCloud/Google Drive/NAS） | 高 | ✅ 已修（`cc1e2d1`，2026-07-19） | 本次核實：`config.py:55` `API_KEY_FIELDS = {k for k in DEFAULT_CONFIG if k.endswith("_api_key")}`，`LOCAL_KEYS` 收錄；`load_config()` 有一次性遷移邏輯（`config.py:102-112`）；`tests/test_config.py::test_load_config_migrates_leaked_api_key_from_global_to_local` 通過 |
| 5 | 完全沒有 `test_*.py`，核心 pipeline 零自動化測試覆蓋 | 中高 | ✅ 已修（`f8633de` 起，2026-07-19） | 本次核實：現樹 `tests/` 目錄 23 個測試檔，`python -m pytest tests/ -v` 實跑 **233 passed, 10 skipped**（見第 6 節） |
| 6 | `paths.py` 宣告的雲端同步路徑常數（`VOCAB_DIR`/`MEMORY_DIR`/`STATS_DIR`）是死碼，實際未同步 | 中（誤導性） | ✅ 已修（`c37b286` 2026-07-19 移除前三個；`AI_PERMANENT_MEMORY_PATH` 尾巴 `53a4ef3` 2026-07-20 補removed） | 本次核實：`paths.py:58-61` 現為說明性註解，四個常數本體已不存在；`vocab/manager.py:17` 註解確認命名撞名風險已知並處理 |
| 7 | `ui/settings_window.py` god file | 中 | ✅ 已修（`1252a68`，2026-07-21；squash 後短碼，見 docs/DECISIONS.md 關於歷史 commit hash 的說明） | 本次核實：`ui/settings_window.py` 從 2164 行縮減為 ~490 行薄殼（`SettingsWindow` 用多重繼承混入 7 個分頁 mixin，`_setup_ui`/`_load_data`/`_save_action` 等視窗骨架邏輯留在殼內）；七個分頁邏輯拆到 `ui/settings/`（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`）+ 共用元件 `common.py`；對外 `from ui.settings_window import SettingsWindow` 契約不變（`ui/app.py` 零 diff）；`tests/test_stt_engine_dispatch.py` 的 `STT_ENGINES` 靜態解析目標同步改指向 `ui/settings/common.py`，防護力不變。`python -m pytest tests/ -v`：246 passed, 10 skipped（較拆分前 241 passed 多 5，為新增的 5 個分頁檔被 `test_smoke.py` 全 repo py_compile 掃描一併計入）；另在乾淨 venv（僅裝 PyQt6，不裝 CUDA/faster-whisper）跑實機建構煙霧測試，`SettingsWindow()` 建構＋七頁逐一切換＋各頁 widget 存取＋正常 close，exit code 0 |
| 8 | `requirements-win.txt` 無版本上限鎖定 | 中低 | ✅ 已修（`266280d`，2026-07-21） | 本次核實：`requirements-win.txt`（14 行套件宣告）與 `requirements-cuda-win.txt`（2 行）現在**全部**帶 `<` 主版本上限（如 `PyQt6>=6.6.0,<7`）；`pywin32` 無傳統 semver 語意（單一遞增 build number）故鎖 `<400` 並加註說明，`certifi` 用日曆版本鎖 `<2027`；`tools/check_dependency_freshness.py` 只做「是否落後」提醒，不做版本上限治理，兩者互補 |
| 9 | `diagnose_mic.py` 在 Windows 上是 macOS-only 死碼空殼 | 低（誤導性，非功能風險） | ✅ 已修（`0ee2730`，2026-07-19） | 本次核實：全檔已重寫（90 行），無任何 `Darwin`/`platform.system()` 判斷式，改為真實列裝置＋實錄 0.5 秒 RMS 診斷 |
| 10 | PTT／VAD 全時模式並行時缺乏互斥檢查 | 低中 | ✅ 已修（`e33d479`，2026-07-19） | 本次核實：`audio/mutex.py`（79 行，`PttVadMutex` 純狀態機）存在，接線於 `ui/app.py:70-72,209-210,282-283,294`；`tests/test_recording_mutex.py` 7 個測試通過 |
| 11 | `eval()` 用於語音計算機指令，注入面 | 低（已有輸入清洗，仍是通用執行任意運算式機制） | ✅ 已修（`3d2c215`，2026-07-19） | 本次核實：`actions/builtins.py` 已無 `eval(` 呼叫，改 `ast.parse(mode="eval")` 白名單解析；`tests/test_calculator.py::test_builtins_module_has_no_eval_usage` 靜態守門測試通過 |
| 12 | `ui/settings_window.py` 硬編碼 macOS 字型 `Monaco` | 低（視覺不一致，非崩潰） | ✅ 已修（`2e52f87`，2026-07-19） | 本次核實（行號因 #7 god file 拆分已搬動）：原 `ui/settings_window.py:1119,1187` 兩處已隨拆分搬到 `ui/settings/soul_page.py:43,111`，皆為 `QFont("Consolas", ...)`，註解說明原因不變 |
| 13 | OpenRouter STT 引擎自始壞掉（與 #2 同型：簽章不符＋WAV bytes 重複編碼被吞掉） | 中高（使用者可見，靜默失敗） | ✅ 已修（`75952fd`，2026-07-19，修復 #2 時意外發現） | 本次核實：`stt/openrouter_stt.py:12-26` 直接把原始 WAV bytes 包 `io.BytesIO` 上傳，簽章對齊 `BaseSTT`；`tests/test_openrouter_stt.py` 5 個測試通過 |
| 14 | Claude LLM 引擎自始壞掉（讀 `claude_api_key`/`claude_model`，但 config/UI 存 `anthropic_*`，永遠拿空 key） | 中高（使用者可見，靜默失敗） | ✅ 已修（`9192ef6`，2026-07-19） | 本次核實：`llm/claude.py:14-15` 已讀 `anthropic_api_key`/`anthropic_model`；新增 `tests/test_llm_config_keys.py` 用 AST 靜態掃描鎖住全部 7 個 provider 的 config 欄位名防回歸，本次實跑通過 |
| 15 | 網路請求逾時缺口（`llm/claude.py` anthropic SDK、`stt/groq_whisper.py` groq SDK 無明確 timeout，落回 SDK 預設 600s） | 中 | ✅ 已修（`eb61819`，2026-07-19） | 本次核實：新增 `net_config.py`（18 行）定義 `CLOUD_REQUEST_TIMEOUT_SECONDS = 60`；`llm/claude.py:18` 的 `anthropic.Anthropic(..., timeout=CLOUD_REQUEST_TIMEOUT_SECONDS)` 已接線；`tests/test_provider_timeouts.py` 2 個測試（因本機未裝 anthropic/groq SDK 而 `skipped`，非失敗） |
| 16 | STT 語言 hint 被翻譯目標語言污染（用過一次「翻譯成英文」後，之後所有中文錄音都被當英文辨識） | 高（辨識品質，一次觸發長期影響） | ✅ 已修（`d99a326`，2026-07-20） | 本次核實：新增 `stt/language.py`（7 行，`get_transcription_language()`），`ui/app.py:322-323` 已接線改讀 `config["language"]`；`tests/test_stt_language_selection.py` 2 個測試通過 |
| 17 | 智慧詞彙學習對本地辨識完全無效（`subprocess_whisper.py` worker 從未讀取 IPC 訊息的 `prompt` 欄位，永遠用硬編字串當 `initial_prompt`） | 中高（功能名不副實） | ✅ 已修（`aee3973`，2026-07-20） | 本次核實：`stt/subprocess_whisper.py` 的 `_run_transcribe()` 已支援 `initial_prompt` 參數，worker 迴圈讀取 `msg.get("prompt")`；`tests/test_stt_transcribe_params.py` 5 個測試通過（含以 `inspect.getsource()` 靜態檢查 worker 原始碼的回歸測試） |
| 18 | LLM system prompt 分散在 4 個引擎各自硬編中文死屬性，無多語 fallback | 中 | ✅ 已修（`19017c8`，2026-07-20） | 本次核實：`llm/prompts.py`（39 行，`SYSTEM_PROMPTS` zh/en/ja）存在；`tests/test_llm_prompts.py` 9 個測試通過（含 6 個引擎的 fallback 驗證） |
| 19 | LLM 未啟用時輸出文字沒有任何贅詞清理（soul 系統形同虛設） | 中 | ✅ 已修（`da93f62`，2026-07-20） | 本次核實：`utils/soul_rules.py`（58 行純函式）存在，`ui/app.py:447,472` 接線 `_apply_basic_soul_rules`；`tests/test_soul_rules.py` 11 個測試通過 |
| 20 | `soul/scenario/default.md` 贅詞清單缺「所以說」「就是說」 | 低 | ✅ 已修（`1e53549`，2026-07-20） | 未逐字核對 diff，依 CHANGELOG 記載列為已修 |
| 21 | 無崩潰/環境診斷匯出管道，設定頁「系統診斷」按鈕是誤植的 macOS-only 死擋板 | 中（支援成本） | ✅ 已修（`7bc3b0f`，2026-07-20） | 本次核實：`utils/diagnostics.py`（281 行，環境資訊＋裝置清單＋日誌尾段＋脫敏設定 zip 匯出）存在；原 `ui/settings_window.py:1480-1487` 已隨 #7 god file 拆分搬到 `ui/settings/general_page.py:131-158`（含「🎤 麥克風測試與診斷」「📦 匯出診斷包」按鈕與擋板已移除的說明註解）；`tests/test_diagnostics.py` 13 個測試通過 |
| 22 | `vocab/manager.py` 本機常數 `VOCAB_DIR` 與已移除的雲端同步死碼常數同名，容易混淆 | 低 | ✅ 已修（`27d93c8`，2026-07-20） | 本次核實：`vocab/manager.py:17` 常數已改名 `_VOCAB_DATA_DIR`，註解說明沿革 |
| 23 | `requirements-win.txt` 列了 `pystray`，但 UI 已全面改用 `QSystemTrayIcon`（PyQt6 內建），是多餘依賴 | 低（清理項，非風險項） | ✅ 已修（`aa1e220`，2026-07-21） | 本次核實：`requirements-win.txt` 已移除 `pystray>=0.19.5`；全 repo grep `pystray` 零結果（連 `ui/menu_bar.py` 原本的殘留註解也隨死分支一併清除，見 24-2）；`ui/tray_manager.py:13,39,50,55` 確認為 `QSystemTrayIcon` 實作 |
| 24 | 見第 4 節「本次新發現」24-1（✅ 已處理）／24-2（✅ 已修）／24-3（🔍 需實機驗證聽感） | — | ✅/🔍 | 本次 review 新增項目，非歷史清單延續 |

**統計**：已修 23 項、待修 0 項、決定不做 0 項（歷史上的「不吸收」項目屬於功能吸收分析的範圍，非本問題總帳的 bug/風險，詳見第 5 節與 `docs/mac-mainline-absorption-analysis.md` 第 6 節，不重複列在此表）。**新發現 24-1／24-2 已處理**；另有一項貫穿全專案的最大缺口＝**全部修復與新功能尚未實機驗證**（UI/錄音/雲端 API 行為，見第 7 節「未驗證邊界」與下一步建議第 1 項），這不是單一 bug 而是整體狀態，未計入上述編號。

---

## 4. 本次新發現

### 24-1（中，文件治理缺口，✅ 已處理）squash 後大量修復 commit hash 已不在 `git log` 可達範圍——已於 `4278ff8`（2026-07-20）在 `CHANGELOG.md:7`／`docs/DECISIONS.md:5` 補免責聲明

`git log --oneline -5` 顯示 `HEAD` 為 `84d1b28`（merge，雙親 `51094bf`／`e5ddc02`），這是刻意設計的「squash 成單一 v3.1.0 commit」（`docs/UPSTREAM.md:26-33`、`docs/DECISIONS.md:7`）。但實際查證發現：`CHANGELOG.md`／`docs/DECISIONS.md` 裡引用的近 20 個「修復 commit hash」（如 `04d82cc`、`71f0cbe`、`19017c8`、`aee3973`、`d99a326` 等，即本表 #1-22 逐項引用的那些）**全部不是 `HEAD` 的祖先**（已用 `git merge-base --is-ancestor <hash> HEAD` 逐一驗證，全部回傳「NOT ancestor」）。這些 commit 目前只殘留在本機 `.git` 的 `reflog`（`git reflog` 可查到，如 `HEAD@{20}: commit: feat(llm): 集中化...`），是「squash 前 `HEAD` 曾經指到過的位置」留下的痕跡——**不在任何分支或標籤上**，未被 push 到任何 remote，未來只要跑 `git gc --prune=now`、或任何人重新 clone 這個 repo，這些 hash 就會徹底變成「bad object」查無此 commit。

`docs/DECISIONS.md:50` 已經記錄過一個相關但不同的案例（`51094bf` 這個 hash 在本 repo 指向一個無關的 README commit，因為它其實是「Mac 原始碼庫」的 hash，兩個不同 repo 撞號）——但這只解釋了「跨 repo 撞號」的情況，**沒有涵蓋「本 repo 自己的 squash 前 commit，現在也查無此 hash」這個更大範圍的現象**。換句話說：`CHANGELOG.md`/`docs/DECISIONS.md` 目前的寫法會讓讀者以為「這些 hash 是可以 `git show` 出來驗證的」，但除非剛好在 squash 發生後、`reflog` 過期前、且在同一台機器上，否則驗證不了。

**建議（已實施）**：`4278ff8` 已在 `CHANGELOG.md:7` 與 `docs/DECISIONS.md:5` 補上免責聲明——「本文件引用的更早 hash 屬 squash 前的開發過程紀錄，已不存在於 git 歷史，僅作為文件內的變更對照識別碼保留，無法 `git show`」，避免接手者照 hash 查證而撲空。本檔問題總帳的狀態欄出處也已改為優先引用 CHANGELOG/DECISIONS 章節而非單靠 hash（見文末維護慣例）。

### 24-2（低，清理項，✅ 已修）`ui/menu_bar.py` 殘留 pystray 時代的死分支，與 #23 同一批技術債——已於 `aa1e220`（2026-07-21）清理

修復前 `ui/menu_bar.py:187-199` 的 sender 文字取值邏輯（下列程式碼為修復前原始碼存檔，**已移除，非現況**）：

```python
if hasattr(sender, "text"):        # 187: PyQt6 / QAction check
    ...
elif hasattr(sender, "text"):      # 195: 註解寫「pystray check (label)」，但條件與上面完全相同
    raw_val = sender.text
elif isinstance(sender, str) and False:  # 198: 註解自承「legacy fallback (unused)」
    raw_val = sender
elif isinstance(sender, str):
    raw_val = sender
```

第 195 行的 `elif hasattr(sender, "text")` 與第 187 行條件完全相同，**永遠不可能被執行到**（`hasattr` 為 True 時第一個 `if` 已經接手）；第 198 行更直接用 `and False` 把自己永久短路，註解也自承「unused」。這三行合計是 Mac/pystray 跨平台時代遺留、Windows-only 化時沒有清乾淨的死碼——不影響現有行為（第一個 `if` 分支涵蓋所有實際情況），但容易誤導後續維護者以為系統還需要相容 pystray 的物件介面。與 #23（`requirements-win.txt` 殘留 `pystray` 套件宣告）是同一批「pystray 退場沒清乾淨」的技術債。

**已修**：`aa1e220` 已將這兩處死分支（原 195、198 行）與 `requirements-win.txt` 的 `pystray>=0.19.5` 一併移除。本次核實 `ui/menu_bar.py:186-199` 現況只剩一個 `if hasattr(sender, "text")` 分支＋`elif isinstance(sender, str)` 字串 fallback，無任何 pystray 殘留死碼；`tests/` 全數通過（233 passed, 10 skipped，不變）。

### 24-3（🔍 需驗證，非缺陷）`stt/hallucination_filter.py` 的極短口語詞（「嗯」「啊」等）落入黑名單，可能誤殺合法極短語音

`stt/hallucination_filter.py:48-50` 的黑名單包含單字語氣詞（「嗯」「啊」「喔」「哦」「嗯哼」「呃」「嗯嗯」）與純標點（「。」「...」「…」）。`is_hallucination()` 的判定邏輯（`stt/hallucination_filter.py:94-98`）在整段文字去除頭尾標點、轉小寫後，若**整段**剛好等於黑名單裡的一個詞，就判定為幻覺並丟棄。這代表使用者如果真的只對著麥克風說一個字「嗯」（例如附和某人、確認收到），這段合法但極短的語音會被當作 Whisper 幻覺整段拋棄，使用者會發現「說了但沒反應」。

這是移植自 Mac 主線既有邏輯（`docs/mac-mainline-absorption-analysis.md` 13-3/15-1/15-2/16-1/16-2 標記「已存在」，非本次新增），且 `audio/recorder.py` 另有 `len(audio_data) < 8000` 的短音檔長度守衛可能先一步擋掉極短錄音（需要確認兩者的觸發順序與門檻是否會讓「說一個字」永遠進不到這裡）——因此標記為「需驗證」而非「新 bug」：實機測試時建議專門測一次「只說一個語氣詞」的案例，確認是否符合預期（多數使用情境下，使用者不太可能只想輸入單一語氣詞，這個取捨可能是合理的，但目前沒有看到任何測試或文件明確討論過這個邊界案例的取捨理由）。

---

## 5. 現況架構速覽

| 模組 | 行數級距 | 職責 |
|---|---|---|
| `main.py` | ~130 | 進入點：crash-proofing 環境變數、`initialize_paths()`、啟動 `VoiceTypeApp` |
| `ui/app.py` | ~600 | `VoiceTypeApp(QObject)` 協調者：熱鍵/錄音/STT/LLM/注入/記憶全流程 orchestration |
| `ui/settings_window.py` | ~492 | `SettingsWindow` 薄殼：多重繼承混入 `ui/settings/` 七分頁 mixin，`_setup_ui`/`_load_data`/`_save_action` 等視窗骨架邏輯（god file 已拆分，見問題總帳 #7） |
| `ui/settings/`（8 檔） | ~各 40~360 | 設定視窗七分頁 mixin（`dashboard_page.py`／`engine_page.py`／`soul_page.py`／`vocab_mem_page.py`／`sync_page.py`／`stats_page.py`／`general_page.py`）+ 共用元件與常數 `common.py` |
| `ui/menu_bar.py`／`tray_manager.py`／`mic_indicator.py`／`floating_button.py`／`positions.py`／`about_window.py` | 各 ~70~360 | PyQt6 選單列／系統匣／浮動指示／浮動按鈕／視窗位置記憶／關於視窗 |
| `hotkey/listener.py` | ~140 | 純 `ctypes` 輪詢 Win32 API 的全域熱鍵，無 `pynput` |
| `audio/recorder.py`／`auto_trigger.py`／`gain.py`／`mutex.py` | ~80~190 | PTT 錄音／VAD 全時模式／增益＋AGC 純函式／PTT-VAD 互斥狀態機 |
| `stt/`（8 檔） | ~10~460 | `subprocess_whisper.py`（子行程隔離本地 Whisper，最大最複雜）＋ 4 個雲端引擎＋`hallucination_filter.py`＋`language.py` |
| `llm/`（9 檔） | ~10~100 | 7 個 provider（無 minimax）＋`base.py`＋`prompts.py`（集中化 system prompt） |
| `output/injector.py` | ~165 | 剪貼簿 + `SendInput` 模擬注入 |
| `vocab/`／`memory/`／`stats/` | ~95~240 | 自訂詞彙學習／跨 session 記憶／使用統計，各自本機 `%APPDATA%` |
| `utils/`（6 檔） | ~20~280 | 品牌/AppUserModelID、權限（多為 no-op）、資源路徑、靈魂規則純函式、診斷包匯出 |
| `tools/`（4 檔） | ~40~185 | 環境預檢、模型下載、可攜 Python 下載腳本、依賴新鮮度檢查 |
| `config.py`／`paths.py`／`net_config.py` | ~20~175 | 設定讀寫（本地/雲端分流）、路徑常數、逾時常數 |
| `tests/`（23 檔） | — | 233 個自動化測試，見第 6 節 |

---

## 6. 各面向短評

**品質**：核心邏輯模組（`audio/gain.py`、`utils/soul_rules.py`、`stt/hallucination_filter.py`、`audio/mutex.py`、`llm/prompts.py`）都刻意抽成無重量依賴的純函式檔案，docstring 交代移植來源、動機與取捨，這是本次 review 讀到最一致的優點——不是「為了測試而測試」，是真的把可測試性當架構考量。曾經持續膨脹（2050→2164 行）沒人動的 `ui/settings_window.py` god file 已於 `1252a68` 拆分為 ~492 行薄殼＋`ui/settings/` 七分頁子套件（#7）；`ui/menu_bar.py` 的 pystray 時代死碼也已於 `aa1e220` 清理（24-2）。目前無已知的程式碼結構性缺點待清；剩下的缺口是第 7 節列出的實機驗證空白。

**安全與隱私**：API Key 已全部本地化並有遷移邏輯（問題總帳 #4）；計算機 `eval()` 已改 AST 白名單（#11）；`utils/diagnostics.py` 匯出診斷包前會 `_sanitize_config()` 脫敏（`utils/diagnostics.py:44-59`）；`requirements-win.txt`/`requirements-cuda-win.txt` 已補主版本上限（`266280d`，#8）。仍存在但屬「已知且刻意不動」的殘留風險：`llm/gemini.py` 的 API key 走 URL query string（Google 官方設計，非本 repo 問題）。

**測試與 CI**：`python -m pytest tests/ -v` 本次實跑 **233 passed, 10 skipped**，與 `docs/DECISIONS.md` 2026-07-20 條目記載的數字一致。10 個 skip 全部是「本機開發環境缺少可選依賴」造成（`pytest.importorskip("anthropic")`／`("groq")`，以及 PyQt6/sounddevice 相關模組的 import 測試），不是測試邏輯有問題，且 `test_smoke.py` 用同一套「optional import 就 skip」機制涵蓋了這件事的誠實聲明。CI（`.github/workflows/ci.yml`）在 `windows-latest` 上跑 py_compile 全樹 + pytest，`release.yml`／`dependency-freshness.yml` 兩條輔助 workflow 也都語法正確（已用 `yaml.safe_load` 等方式驗證，見 `docs/DECISIONS.md`）。**缺口**：CI 只驗證「能 compile、單元測試過」，不驗證「PyQt6 UI 能開起來」，這與第 7 節的實機驗證空白是同一個缺口的兩面。

**打包發佈**：`setup_win.bat`／`release_win.ps1`／`voicetype_installer.iss` 三條路徑齊全，`voicetype_installer.iss` 的死引用已修（#1）。`release_win.ps1` 新增 `-NoModel` 選項（`release_win.ps1:13,26-28`），與 `-Lite`／預設 Full 三種組合的資料夾命名/CUDA 安裝/模型隨附條件已核對邏輯正確。`release.yml` 只建置 Lite/NoModel 兩版（Full 版含模型體積問題，決策記載於 `docs/DECISIONS.md`），這個範圍限縮有清楚理由，不是遺漏。**這整條打包鏈本身也是「寫得對」與「跑得動」的差距未知**——CI 目前不曾真的跑過 `setup_win.bat`/`release_win.ps1` 端到端建置。

**文件**：`AGENTS.md`／`SKILL.md`／`docs/DEVELOPMENT.md`／`docs/DECISIONS.md`／`docs/UPSTREAM.md`／`CHANGELOG.md` 形成了清楚的分工（各司其職，非重複堆疊），`README.md`/`README.en.md` 中英版本結構、章節、安裝步驟一致（已抽查頭部與快速安裝三步驟段落，用詞對應良好）。**曾發現的缺口（已處理）**：squash 後的 commit hash 引用失效問題（24-1）已於 `4278ff8` 在 `CHANGELOG.md:7`／`docs/DECISIONS.md:5` 補免責聲明涵蓋。

---

## 7. 未驗證邊界（誠實聲明）

以下項目本次 review **只做了靜態讀碼與 `pytest` 驗證，沒有在真實環境執行**，這與過去幾輪修復（`docs/DECISIONS.md` 各條目)的誠實聲明範圍一致，本次沒有新增驗證能力，原樣列出：

- **實機 UI**：`python main.py` 從未在本次或過去任一輪修復中被實際啟動過（開發環境無 PyQt6）。`ui/settings_window.py` 的麥克風裝置下拉選單、增益 slider、AGC 勾選框、「📦 匯出診斷包」按鈕、「🎤 麥克風測試」擋板移除後的實際彈窗行為，全部只讀過原始碼與 py_compile。
- **真麥克風鏈路**：`audio/recorder.py` 的 `device`/`gain`/`gain_auto` 參數、AGC 動態調整、`audio/mutex.py` PTT/VAD 互斥在真實硬體上的實際體感（純函式邏輯本身有單元測試覆蓋，但「接上真麥克風後聽起來對不對」未驗證）。
- **真 API key 雲端引擎**：Groq／Gemini／OpenRouter／Claude／OpenAI／Qwen／DeepSeek 七個 provider 的請求/回應皆為 `httpx.post`/SDK mock 測試，未用真實 API key 打過一次真實請求（`tests/test_provider_timeouts.py` 兩個測試因本機未裝 `anthropic`/`groq` SDK 而 `skipped`，並非「已驗證但通過」）。
- **CUDA 實機**：`requirements-cuda-win.txt`、`stt/subprocess_whisper.py` 的 CUDA DLL 路徑注入與可用性驗證降級邏輯，未在有 NVIDIA GPU 的機器上跑過。
- **NoModel/Lite 包實際安裝體驗**：`release.yml` CI 建置通過（產出 ZIP、算出 SHA256），但沒有人工解壓縮、雙擊啟動、走過首次啟動下載模型的完整流程。
- **極短語氣詞邊界案例**（見 24-3）：「只說一個字」是否會被幻覺過濾器或短音檔長度守衛擋下、擋下的行為是否符合預期，需要實機錄一次驗證。

---

## 8. 下一步建議

1. **（最高優先）實機驗證整條鏈路**：在有 PyQt6/sounddevice/麥克風的 Windows 機器上跑一次 `python main.py`，走過「熱鍵錄音→本地 Whisper 辨識→LLM 潤飾→貼字」全流程，以及設定頁新按鈕（麥克風裝置切換、增益 slider、診斷包匯出）。這是目前唯一一項「紙面完成、實機完全未知」的大類缺口，優先於任何新功能。
2. ~~**在 `CHANGELOG.md`/`docs/DECISIONS.md` 補一句 squash hash 失效聲明**（見 24-1）~~：**已完成**（`4278ff8`，2026-07-20）。
3. ~~清理 pystray 殘留（#23 + 24-2）~~：**已完成**（`aa1e220`，2026-07-21）——`requirements-win.txt` 已移除 `pystray>=0.19.5`，`ui/menu_bar.py` 死分支已移除。
4. ~~`ui/settings_window.py` 拆分（#7）~~：**已完成**（`1252a68`，2026-07-21）——拆為 ~492 行薄殼＋`ui/settings/` 七分頁子套件，已跑過乾淨 venv 實機建構煙霧測試。
5. ~~`requirements-win.txt` 補版本上限（#8）~~：**已完成**（`266280d`，2026-07-21）——`requirements-win.txt`/`requirements-cuda-win.txt` 全數套件已加主版本上限。
6. **在有真實 CUDA GPU 與各雲端 API key 的環境跑一次端到端整合測試**，把第 7 節列出的未驗證邊界逐項清空。

---

## 9. 維護慣例

- **REVIEW.md 採 latest-only**：只放最新一次覆核於根目錄，不逐版累積歷史（比照 `docs/DECISIONS.md` 2026-07-19 條目定下的慣例）。
- **修 bug 必回註本檔問題總帳的狀態欄**：規則見 [`AGENTS.md`](AGENTS.md)「開發約定」——適用所有 AI agent（Claude、Codex、Gemini 等），非 Claude 專屬。修復 `⏳ 待修` 項目或本檔未列出的新 bug 時，回到第 3 節對應列（或新增列）標註修復依據與日期；不得讓本檔長期陳列已解決的問題而不更新狀態。
- **修復回註格式建議**：狀態欄改 `✅ 已修` 時附「commit 訊息摘要或 CHANGELOG/DECISIONS 章節出處＋日期」，鑑於 24-1 的發現，**不建議繼續依賴 commit hash 作為唯一可驗證依據**（squash 後會失效），優先引用 `CHANGELOG.md`/`docs/DECISIONS.md` 的章節標題與日期。

---

*本 review 為對 `main` 分支（`84d1b28`，v3.1.0）的 fresh-context 靜態程式碼閱讀分析，`python -m pytest tests/ -v` 已實跑（233 passed, 10 skipped）；未安裝 PyQt6/sounddevice、未實機啟動程式、未使用真實 API key 或 CUDA 硬體驗證行為。工作樹本身未做任何修改，僅新增/改寫本檔案（`REVIEW.md`）。*
