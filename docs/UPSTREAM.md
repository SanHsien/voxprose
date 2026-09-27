# 上游追蹤（UPSTREAM）

> 建立日期：2026-07-20（v3.1.0 發版工程批次）
> 目的：本 fork 有兩條上游祖先鏈（Windows 線 + Mac 主線），squash 發版後歷史會被壓成單一 v3.1.0 commit。本檔記錄目前的同步基準點，讓未來合併能找到正確的 merge base，也方便日後追蹤兩邊上游的新變更。

## 同步狀態標記區塊（機器可讀，唯一真相源）

`tools/check_upstream_updates.py` 只解析下面這個標記區塊取得每個上游分支的同步狀態，**不會**讀下方「同步狀態表」的文字敘述——人類讀敘述、機器讀 JSON，避免兩處各自維護造成漂移；**改動任一分支狀態時兩處必須同步更新**，不一致以區塊為準。

`last_merged` = 已合併進本 fork 的最後一個上游 commit（等同 `git merge-base HEAD upstream/<branch>`）；`last_reviewed` = 已審視過的最後一個上游 commit（含決定不採用者，只負責「不再重複騷擾」）。兩者差距列於下方「Skipped（審視後未採用）」表，負責「不失憶」；`tools/check_upstream_updates.py` 只回報比 `last_reviewed` 新的變更。

<!-- sync-points:start -->
```json
{
  "schema_version": 1,
  "repo": "jfamily4tw/voicetype4tw-mac",
  "branches": {
    "win-go-mask-202607": {
      "last_merged": "e5ddc02",
      "last_reviewed": "3387daf",
      "note": "last_reviewed 推進至 3387daf（V3.0.2，2026-08-20，Python 支援放寬到 3.10-3.14）：本 fork 已在 V3.4.4 支援 3.10-3.14（pyproject requires-python >=3.10,<3.15、setup_win.bat 由新到舊探測、CI 五個版本都跑），且探測順序比上游新（上游 3.12 優先，本 fork 3.14 優先），無可引用內容。"
    },
    "win-stable": {
      "last_merged": "b694e40",
      "last_reviewed": "b694e40"
    },
    "main": {
      "last_merged": null,
      "last_reviewed": "4269178",
      "license_source": "46346d3",
      "note": "Mac 線，程式碼不追蹤（僅分析吸收），license_source 記錄 LICENSE 取自 main 的哪個 commit。last_reviewed 推進至 4269178（v2.9.19，2026-07-23，Apple Local prompt leak hotfix）：只修改 Apple Foundation Models helper、llm/apple_local.py 與 macOS DMG/版本資料，本 Windows-only fork 無 Apple Local 引擎或 Swift helper，已列 Skipped 表。前一筆 805b007 的 3 項平台無關修正已另行吸收，見 CHANGELOG v3.3.0；10b2fc8／0ed0c47 為更早的 macOS 專屬 commit，均已列 Skipped 表；46346d3 的 LICENSE 已採用"
    }
  },
  "tickets": {
    "reviewed_pr_through": 9,
    "reviewed_issue_through": 8,
    "reviewed_date": "2026-08-23",
    "note": "首次盤點 PR/issue（本檔先前只追 commit）。查詢一律 --state all：一個項目在兩次檢查之間被開了又關，對本 fork 來說仍是從沒審過。逐筆結論見本檔 2026-08-23 段落。"
  }
}
```
<!-- sync-points:end -->

## Skipped（審視後未採用）

**每次審視後決定「不採用」，除了推進 `last_reviewed`，都必須在這裡補一列**，供日後查「這條上游分支曾有哪些被跳過的變更」。日後若對熱鍵監聽（`hotkey/listener.py`）、程式退出流程等生命週期管理做架構級重構，應先回掃此表，確認有沒有當初因「macOS 專屬」跳過、但新架構下可能變得適用的項目。

| 上游分支 | Commit | 標題 | 審視日期 | 未採用理由 |
|---|---|---|---|---|
| `main`（Mac 線） | [`0ed0c47`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/0ed0c47) | fix: clean up runtime on native macOS quit | 2026-07-20 | macOS 專屬（AppKit 應用程式退出清理），本 fork 無 AppKit 相依，不適用。 |
| `main`（Mac 線） | [`10b2fc8`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/10b2fc8) | fix: keep hotkey watchdog recovering | 2026-07-20 | macOS 專屬（CGEventTap watchdog），本 fork 熱鍵走 Win32 `GetAsyncKeyState` 輪詢架構，不適用。 |
| `main`（Mac 線） | [`805b007`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/805b007) | release: v2.9.18 mac apple local correction | 2026-07-22 | Apple Foundation Models 整套、Mac 打包鏈與 Mac 專屬 UI 改動是 macOS 26 專屬，Windows 無對應物；`COMMON_ALIAS_CORRECTIONS` 是原作者個人別名，無普遍價值。其中 3 項平台無關修正已另行吸收，見 CHANGELOG v3.3.0：vocab 短 ASCII 縮寫守衛、OpenCC 簡轉繁後處理概念（獨立實作為 `utils/zh_convert.py`）、學習詞排序穩定化。 |
| `main`（Mac 線） | [`4269178`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/42691782e517d68f0acbf1f26a4db2f544e78086) | fix: prevent apple local prompt leakage | 2026-07-28 | 修正 Apple Foundation Models 偶發回吐提示詞：改 Swift `LanguageModelSession` prompt、清洗 `llm/apple_local.py` 輸出，並更新 macOS DMG／版本資料。VoxProse 沒有 Apple Local 引擎、Swift helper、DMG 打包鏈或 `llm/apple_local.py`，現有雲端／Ollama 引擎走不同實作，無可移植的同型修補。 |

## Mac 主線分析：評估後不吸收

> 2026-07-20 對 Mac 主線 tip `51094bf`（v2.9.16）相對分岔點 v2.9.6（`b9f997b`）的逐版逐項吸收分析（原 `docs/mac-mainline-absorption-analysis.md`，已於文件整理批次併入本檔並移除）。可攜／需改寫兩類項目（共 15 項）已全數吸收或有明確處置，詳見 `CHANGELOG.md`；以下為評估後**明確不吸收**的項目，保留理由供日後回掃參考。

| 項目 | 理由 |
|---|---|
| 7-7 設定頁版面調整（QGridLayout 對齊、白色 slider QSS、warmup 進度條） | 現樹設定頁已大幅分岔（自行迭代過 Settings UI Refinements），Mac 版面 patch 無法直接套；已隨麥克風裝置選擇（7-1）批次做時順手參考版面，不單獨吸收。 |
| 8-1 MiniMax LLM 引擎 | 純 HTTP API 可攜，但是否採用屬產品決策（維護者是否使用 MiniMax），技術上可攜但預設引擎清單變更需維護者拍板。 |
| 10-1 target_pid 精準注入（`CGEventPostToPid` 等效：Win32 `GetForegroundWindow`/`SetForegroundWindow`） | 概念值得（Windows 同樣有長轉錄期間切視窗貼錯地方的風險），惟需全新 Win32 接線且有 `SetForegroundWindow` 前景鎖定限制地雷；建議等使用者實際回報貼錯視窗再立項。 |
| 11-1 CGEventTap 三層自癒、11-2 keystrike log 改 queue | macOS event tap 專屬失效模式（callback 超時被系統靜默停用），Windows 低階鍵盤 hook 架構無此病。 |
| 12-1/12-2/13-5/13-6/13-7 打包鏈修復（codesign reseal、libssl rpath、MLX 版本 pin、entitlements、warmup noop） | macOS 簽章／MLX／dylib 專屬，Windows 打包鏈（`release_win.ps1`）無對應物。 |
| 13-4 default `llm_engine` 改 openrouter | 一行改動但屬產品決策：無 OpenRouter key 的使用者體驗未必較好，需維護者確認。 |
| 14-1 MLX Whisper GPU thread-safety lock（class-level `_gpu_lock`） | MLX/Metal command queue 專屬考量，現樹無 MLX；若日後併發轉錄（熱鍵路徑 vs 全時模式）出現崩潰，可回頭參考其「class-level 序列化」思路。 |
| 15-4 設定頁模型順序修復（`MODEL_META` dict 順序） | 現樹設定頁無同構的 `MODEL_META` 結構，Mac 版一致性 bug 不存在於現樹。 |
| 16-5 模型外部快取目錄 + symlink | 現樹 `bundled_models/` 隨附模型機制已用不同方式滿足同一需求。 |

## 2026-08-22：上游 PR／issue 盤點——全數 macOS 專屬，不引用

上游當時 **1 個 open PR、3 個 open issue、5 個分支**。四項全部落在 macOS 專屬失效模式，
本 fork 是 Windows 線，沒有對應物：

| 項目 | 結論 |
|---|---|
| PR [#9](https://github.com/jfamily4tw/voicetype4tw-mac/pull/9) 修正 macOS 打包、翻譯與執行期問題 | 不引用。打包鏈是 codesign／dylib／entitlements，本 fork 走 `release_win.ps1`；上方「Mac 主線分析」已對同類項目（12-1/12-2/13-5～13-7）記過不吸收。翻譯部分本 fork 已自行繁中化。 |
| issue #6 MLX Whisper GPU SIGSEGV（多執行緒競態） | 不引用。MLX/Metal 專屬；本 fork 無 MLX。若日後併發轉錄在 Windows 出現崩潰，可回頭參考它「class-level 序列化」的思路（同上分析 14-1）。 |
| issue #7 Apple Silicon 上 bundled OpenSSL rpath 錯誤 | 不引用。macOS dylib 路徑專屬。 |
| issue #8 macOS 自動貼上失敗需手動 Cmd+V | 不引用。本 fork 的注入走 Win32 低階鍵盤路徑，失效模式不同。 |

**分支**：上游 5 個分支，3 個不是 PR head——`win-stable`、`win-go-mask-202607`、
`feature/v2.9.7-clean`。前兩個相對 Mac `main` 顯示 ahead 19／22，那不是「有未吸收的東西」，
而是 Windows 線與 Mac 線本來就分岔；本檔上方的同步狀態標記區塊已對這兩個分支逐一記
`last_merged`／`last_reviewed`（`b694e40`／`e5ddc02`），是本批 fork 裡唯一做到逐分支追蹤的。
`feature/v2.9.7-clean`（ahead 4）是 v2.9.7 的 README 與截圖整理，屬 Mac 線文件，不吸收。

**水位**：PR 已看到 **#9**、issue 已看到 **#8**（GitHub 的 PR 與 issue 共用編號序，實際水位取
`#9`）。下次只看更大的編號；commit 水位仍由本檔的同步狀態標記區塊管，分支水位同上。

## Upstream remote

```
upstream  https://github.com/jfamily4tw/voicetype4tw-mac.git
```

`git remote -v` 若尚未設定：

```
git remote add upstream https://github.com/jfamily4tw/voicetype4tw-mac.git
```

## 同步狀態表

> 以下為人類可讀的說明，**同步狀態的唯一真相源是上方「同步狀態標記區塊」**；若這裡的敘述與標記區塊不一致，以標記區塊為準（代表這裡漏更新了，應盡快修正）。

| 上游分支 | 上游 tip commit | 併入狀態 | 備註 |
|---|---|---|---|
| `win-stable` | `b694e40`（release(win): mark win-go-mask v3.0.1，2026-07-08） | 已完整併入 | v3.0.1 基底，本 fork 早期歷史直接構築於此分支之上。 |
| `win-go-mask-202607` | `e5ddc02`（Assets: regenerate README screenshots from the live V3.0.1 UI，2026-07-20） | 已併入（merge commit `12f51d6`） | 內容：三步驟安裝流程、README 改寫、新截圖。**例外**：其 `paths.py`（`VERSION_NAME`/`BUILD_ID`）與 `voicetype_installer.iss`（`MyAppVersion`/`OutputBaseFilename`）版本字串未採用——installer 那筆是 `MyAppVersion "2.8.27_V90"`，明顯是上游誤植降版（早於本 fork 當時的 3.0.1），本樹版本號自行管理，不隨上游該筆走。 |
| `main`（Mac 線） | 程式碼不追蹤；fork 分岔點 `51094bf`（Revise README contributors and version info，v2.9.16，2026-07-08） | 不併入程式碼，僅分析吸收 | `51094bf` 是 Mac 主線與本 fork 的共同祖先，作為「Mac 功能吸收分析」的基準點，詳細逐版逐項分析已併入本檔上方「Mac 主線分析：評估後不吸收」小節。最新已審視至 `4269178`（Apple Local prompt leak hotfix，2026-07-23）；該筆與較早的 `0ed0c47`、`10b2fc8` 均屬 macOS 專屬，未採用理由見 Skipped 表。LICENSE 另取自 `main` 分支 tip `46346d3`（docs: add MIT license and contribution guide，2026-07-20）——雙軌授權因此收斂為全 MIT。 |

## Squash 後的雙親關係

v3.1.0 發版時，本 fork 全部 commit 會 squash 成單一 commit。為了讓未來 merge 仍有正確的 merge base，squash commit 會保留雙親：

- 親 1：`51094bf`（Mac 主線分岔點，v2.9.16）
- 親 2：`e5ddc02`（Windows 線 win-go-mask-202607 最新併入點）

兩條上游祖先鏈都保留在 commit graph 中，日後任一邊有新變更時，`git merge` / `git log A..upstream/B` 都能找到正確的共同祖先，不會出現「歷史不相關」的合併衝突。

## 自動檢查機制

`.github/workflows/upstream-check.yml` 每週一 02:00 UTC 自動執行（另支援 `workflow_dispatch` 手動觸發），跑 `tools/check_upstream_updates.py`：解析上方「同步狀態標記區塊」取得三個分支各自的 `last_reviewed`，透過 GitHub REST API（compare API）查詢上游三個分支比 `last_reviewed` 新的 commit。有新變更時，開一個新 issue 或在既有「上游更新檢查」issue 補 comment（比照 `dependency-freshness.yml` 的 search-or-create 邏輯），標題固定「上游更新檢查：有新 commit 待審視」。

同樣的檢查也可以在本機手動跑：

```bash
python tools/check_upstream_updates.py --output upstream-check-report.md
# 有 GITHUB_TOKEN 環境變數可提高 API rate limit（非必要，匿名也能跑，額度較低）
GITHUB_TOKEN=ghp_xxx python tools/check_upstream_updates.py --output upstream-check-report.md
```

腳本輸出的報告會列出每個分支比 `last_reviewed` 新的 commit（sha、日期、標題、作者、連結），並附上「審視後怎麼辦」指引：

1. 先讀 commit 內容，判斷是否適用於 Windows 樹（Mac 專屬修復通常不適用）。
2. **採用**：走一般 merge/cherry-pick 流程處理衝突，完成後回來更新本檔「同步狀態標記區塊」（與下方「同步狀態表」同步）的 `last_merged` 與 `last_reviewed`。
3. **不採用**：只推進「同步狀態標記區塊」的 `last_reviewed`（不動 `last_merged`），**同時**在上方「Skipped」表補一列，並在 [`docs/DECISIONS.md`](DECISIONS.md) 記一句理由。
4. 不論哪種結果，更新同步狀態是慣例，不是選項——這是讓下一次檢查不再重複報告同一批 commit 的唯一機制。

舊版「用 `git log A..upstream/B` 手動比對」流程仍然有效（尤其想看完整 diff 時），但日常的「有沒有新東西要看」判斷已由上述自動機制取代，不需要每次手動下指令。

```bash
# 手動比對範例（A 換成該分支目前的 last_reviewed）
git fetch upstream
git log <last-reviewed-sha>..upstream/<branch-name> --oneline
```

## 2026-08-23：首次盤點上游 PR 與 issue，並推進 Windows 線水位

這份文件先前**只追 commit**。`sync-points` 沒有 PR／issue 欄位，`check_upstream_updates.py` 也
不查——也就是說那兩個面向不是「查過沒發現」，而是**根本沒查**，而報告一直是綠的。本輪補上，
查詢一律用 `--state all`：一個項目在兩次檢查之間被開了又關，對本 fork 來說仍然是從沒審過。

### commit：`win-go-mask-202607` 推進到 `3387daf`

`3387daf`（V3.0.2，2026-08-20）把上游的 Python 支援從 3.10–3.12 放寬到 3.10–3.14。
**本 fork 已經走在前面**：`pyproject.toml` 是 `requires-python = ">=3.10,<3.15"`、
`setup_win.bat` 由新到舊探測（3.14 → 3.13 → 3.12 → 3.11 → 3.10，上游是 3.12 優先）、
CI 五個版本都跑，版本已是 V3.4.4。沒有可引用的內容，水位推進即可。

`main`（Mac 線）與 `win-stable` 各 0 個新 commit。

### PR：4 筆已關閉／1 筆 open，全數不引用

| PR | 結論 |
| --- | --- |
| [#9](https://github.com/jfamily4tw/voicetype4tw-mac/pull/9) 修正 macOS 打包、翻譯與執行期問題（open） | **不適用**：macOS 打包（DMG／codesign）與 Apple 平台執行期。本 fork 是 Windows-only，沒有對應層。 |
| [#5](https://github.com/jfamily4tw/voicetype4tw-mac/pull/5)／[#4](https://github.com/jfamily4tw/voicetype4tw-mac/pull/4) 麥克風裝置選擇與增益（已關閉，未合併） | **已涵蓋**：本 fork 的設定頁早有麥克風裝置選擇（`ui/settings/`），且走 Windows 的音訊裝置列舉；上游那兩筆是 macOS 的 Qt multimedia 路徑。 |
| [#2](https://github.com/jfamily4tw/voicetype4tw-mac/pull/2) Qwen3-ASR 1.7B STT 引擎（已關閉，未合併） | **不引用**：新增引擎屬產品範圍決策，且上游自己沒有合併。**觸發條件**：本線決定支援該引擎時再回頭看這份實作。 |
| [#1](https://github.com/jfamily4tw/voicetype4tw-mac/pull/1) MLX Whisper（Apple Silicon 加速，已合併） | **不適用**：Apple Silicon 專屬加速路徑。 |

### issue：4 筆，其中一筆值得實查

| issue | 結論 |
| --- | --- |
| [#3](https://github.com/jfamily4tw/voicetype4tw-mac/issues/3) `UnicodeDecodeError on startup`（已關閉） | **實查後：本 fork 不受影響。** 這是唯一與平台無關的一筆（以 UTF-8 讀到不是 UTF-8 的檔案就炸）。全 repo 掃過 `open(` 的文字模式呼叫，只有 `stt/subprocess_whisper.py:60` 的 faulthandler 檔沒有帶 `encoding=`，而那個 handle 是交給 `faulthandler` 以 fileno 寫入、不做文字解碼。設定與設定頁的讀取全部顯式帶 `encoding`。 |
| [#8](https://github.com/jfamily4tw/voicetype4tw-mac/issues/8) macOS 自動貼上失敗需手動 Cmd+V | **不適用**：macOS Accessibility 貼上路徑。本 fork 走 Windows 的輸入注入。 |
| [#7](https://github.com/jfamily4tw/voicetype4tw-mac/issues/7) Apple Silicon 上 bundled OpenSSL 路徑錯誤 | **不適用**：macOS 打包產物的動態連結路徑。 |
| [#6](https://github.com/jfamily4tw/voicetype4tw-mac/issues/6) MLX Whisper GPU crash（SIGSEGV） | **不適用**：MLX 是 Apple Silicon 專屬後端，本 fork 沒有。 |

### 水位

- commit：`main` `4269178`／`win-stable` `b694e40`／`win-go-mask-202607` **`3387daf`**
- PR：**#9**、issue：**#8**（首次記錄，寫在 `sync-points` 的 `tickets` 區塊）

**判準**：上游是 Mac 線為主、本 fork 是 Windows-only，所以「不適用」在這裡幾乎都可以指到具體的
平台層（Apple Silicon／MLX／DMG／Accessibility）。真正要逐字看的是**與平台無關**的那些——像
issue #3 的編碼問題——那類一律要打開本 fork 的程式碼確認，不能從標題推斷。
