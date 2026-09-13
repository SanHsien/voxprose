"""Repository guard against broad bare-except handlers.

Regression: QA-HARDEN-001 — bare except handlers can swallow SystemExit and
KeyboardInterrupt in addition to ordinary runtime failures.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
EXCLUDED_PARTS = {".git", "venv", ".venv", "build", "dist", ".runtime"}


def test_repository_has_no_bare_except_handlers():
    offenders = []
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")

    assert offenders == []
