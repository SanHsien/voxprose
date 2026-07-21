#!/usr/bin/env python3
"""檢查上游專案 jfamily4tw/voicetype4tw-mac 是否有新 commit 待審視。

此工具供 GitHub Actions 排程與本地維護使用；它只查詢並輸出報告，
不會自行 merge/cherry-pick 任何 commit。比照 `tools/check_dependency_freshness.py`
的風格改寫（同樣走 stdlib、只輸出 Markdown + GitHub Actions output，不安裝額外套件）。

同步狀態設計（詳見 docs/UPSTREAM.md「同步狀態標記區塊」），每個追蹤分支記兩個欄位：
- `last_merged`：已合併進本 fork 的最後一個上游 commit（等同 `git merge-base
  HEAD upstream/<branch>` 可驗證的那個 commit）。`null` 表示這條線不併入程式碼，
  僅供分析追蹤（例如 Mac 主線）。
- `last_reviewed`：已審視過的最後一個上游 commit（含審視後決定不採用者）。

本工具只回報「比 `last_reviewed` 新」的 commit，避免每次都重複列出已經審視過、
決定不採用的上游變更。同步狀態怎麼解析、找不到時要多嚴格，見下方
`parse_sync_points()`——**解析失敗一律拋出 `UpstreamParseError` 並讓 main() 回傳
非 0**，絕不可以把「解析不出同步狀態」靜默當成「沒有更新」回報。
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_MD = ROOT / "docs" / "UPSTREAM.md"

SYNC_START_MARKER = "<!-- sync-points:start -->"
SYNC_END_MARKER = "<!-- sync-points:end -->"

# docs/UPSTREAM.md 目前追蹤的三個上游分支；`parse_sync_points()` 會確認
# 標記區塊裡三個分支都存在，缺一個都視為解析失敗（而非默默略過）。
REQUIRED_BRANCHES = ("win-go-mask-202607", "win-stable", "main")

DEFAULT_REPO = "jfamily4tw/voicetype4tw-mac"


class UpstreamParseError(Exception):
    """docs/UPSTREAM.md 的同步狀態標記區塊解析失敗時拋出。

    呼叫端（main()）必須讓這個例外導致非 0 exit code，絕不可以吞掉後
    當作「沒有更新」處理——見模組 docstring 與 AGENTS.md「不模擬」原則。
    """


def parse_sync_points(markdown_text: str) -> Dict[str, object]:
    """解析 docs/UPSTREAM.md 內容，回傳同步狀態標記區塊的 JSON 資料。

    標記區塊格式（docs/UPSTREAM.md 內建立）：

        <!-- sync-points:start -->
        ```json
        { "schema_version": 1, "repo": "...", "branches": {...} }
        ```
        <!-- sync-points:end -->

    任何一步失敗（找不到標記、標記內沒有 JSON 區塊、JSON 語法錯誤、
    缺少必要分支或欄位）都會拋出 UpstreamParseError，訊息內含具體原因，
    方便 CI log 與本機排錯直接看出是哪裡壞了。
    """
    start = markdown_text.find(SYNC_START_MARKER)
    end = markdown_text.find(SYNC_END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise UpstreamParseError(
            f"在 {UPSTREAM_MD} 找不到完整的 sync-points 標記區塊"
            f"（{SYNC_START_MARKER} ... {SYNC_END_MARKER}）。"
            "同步狀態資料是本工具唯一的資料來源，缺少此區塊無法判斷任何分支的狀態。"
        )

    block = markdown_text[start + len(SYNC_START_MARKER) : end]
    fence_match = re.search(r"```json\s*(\{.*?\})\s*```", block, re.DOTALL)
    if not fence_match:
        raise UpstreamParseError(
            "sync-points 標記區塊內找不到 ```json ... ``` fenced code block，"
            "無法解析同步狀態資料。"
        )

    raw_json = fence_match.group(1)
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise UpstreamParseError(
            f"sync-points 標記區塊內的 JSON 解析失敗：{exc}"
        ) from exc

    if not isinstance(data, dict):
        raise UpstreamParseError("sync-points JSON 最外層必須是物件（object）。")

    branches = data.get("branches")
    if not isinstance(branches, dict) or not branches:
        raise UpstreamParseError("sync-points JSON 缺少非空的 `branches` 物件。")

    missing = [name for name in REQUIRED_BRANCHES if name not in branches]
    if missing:
        raise UpstreamParseError(
            f"sync-points JSON 的 `branches` 缺少必要分支：{', '.join(missing)}"
        )

    for name in REQUIRED_BRANCHES:
        info = branches[name]
        if not isinstance(info, dict):
            raise UpstreamParseError(f"分支 `{name}` 的同步狀態資料必須是物件（object）。")
        last_reviewed = info.get("last_reviewed")
        if not last_reviewed or not isinstance(last_reviewed, str):
            raise UpstreamParseError(
                f"分支 `{name}` 缺少有效的 `last_reviewed`（不可為空/None）。"
            )

    return data


def load_sync_points(path: Path = UPSTREAM_MD) -> Dict[str, object]:
    """讀取並解析 docs/UPSTREAM.md 的同步狀態標記區塊。檔案不存在會直接拋出例外。"""
    text = path.read_text(encoding="utf-8")
    return parse_sync_points(text)


def _github_request(url: str, token: Optional[str], timeout: float = 15.0) -> object:
    """打 GitHub REST API，回傳解析後的 JSON。任何失敗都讓例外往上拋。"""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "voicetype-upstream-check",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - 固定 https
        return json.loads(resp.read().decode("utf-8"))


def fetch_new_commits(
    repo: str,
    branch: str,
    last_reviewed_sha: str,
    token: Optional[str] = None,
) -> List[Dict[str, str]]:
    """回傳 `last_reviewed_sha` 之後、branch tip 之前（不含 `last_reviewed_sha`
    本身）的新 commit 清單。

    用 GitHub compare API（base...head）：回傳的 `commits` 陣列是「head 可達、
    base 不可達」的 commit，順序由舊到新，正好對應「比 last_reviewed 新的變更」。
    每筆整理成 {sha, short_sha, date, title, author, url}。
    """
    url = (
        f"https://api.github.com/repos/{repo}/compare/"
        f"{last_reviewed_sha}...{branch}"
    )
    data = _github_request(url, token)
    commits = data.get("commits", []) if isinstance(data, dict) else []

    rows: List[Dict[str, str]] = []
    for commit in commits:
        sha = commit.get("sha", "")
        commit_info = commit.get("commit", {}) or {}
        message = commit_info.get("message", "") or ""
        title = message.splitlines()[0] if message else "(無標題)"
        author_info = commit_info.get("author", {}) or {}
        author = (
            author_info.get("name")
            or (commit.get("author") or {}).get("login")
            or "unknown"
        )
        date = author_info.get("date", "unknown")
        html_url = commit.get("html_url") or (
            f"https://github.com/{repo}/commit/{sha}" if sha else ""
        )
        rows.append(
            {
                "sha": sha,
                "short_sha": sha[:7] if sha else "unknown",
                "date": date,
                "title": title,
                "author": author,
                "url": html_url,
            }
        )
    return rows


def collect_branch_results(
    sync_points: Dict[str, object],
    repo: Optional[str] = None,
    token: Optional[str] = None,
) -> List[Dict[str, object]]:
    """對每個追蹤分支查詢新 commit，回傳每個分支的結果（含查詢失敗的錯誤訊息）。"""
    effective_repo = repo or sync_points.get("repo") or DEFAULT_REPO
    branches = sync_points["branches"]

    results: List[Dict[str, object]] = []
    for name in REQUIRED_BRANCHES:
        info = branches[name]
        last_reviewed = info["last_reviewed"]
        try:
            commits = fetch_new_commits(effective_repo, name, last_reviewed, token=token)
            results.append(
                {
                    "branch": name,
                    "last_reviewed": last_reviewed,
                    "last_merged": info.get("last_merged"),
                    "commits": commits,
                    "error": None,
                }
            )
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError) as exc:
            results.append(
                {
                    "branch": name,
                    "last_reviewed": last_reviewed,
                    "last_merged": info.get("last_merged"),
                    "commits": [],
                    "error": str(exc),
                }
            )
    return results


def render_markdown(results: List[Dict[str, object]], repo: str) -> str:
    """輸出 GitHub issue / log 可讀的 Markdown 報告。"""
    lines = [
        "# 上游更新檢查",
        "",
        f"來源專案：[`{repo}`](https://github.com/{repo})",
        "",
    ]

    any_error = False

    for result in results:
        branch = result["branch"]
        last_reviewed = result["last_reviewed"]
        lines.append(f"## `{branch}`（目前 last_reviewed：`{last_reviewed[:7]}`）")
        lines.append("")

        if result["error"]:
            any_error = True
            lines.append(f"查詢失敗：`{result['error']}`")
            lines.append("")
            continue

        commits = result["commits"]
        if not commits:
            lines.append("沒有比 last_reviewed 新的 commit。")
            lines.append("")
            continue

        for commit in commits:
            lines.append(
                f"- [`{commit['short_sha']}`]({commit['url']}) "
                f"{commit['title']}（{commit['author']}，{commit['date']}）"
            )
        lines.append("")

    lines.extend(
        [
            "## 審視後怎麼辦",
            "",
            "1. 先讀 commit 內容，判斷是否適用於本 fork 的 Windows 樹"
            "（Mac 專屬修復通常不適用）。",
            "2. **採用**：走一般 merge/cherry-pick 流程處理衝突，完成後回來更新 "
            "`docs/UPSTREAM.md` 同步狀態標記區塊的 `last_merged` 與 `last_reviewed`"
            "（同步更新「同步狀態表」的文字敘述）。",
            "3. **不採用**：只推進 `docs/UPSTREAM.md` 同步狀態標記區塊的 "
            "`last_reviewed`（不動 `last_merged`），**同時**在 `docs/UPSTREAM.md`"
            "「Skipped（審視後未採用）」表補一列（分支／commit／標題／審視日期／"
            "未採用理由），並在 `docs/DECISIONS.md` 記一句理由。`last_reviewed` "
            "負責「不再重複騷擾」，Skipped 表負責「不失憶」——兩者缺一不可，"
            "否則日後想回頭查「當初為什麼跳過」會查無所獲。",
            "4. 不論哪種結果，更新同步狀態是慣例，不是選項——這是讓下一次檢查"
            "不再重複報告同一批 commit 的唯一機制。",
        ]
    )

    if any_error:
        lines.insert(
            2,
            "> ⚠️ 部分分支查詢失敗（見下方章節），該分支的「沒有更新」判斷不可信，"
            "請人工確認或稍後重跑。",
        )

    return "\n".join(lines) + "\n"


def write_github_output(has_updates: bool, report_path: Path) -> None:
    """寫入 GitHub Actions output（$GITHUB_OUTPUT）。"""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"has_updates={'true' if has_updates else 'false'}\n")
        f.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="檢查上游 jfamily4tw/voicetype4tw-mac 是否有新 commit 待審視"
    )
    parser.add_argument(
        "--output",
        default="upstream-check-report.md",
        help="Markdown 報告輸出路徑",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="同時寫入 GitHub Actions output（has_updates / report_path）",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="覆寫上游 repo（預設讀 docs/UPSTREAM.md 同步狀態區塊內的 repo 欄位）",
    )
    args = parser.parse_args()

    try:
        sync_points = load_sync_points()
    except UpstreamParseError as exc:
        print(f"[ERROR] docs/UPSTREAM.md 同步狀態解析失敗：{exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[ERROR] 讀取 {UPSTREAM_MD} 失敗：{exc}", file=sys.stderr)
        return 1

    token = os.environ.get("GITHUB_TOKEN")
    effective_repo = args.repo or sync_points.get("repo") or DEFAULT_REPO

    results = collect_branch_results(sync_points, repo=args.repo, token=token)
    report = render_markdown(results, effective_repo)

    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(report)

    has_updates = any(bool(r["commits"]) for r in results)
    has_error = any(r["error"] for r in results)

    if args.github_output:
        write_github_output(has_updates, output_path)

    if has_error:
        print(
            "[ERROR] 至少一個分支查詢失敗，見上方報告；不把這次結果當成"
            "「確認沒有更新」，回傳非 0 exit code。",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
