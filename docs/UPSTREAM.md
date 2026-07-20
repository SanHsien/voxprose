# 上游追蹤（UPSTREAM）

> 建立日期：2026-07-20（v3.1.0 發版工程批次）
> 目的：本 fork 有兩條上游祖先鏈（Windows 線 + Mac 主線），squash 發版後歷史會被壓成單一 v3.1.0 commit。本檔記錄目前的同步基準點，讓未來合併能找到正確的 merge base，也方便日後追蹤兩邊上游的新變更。

## Upstream remote

```
upstream  https://github.com/jfamily4tw/voicetype4tw-mac.git
```

`git remote -v` 若尚未設定：

```
git remote add upstream https://github.com/jfamily4tw/voicetype4tw-mac.git
```

## 同步狀態表

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

## 檢查上游更新標準流程

```bash
# 1. 抓上游最新
git fetch upstream

# 2. Windows 線：win-go-mask-202607 有沒有新 commit
git log e5ddc02..upstream/win-go-mask-202607 --oneline

# 3. Windows 線：win-stable 有沒有新 commit（一般已穩定，但仍檢查）
git log b694e40..upstream/win-stable --oneline

# 4. Mac 線：main 有沒有新功能可吸收（僅供分析，不直接 merge 程式碼）
git log 46346d3..upstream/main --oneline
```

若上述任一指令有輸出，代表上游有新變更：
1. 先讀 commit 內容，判斷是否適用於 Windows 樹（Mac 專屬修復通常不適用）。
2. 適用的話，走一般 merge/cherry-pick 流程處理衝突。
3. **合併或分析完成後，回來更新本檔「同步狀態表」的對應同步點**（新的 tip commit hash、日期、內容摘要），維持本檔與實際狀態一致——這是慣例，不是選項。
