"""驗證 .github/workflows/ci.yml 的 Python 版本矩陣（2026-07-23 加固任務第
5 項）：pyproject.toml 原宣告支援 `>=3.10,<3.13`，但 CI 過去只測 3.12，
3.10/3.11 從未被實際驗證過。這裡鎖定矩陣涵蓋宣告的版本範圍，避免之後被
悄悄改回單一版本。

2026-07-23（同日第二輪，正式支援 3.13/3.14）：`requires-python` 放寬為
`>=3.10,<3.15`，本檔斷言邏輯是動態從 pyproject.toml 解析範圍再與矩陣比對
（見 `test_ci_matrix_covers_python_versions_declared_in_pyproject`），因此
兩邊只要同步更新就會繼續通過，不需要跟著改斷言本身。
"""
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


def _load_ci_yaml() -> dict:
    with open(CI_YML, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ci_yml_is_valid_yaml():
    data = _load_ci_yaml()
    assert isinstance(data, dict)
    assert "jobs" in data


def test_ci_matrix_covers_python_versions_declared_in_pyproject():
    data = _load_ci_yaml()
    job = data["jobs"]["smoke-test"]
    matrix_versions = set(job["strategy"]["matrix"]["python-version"])

    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', pyproject_text)
    assert m, "requires-python not found in pyproject.toml"
    requires_python = m.group(1)

    # ">=3.10,<3.13" -> declared minor versions {3.10, 3.11, 3.12}
    lower = re.search(r">=\s*3\.(\d+)", requires_python)
    upper = re.search(r"<\s*3\.(\d+)", requires_python)
    assert lower and upper, f"Could not parse requires-python bounds: {requires_python!r}"
    declared_versions = {f"3.{i}" for i in range(int(lower.group(1)), int(upper.group(1)))}

    assert matrix_versions == declared_versions, (
        f"CI matrix {matrix_versions} does not match pyproject.toml's "
        f"declared support range {requires_python!r} ({declared_versions})"
    )


def test_ci_matrix_uses_fail_fast_false_so_one_version_failing_doesnt_hide_others():
    data = _load_ci_yaml()
    job = data["jobs"]["smoke-test"]
    assert job["strategy"]["fail-fast"] is False


def test_setup_python_step_references_the_matrix_variable():
    data = _load_ci_yaml()
    job = data["jobs"]["smoke-test"]
    setup_steps = [s for s in job["steps"] if s.get("uses", "").startswith("actions/setup-python")]
    assert len(setup_steps) == 1
    assert setup_steps[0]["with"]["python-version"] == "${{ matrix.python-version }}"
