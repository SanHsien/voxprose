"""排程維護 workflow 的防回歸測試。"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def test_all_workflow_yaml_is_valid():
    for path in WORKFLOWS.glob("*.yml"):
        data = _load_yaml(path)
        assert isinstance(data, dict), path
        assert "jobs" in data, path


def test_dependabot_tracks_pip_and_github_actions_weekly():
    data = _load_yaml(ROOT / ".github" / "dependabot.yml")
    updates = data["updates"]

    assert {entry["package-ecosystem"] for entry in updates} == {"pip", "github-actions"}
    assert all(entry["schedule"]["interval"] == "weekly" for entry in updates)


def test_dependency_tracker_has_issue_and_pr_permissions():
    data = _load_yaml(WORKFLOWS / "dependency-freshness.yml")

    assert data["permissions"]["issues"] == "write"
    assert data["permissions"]["pull-requests"] == "read"
    assert data["concurrency"]["cancel-in-progress"] is True


def test_codeql_uses_extended_python_queries():
    data = _load_yaml(WORKFLOWS / "codeql.yml")
    steps = data["jobs"]["analyze"]["steps"]
    init = next(step for step in steps if step.get("uses", "").startswith("github/codeql-action/init"))

    assert init["with"]["languages"] == "python"
    assert init["with"]["queries"] == "security-extended"
