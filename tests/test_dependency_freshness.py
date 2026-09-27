"""依賴新鮮度工具的解析、判斷與報告測試。"""

from pathlib import Path

from tools import check_dependency_freshness as freshness


def test_parse_requirements_reads_bounds_and_source_files(tmp_path: Path):
    win = tmp_path / "requirements-win.txt"
    cuda = tmp_path / "requirements-cuda-win.txt"
    win.write_text("PyQt6>=6.6.0,<7\nopenai>=1.30.0,<3  # cloud\n", encoding="utf-8")
    cuda.write_text("nvidia-cudnn-cu12>=8.9.2,<10\n", encoding="utf-8")

    packages = freshness.parse_requirements((win, cuda))

    assert packages["pyqt6"]["minimum"] == "6.6.0"
    assert packages["pyqt6"]["upper"] == {"operator": "<", "version": "7"}
    assert packages["openai"]["requirement"] == "openai>=1.30.0,<3"
    assert packages["nvidia-cudnn-cu12"]["files"] == ["requirements-cuda-win.txt"]


def test_collect_status_marks_in_range_latest_as_no_attention(monkeypatch):
    packages = {
        "example": {
            "name": "example",
            "minimum": "1.0.0",
            "upper": {"operator": "<", "version": "2"},
            "requirement": "example>=1.0.0,<2",
            "files": ["requirements-win.txt"],
        }
    }
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: "1.4.0")

    row = freshness.collect_status(packages)[0]

    assert row["baseline_behind"] is True
    assert row["blocked_by_upper"] is False
    assert row["check_failed"] is False
    assert row["needs_attention"] is False


def test_marks_new_major_as_blocked_by_upper_bound(monkeypatch):
    packages = {
        "example": {
            "name": "example",
            "minimum": "1.0.0",
            "upper": {"operator": "<", "version": "2"},
            "requirement": "example>=1.0.0,<2",
            "files": ["requirements-win.txt"],
        }
    }
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: "2.1.0")

    row = freshness.collect_status(packages)[0]

    assert row["baseline_behind"] is True
    assert row["blocked_by_upper"] is True
    assert row["needs_attention"] is True


def test_versions_with_only_trailing_zero_difference_are_equal():
    assert freshness.is_newer_version("1.14.0", "1.14") is False
    assert freshness.is_newer_version("1.14.1", "1.14") is True


def test_marks_lookup_failure_for_attention(monkeypatch):
    packages = freshness.parse_requirements(
        [Path(__file__).resolve().parent.parent / "requirements-win.txt"]
    )
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: None)

    rows = freshness.collect_status(packages)

    assert rows
    assert all(row["check_failed"] for row in rows)


def test_render_markdown_explains_manual_review_policy():
    report = freshness.render_markdown(
        [
            {
                "name": "PyQt6",
                "minimum": "6.6.0",
                "upper": {"operator": "<", "version": "7"},
                "requirement": "PyQt6>=6.6.0,<7",
                "files": ["requirements-win.txt"],
                "latest": "7.0.0",
                "baseline_behind": True,
                "blocked_by_upper": True,
                "check_failed": False,
                "needs_attention": True,
            }
        ]
    )

    assert "有新版主線，需評估相容性" in report
    assert "不自動合併依賴 PR" in report
    assert "（installed）" not in report


def test_render_markdown_explains_latest_is_resolvable_within_range():
    report = freshness.render_markdown(
        [
            {
                "name": "example",
                "minimum": "1.0.0",
                "upper": {"operator": "<", "version": "2"},
                "requirement": "example>=1.0.0,<2",
                "files": ["requirements-win.txt"],
                "latest": "1.4.0",
                "baseline_behind": True,
                "blocked_by_upper": False,
                "check_failed": False,
                "needs_attention": False,
            }
        ]
    )

    assert "最新版未超出版本範圍" in report
    assert "不需僅因最低支援版較舊而開啟維護 issue" in report


def test_github_output_only_requests_attention_for_blocked_or_failed(
    monkeypatch, tmp_path: Path
):
    output_path = tmp_path / "github-output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))

    freshness.write_github_output(
        baseline_behind=True,
        blocked_by_upper=False,
        check_failed=False,
        report_path=tmp_path / "report.md",
    )

    values = output_path.read_text(encoding="utf-8")
    assert "baseline_behind=true" in values
    assert "blocked_by_upper=false" in values
    assert "needs_attention=false" in values


def _blocked_package():
    return {
        "example": {
            "name": "example",
            "minimum": "1.0.0",
            "upper": {"operator": "<", "version": "2"},
            "requirement": "example>=1.0.0,<2",
            "files": ["requirements-win.txt"],
        }
    }


def test_approved_deferral_clears_attention_for_the_version_it_was_judged_against(
    monkeypatch,
):
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: "2.1.0")
    monkeypatch.setattr(
        freshness,
        "load_deferrals",
        lambda: {"example": {"deferredLatest": "2.1.0", "reason": "判斷過，暫不升。"}},
    )

    row = freshness.collect_status(_blocked_package())[0]

    # 仍然如實記錄它超出上限，只是不再要求注意。
    assert row["blocked_by_upper"] is True
    assert row["deferred_reason"] == "判斷過，暫不升。"
    assert row["needs_attention"] is False


def test_deferral_lapses_when_upstream_publishes_a_newer_version(monkeypatch):
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: "2.2.0")
    monkeypatch.setattr(
        freshness,
        "load_deferrals",
        lambda: {"example": {"deferredLatest": "2.1.0", "reason": "判斷過，暫不升。"}},
    )

    row = freshness.collect_status(_blocked_package())[0]

    assert row["deferred_reason"] is None
    assert row["needs_attention"] is True


def test_deferral_without_a_reason_is_ignored(monkeypatch):
    monkeypatch.setattr(freshness, "fetch_pypi_version", lambda _name: "2.1.0")
    monkeypatch.setattr(
        freshness,
        "load_deferrals",
        lambda: {"example": {"deferredLatest": "2.1.0", "reason": "   "}},
    )

    row = freshness.collect_status(_blocked_package())[0]

    assert row["deferred_reason"] is None
    assert row["needs_attention"] is True


def test_load_deferrals_returns_empty_when_the_file_is_missing_or_broken(tmp_path: Path):
    assert freshness.load_deferrals(tmp_path / "nope.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert freshness.load_deferrals(broken) == {}


def test_repo_deferrals_file_is_parseable_and_every_entry_states_a_reason():
    for name, entry in freshness.load_deferrals().items():
        assert isinstance(entry.get("deferredLatest"), str) and entry["deferredLatest"], name
        assert isinstance(entry.get("reason"), str) and entry["reason"].strip(), name
