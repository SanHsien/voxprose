# 上游追蹤（UPSTREAM）

> 建立日期：2026-07-20（v3.1.0 發版工程批次）
> 目的：本 fork 有兩條上游祖先鏈（Windows 線 + Mac 主線），squash 發版後歷史會被壓成單一 v3.1.0 commit。本檔記錄目前的同步基準點，讓未來合併能找到正確的 merge base，也方便日後追蹤兩邊上游的新變更。

## 同步狀態標記區塊（機器可讀，唯一真相源）

`tools/check_upstream_updates.py` 只解析下面這個標記區塊來取得每個上游分支的同步狀態，**不會**去讀下方「同步狀態表」的文字敘述。這是刻意設計：人類讀敘述、機器讀 JSON，避免兩處各自維護造成漂移。**改動任一分支的狀態時，這個區塊與下方「同步狀態表」必須同步更新**——區塊是唯一真相源，敘述表只是給人看的說明，不一致以區塊為準。

本表記錄本 fork 與上游各分支的同步狀態：`last_merged` = 已合併進本 fork 的最後一個上游 commit（等同 `git merge-base HEAD upstream/<branch>` 可驗證的那個 commit）；`last_reviewed` = 已審視過的最後一個上游 commit（含審視後決定不採用者）。兩者之間的差距列於下方「Skipped（審視後未採用）」表。`tools/check_upstream_updates.py` 只會回報比 `last_reviewed` 新的變更，避免每次都重複列出已經審視過、決定不採用的上游 commit。

<!-- sync-points:start -->
```json
{
  "schema_version": 1,
  "repo": "jfamily4tw/voicetype4tw-mac",
  "branches": {
    "win-go-mask-202607": {
      "last_merged": "e5ddc02",
      "last_reviewed": "e5ddc02"
    },
    "win-stable": {
      "last_merged": "b694e40",
      "last_reviewed": "b694e40"
    },
    "main": {
      "last_merged": null,
      "last_reviewed": "10b2fc8",
      "license_source": "46346d3",
      "note": "Mac 線，程式碼不追蹤（僅分析吸收），license_source 記錄 LICENSE 取自 main 的哪個 commit"
    }
  }
}
```
<!-- sync-points:end -->

## Skipped（審視後未採用）

`last_reviewed` 只負責「不再重複騷擾」——一旦推進過，`tools/check_upstream_updates.py` 就不會再報告該 commit。但這也代表「當初審視後認定不適用、但日後情勢改變可能變得該採用」的 commit 會永遠消失在檢查報告視野外。這張表就是防失憶用的留檔：**每次審視後決定「不採用」，除了推進 `last_reviewed`，都必須在這裡補一列**，讓未來有人（或自己）想查「這條上游分支曾經有過哪些被跳過的變更」時查得到。

**日後若對熱鍵監聽（`hotkey/listener.py`）、程式退出流程或類似生命週期管理做架構級重構，應先回掃此表，確認有沒有當初因「macOS 專屬、不適用」跳過、但新架構下可能變得適用的項目。**

| 上游分支 | Commit | 標題 | 審視日期 | 未採用理由 |
|---|---|---|---|---|
| `main`（Mac 線） | [`0ed0c47`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/0ed0c47) | fix: clean up runtime on native macOS quit | 2026-07-20 | macOS 專屬（AppKit 應用程式退出清理流程），本 fork 是 Windows-only 樹、無 AppKit 相依，不適用。 |
| `main`（Mac 線） | [`10b2fc8`](https://github.com/jfamily4tw/voicetype4tw-mac/commit/10b2fc8) | fix: keep hotkey watchdog recovering | 2026-07-20 | macOS 專屬（CGEventTap watchdog 復原機制），本 fork 熱鍵走 `hotkey/listener.py` 的 Win32 `GetAsyncKeyState` 輪詢架構，兩者監聽機制完全不同，不適用；此 commit 同時也是 `main` 分支目前的 `last_reviewed`。 |

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
| `main`（Mac 線） | 程式碼不追蹤；fork 分岔點 `51094bf`（Revise README contributors and version info，v2.9.16，2026-07-08） | 不併入程式碼，僅分析吸收 | `51094bf` 是 Mac 主線與本 fork 的共同祖先，作為「Mac 功能吸收分析」的基準點，詳細逐版逐項分析見 [`docs/mac-mainline-absorption-analysis.md`](./mac-mainline-absorption-analysis.md)。其後的 Mac 專屬修復 `0ed0c47`（fix: clean up runtime on native macOS quit）與 `10b2fc8`（fix: keep hotkey watchdog recovering）評估為 macOS 平台專屬，不適用於 Windows 樹。LICENSE 另取自 `main` 分支 tip `46346d3`（docs: add MIT license and contribution guide，2026-07-20）——雙軌授權因此收斂為全 MIT。 |

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
3. **不採用**：只推進「同步狀態標記區塊」的 `last_reviewed`（不動 `last_merged`），**同時**在上方「Skipped（審視後未採用）」表補一列（分支／commit／標題／審視日期／未採用理由），並在 [`docs/DECISIONS.md`](DECISIONS.md) 記一句理由。`last_reviewed` 負責「不再重複騷擾」，Skipped 表負責「不失憶」——兩者缺一不可，否則日後想回頭查「當初為什麼跳過」會查無所獲。
4. 不論哪種結果，更新同步狀態是慣例，不是選項——這是讓下一次檢查不再重複報告同一批 commit 的唯一機制。

舊版「用 `git log A..upstream/B` 手動比對」流程仍然有效（尤其想看完整 diff 時），但日常的「有沒有新東西要看」判斷已由上述自動機制取代，不需要每次手動下指令。

```bash
# 手動比對範例（A 換成該分支目前的 last_reviewed）
git fetch upstream
git log <last-reviewed-sha>..upstream/<branch-name> --oneline
```
