"""Regression checks for GitHub Actions that target the current Node runtime.

Regression: REVIEW 28-9 — older action majors targeted deprecated Node.js 20.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"


def _workflow_text(name: str) -> str:
    return (WORKFLOW_DIR / name).read_text(encoding="utf-8")


def _major_versions(text: str, action: str) -> list[int]:
    pattern = rf"uses:\s*{re.escape(action)}@v(\d+)"
    return [int(value) for value in re.findall(pattern, text)]


def test_official_actions_use_node24_generation():
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(WORKFLOW_DIR.glob("*.yml"))
    )

    assert _major_versions(workflow_text, "actions/checkout")
    assert min(_major_versions(workflow_text, "actions/checkout")) >= 7
    assert _major_versions(workflow_text, "actions/setup-python")
    assert min(_major_versions(workflow_text, "actions/setup-python")) >= 7
    assert _major_versions(workflow_text, "actions/upload-artifact")
    assert min(_major_versions(workflow_text, "actions/upload-artifact")) >= 7


def test_release_action_uses_node24_generation():
    release_text = _workflow_text("release.yml")
    versions = _major_versions(release_text, "softprops/action-gh-release")

    assert versions
    assert min(versions) >= 3
