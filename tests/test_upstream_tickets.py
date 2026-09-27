"""上游 PR／issue 面向的契約測試。

每一條擋的都是「這個面向在沒有人決定的情況下悄悄不再被檢查」的一種方式。
測試不打網路：GitHub 查詢一律 monkeypatch。
"""

from __future__ import annotations

import sys
import urllib.error
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_upstream_updates as checker  # noqa: E402

SYNC_POINTS = {
    "repo": "example/product",
    "branches": {},
    "tickets": {"reviewed_pr_through": 9, "reviewed_issue_through": 8},
}


def fake_api(pages):
    """依呼叫順序回傳預先準備好的 API 回應。"""
    calls = []

    def request(url, token, timeout=15.0):
        calls.append(url)
        return pages.pop(0) if pages else []

    request.calls = calls
    return request


def test_tickets_are_queried_with_state_all(monkeypatch):
    """一個項目在兩次排程之間被開了又關，對本 fork 來說仍然是從沒審過。"""
    request = fake_api([[{"number": 10, "title": "closed without merging"}], []])
    monkeypatch.setattr(checker, "_github_request", request)

    checker.fetch_new_tickets("example/product", "pr", 9)

    assert "state=all" in request.calls[0]


def test_items_at_or_below_the_reviewed_number_stop_the_walk(monkeypatch):
    monkeypatch.setattr(
        checker,
        "_github_request",
        fake_api(
            [
                [
                    {"number": 11, "title": "new"},
                    {"number": 9, "title": "already triaged"},
                ]
            ]
        ),
    )

    items = checker.fetch_new_tickets("example/product", "pr", 9)

    assert [item["number"] for item in items] == [11]


def test_issue_endpoint_drops_pull_requests(monkeypatch):
    """GitHub 的 issue 端點會把 PR 一起回傳，兩個面向會重複計數。"""
    monkeypatch.setattr(
        checker,
        "_github_request",
        fake_api(
            [
                [
                    {"number": 12, "title": "a real issue"},
                    {"number": 11, "title": "a pull request", "pull_request": {}},
                ],
                [],
            ]
        ),
    )

    items = checker.fetch_new_tickets("example/product", "issue", 8)

    assert [item["number"] for item in items] == [12]


def test_a_failed_query_is_an_error_not_an_empty_result(monkeypatch):
    """「沒查到」和「沒有」在綠色報告裡長得一樣，只有一個是真的。"""

    def boom(url, token, timeout=15.0):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(checker, "_github_request", boom)

    results = checker.collect_ticket_results(SYNC_POINTS)

    assert [result["error"] is not None for result in results] == [True, True]
    assert "未檢查" in checker.render_ticket_markdown(results)


def test_report_covers_both_ticket_axes(monkeypatch):
    monkeypatch.setattr(checker, "_github_request", fake_api([[], []]))

    report = checker.render_ticket_markdown(checker.collect_ticket_results(SYNC_POINTS))

    assert "## 上游 Pull requests" in report
    assert "## 上游 Issues" in report
    assert "`#9`" in report and "`#8`" in report


def test_sync_points_actually_carry_the_two_watermarks():
    """水位寫在 docs/UPSTREAM.md 的 sync-points 區塊，而且真的被讀。"""
    tickets = checker.load_sync_points().get("tickets") or {}

    assert isinstance(tickets.get("reviewed_pr_through"), int)
    assert isinstance(tickets.get("reviewed_issue_through"), int)
