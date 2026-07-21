"""Tests for tools/check_upstream_updates.py.

Covers:
- Parsing the real docs/UPSTREAM.md sync-points block succeeds and yields
  correct sha values for all three tracked branches.
- Parsing failures raise UpstreamParseError loudly instead of being treated
  as "no updates" (see AGENTS.md "不模擬" principle and the task spec this
  tool was built against).
- Report rendering format, using mocked GitHub API responses only -- no real
  network calls are made anywhere in this test module.
"""
import json
import urllib.error

import pytest

import tools.check_upstream_updates as upstream_check
from tools.check_upstream_updates import (
    REQUIRED_BRANCHES,
    UPSTREAM_MD,
    UpstreamParseError,
    collect_branch_results,
    fetch_new_commits,
    load_sync_points,
    parse_sync_points,
    render_markdown,
    write_github_output,
)


# --- Parsing the real docs/UPSTREAM.md ---------------------------------

def test_parse_real_upstream_md_succeeds():
    data = load_sync_points()
    assert data["schema_version"] == 1
    assert data["repo"] == "jfamily4tw/voicetype4tw-mac"

    branches = data["branches"]
    for name in REQUIRED_BRANCHES:
        assert name in branches

    assert branches["win-go-mask-202607"]["last_merged"] == "e5ddc02"
    assert branches["win-go-mask-202607"]["last_reviewed"] == "e5ddc02"
    assert branches["win-stable"]["last_merged"] == "b694e40"
    assert branches["win-stable"]["last_reviewed"] == "b694e40"
    assert branches["main"]["last_merged"] is None
    assert branches["main"]["last_reviewed"] == "10b2fc8"
    assert branches["main"]["license_source"] == "46346d3"


def test_upstream_md_file_exists_at_expected_path():
    # Guard against the glob/path silently pointing at nothing.
    assert UPSTREAM_MD.exists()
    assert UPSTREAM_MD.name == "UPSTREAM.md"


# --- Parsing failures must raise, never silently mean "no updates" -----

def test_parse_missing_markers_raises():
    with pytest.raises(UpstreamParseError, match="找不到完整的 sync-points 標記區塊"):
        parse_sync_points("# 上游追蹤\n\n沒有任何標記區塊在這裡。\n")


def test_parse_marker_without_json_fence_raises():
    broken = (
        f"{upstream_check.SYNC_START_MARKER}\n"
        "這裡忘記放 ```json fenced code block 了\n"
        f"{upstream_check.SYNC_END_MARKER}\n"
    )
    with pytest.raises(UpstreamParseError, match="找不到.*fenced code block"):
        parse_sync_points(broken)


def test_parse_invalid_json_raises():
    # Braces are balanced (so the ```json fence regex matches and hands the
    # content to json.loads), but the trailing comma makes it invalid JSON.
    broken = (
        f"{upstream_check.SYNC_START_MARKER}\n"
        "```json\n"
        '{"schema_version": 1, "branches": {"foo": 1,}}\n'
        "```\n"
        f"{upstream_check.SYNC_END_MARKER}\n"
    )
    with pytest.raises(UpstreamParseError, match="JSON 解析失敗"):
        parse_sync_points(broken)


def test_parse_missing_branch_raises():
    payload = {
        "schema_version": 1,
        "repo": "jfamily4tw/voicetype4tw-mac",
        "branches": {
            "win-stable": {"last_merged": "b694e40", "last_reviewed": "b694e40"},
            # win-go-mask-202607 and main are missing on purpose.
        },
    }
    broken = (
        f"{upstream_check.SYNC_START_MARKER}\n"
        "```json\n"
        f"{json.dumps(payload)}\n"
        "```\n"
        f"{upstream_check.SYNC_END_MARKER}\n"
    )
    with pytest.raises(UpstreamParseError, match="缺少必要分支"):
        parse_sync_points(broken)


def test_parse_missing_last_reviewed_field_raises():
    payload = {
        "schema_version": 1,
        "repo": "jfamily4tw/voicetype4tw-mac",
        "branches": {
            "win-go-mask-202607": {"last_merged": "e5ddc02"},  # no "last_reviewed"
            "win-stable": {"last_merged": "b694e40", "last_reviewed": "b694e40"},
            "main": {"last_merged": None, "last_reviewed": "10b2fc8"},
        },
    }
    broken = (
        f"{upstream_check.SYNC_START_MARKER}\n"
        "```json\n"
        f"{json.dumps(payload)}\n"
        "```\n"
        f"{upstream_check.SYNC_END_MARKER}\n"
    )
    with pytest.raises(UpstreamParseError, match="缺少有效的 `last_reviewed`"):
        parse_sync_points(broken)


def test_parse_empty_branches_object_raises():
    broken = (
        f"{upstream_check.SYNC_START_MARKER}\n"
        "```json\n"
        '{"schema_version": 1, "branches": {}}\n'
        "```\n"
        f"{upstream_check.SYNC_END_MARKER}\n"
    )
    with pytest.raises(UpstreamParseError, match="非空的 `branches`"):
        parse_sync_points(broken)


# --- fetch_new_commits: GitHub compare API response parsing (mocked) ----

class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def _make_compare_payload(shas_and_titles):
    commits = []
    for sha, title, author, date in shas_and_titles:
        commits.append(
            {
                "sha": sha,
                "html_url": f"https://github.com/jfamily4tw/voicetype4tw-mac/commit/{sha}",
                "commit": {
                    "message": title,
                    "author": {"name": author, "date": date},
                },
            }
        )
    return {"commits": commits}


def test_fetch_new_commits_parses_compare_response(monkeypatch):
    payload = _make_compare_payload(
        [
            (
                "abcdef1234567890",
                "fix: something mac-specific\n\nlonger body here",
                "Jimmy",
                "2026-07-21T00:00:00Z",
            )
        ]
    )

    captured_urls = []

    def fake_urlopen(req, timeout=15.0):
        captured_urls.append(req.full_url)
        return _FakeHTTPResponse(payload)

    monkeypatch.setattr(upstream_check.urllib.request, "urlopen", fake_urlopen)

    commits = fetch_new_commits(
        "jfamily4tw/voicetype4tw-mac", "main", "10b2fc8", token=None
    )

    assert len(commits) == 1
    row = commits[0]
    assert row["sha"] == "abcdef1234567890"
    assert row["short_sha"] == "abcdef1"
    assert row["title"] == "fix: something mac-specific"
    assert row["author"] == "Jimmy"
    assert row["date"] == "2026-07-21T00:00:00Z"
    assert row["url"].endswith("abcdef1234567890")

    assert len(captured_urls) == 1
    assert "compare/10b2fc8...main" in captured_urls[0]


def test_fetch_new_commits_empty_when_no_new_commits(monkeypatch):
    def fake_urlopen(req, timeout=15.0):
        return _FakeHTTPResponse({"commits": []})

    monkeypatch.setattr(upstream_check.urllib.request, "urlopen", fake_urlopen)

    commits = fetch_new_commits(
        "jfamily4tw/voicetype4tw-mac", "win-stable", "b694e40", token=None
    )
    assert commits == []


def test_fetch_new_commits_sends_auth_header_when_token_present(monkeypatch):
    captured_requests = []

    def fake_urlopen(req, timeout=15.0):
        captured_requests.append(req)
        return _FakeHTTPResponse({"commits": []})

    monkeypatch.setattr(upstream_check.urllib.request, "urlopen", fake_urlopen)

    fetch_new_commits(
        "jfamily4tw/voicetype4tw-mac", "win-stable", "b694e40", token="fake-token-123"
    )

    assert len(captured_requests) == 1
    assert captured_requests[0].get_header("Authorization") == "Bearer fake-token-123"


def test_fetch_new_commits_works_without_token(monkeypatch):
    captured_requests = []

    def fake_urlopen(req, timeout=15.0):
        captured_requests.append(req)
        return _FakeHTTPResponse({"commits": []})

    monkeypatch.setattr(upstream_check.urllib.request, "urlopen", fake_urlopen)

    # Must not raise even though no token is supplied (anonymous rate limit).
    fetch_new_commits("jfamily4tw/voicetype4tw-mac", "win-stable", "b694e40", token=None)
    assert captured_requests[0].get_header("Authorization") is None


# --- collect_branch_results: per-branch error isolation -----------------

def test_collect_branch_results_isolates_per_branch_errors(monkeypatch):
    sync_points = {
        "schema_version": 1,
        "repo": "jfamily4tw/voicetype4tw-mac",
        "branches": {
            "win-go-mask-202607": {"last_merged": "e5ddc02", "last_reviewed": "e5ddc02"},
            "win-stable": {"last_merged": "b694e40", "last_reviewed": "b694e40"},
            "main": {"last_merged": None, "last_reviewed": "10b2fc8"},
        },
    }

    def fake_fetch(repo, branch, last_reviewed_sha, token=None):
        if branch == "win-stable":
            raise urllib.error.URLError("network is down")
        return []

    monkeypatch.setattr(upstream_check, "fetch_new_commits", fake_fetch)

    results = collect_branch_results(sync_points)
    by_branch = {r["branch"]: r for r in results}

    assert by_branch["win-stable"]["error"] is not None
    assert "network is down" in by_branch["win-stable"]["error"]
    assert by_branch["win-go-mask-202607"]["error"] is None
    assert by_branch["main"]["error"] is None


# --- render_markdown: report format --------------------------------------

def test_render_markdown_lists_commits_with_links():
    results = [
        {
            "branch": "main",
            "last_reviewed": "10b2fc8",
            "last_merged": None,
            "commits": [
                {
                    "sha": "abcdef1234567890",
                    "short_sha": "abcdef1",
                    "date": "2026-07-21T00:00:00Z",
                    "title": "fix: something",
                    "author": "Jimmy",
                    "url": "https://github.com/jfamily4tw/voicetype4tw-mac/commit/abcdef1234567890",
                }
            ],
            "error": None,
        },
        {
            "branch": "win-stable",
            "last_reviewed": "b694e40",
            "last_merged": "b694e40",
            "commits": [],
            "error": None,
        },
        {
            "branch": "win-go-mask-202607",
            "last_reviewed": "e5ddc02",
            "last_merged": "e5ddc02",
            "commits": [],
            "error": None,
        },
    ]

    report = render_markdown(results, "jfamily4tw/voicetype4tw-mac")

    assert "abcdef1" in report
    assert "https://github.com/jfamily4tw/voicetype4tw-mac/commit/abcdef1234567890" in report
    assert "fix: something" in report
    assert "沒有比 last_reviewed 新的 commit" in report
    assert "審視後怎麼辦" in report
    assert "Skipped" in report  # guidance must mention the Skipped table
    assert "DECISIONS.md" in report
    # Old jargon must not leak into the rendered report.
    assert "水位" not in report
    assert "evaluated" not in report


def test_render_markdown_surfaces_errors():
    results = [
        {
            "branch": "main",
            "last_reviewed": "10b2fc8",
            "last_merged": None,
            "commits": [],
            "error": "HTTP Error 403: rate limit exceeded",
        },
        {
            "branch": "win-stable",
            "last_reviewed": "b694e40",
            "last_merged": "b694e40",
            "commits": [],
            "error": None,
        },
        {
            "branch": "win-go-mask-202607",
            "last_reviewed": "e5ddc02",
            "last_merged": "e5ddc02",
            "commits": [],
            "error": None,
        },
    ]

    report = render_markdown(results, "jfamily4tw/voicetype4tw-mac")
    assert "查詢失敗" in report
    assert "rate limit exceeded" in report
    assert "不可信" in report


# --- write_github_output -------------------------------------------------

def test_write_github_output_writes_expected_lines(tmp_path, monkeypatch):
    gh_output = tmp_path / "gh_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_output))

    write_github_output(True, tmp_path / "report.md")

    content = gh_output.read_text(encoding="utf-8")
    assert "has_updates=true" in content
    assert "report_path=" in content


def test_write_github_output_noop_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    # Should not raise even though there's nothing to write to.
    write_github_output(False, tmp_path / "report.md")


# --- Terminology guard: no leftover jargon in source or docs -------------

def test_no_watermark_jargon_in_source_module():
    """The maintainer explicitly rejected the "水位/watermark/evaluated" jargon
    in favor of last_merged/last_reviewed. Guard against it creeping back in."""
    import inspect

    source = inspect.getsource(upstream_check)
    assert "水位" not in source
    assert "watermark" not in source.lower()
    # "evaluated" as an identifier/field name must not reappear (the English
    # word "evaluate" inside unrelated prose is not what we're guarding here,
    # but this module never had a legitimate reason to use either spelling).
    assert "evaluated" not in source
