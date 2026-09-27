#!/usr/bin/env python3
"""檢查 VoxProse 直接依賴的最新版是否仍在允許範圍內。

此工具只讀取 requirements-win.txt / requirements-cuda-win.txt 的宣告與
PyPI JSON API，不讀取目前電腦已安裝的套件版本，確保本機與 GitHub Actions
產生一致結果。它只輸出維護報告，不會自行修改依賴或建立 Release。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_FILES = (
    ROOT / "requirements-win.txt",
    ROOT / "requirements-cuda-win.txt",
)
DEFERRALS_PATH = ROOT / ".github" / "dependency-deferrals.json"

_PACKAGE_RE = re.compile(r"^([A-Za-z0-9_.-]+)\s*(.*)$")
_SPECIFIER_RE = re.compile(
    r"(>=|>|<=|<|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*(?:\.[0-9A-Za-z!+_-]+)*)"
)


def normalize_package_name(package_name: str) -> str:
    """依 Python 套件名稱規則正規化連字號、底線與大小寫。"""
    return re.sub(r"[-_.]+", "-", package_name).lower()


def parse_version(text: str) -> tuple:
    """將一般 PyPI 版本轉成可比較的數值 tuple。

    本專案直接依賴目前使用一般數字版本或 calendar version；PyPI JSON 的
    ``info.version`` 只回傳穩定最新版，因此不需要完整實作 PEP 440 resolver。
    """
    parts = []
    for piece in (text or "").strip().lstrip("vV").split("."):
        match = re.match(r"(\d+)", piece)
        parts.append(int(match.group(1)) if match else 0)
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """latest 是否比 current 新。"""
    return parse_version(latest) > parse_version(current)


def parse_requirements(paths: Iterable[Path]) -> "Dict[str, Dict[str, object]]":
    """解析直接依賴、最低版本、上限與來源檔案。"""
    packages: "Dict[str, Dict[str, object]]" = {}
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith(("-", "http://", "https://")):
                continue
            match = _PACKAGE_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            specifiers = _SPECIFIER_RE.findall(match.group(2))
            minimum = next(
                (version for operator, version in specifiers if operator in {">=", ">", "==", "~="}),
                "",
            )
            upper = next(
                (
                    {"operator": operator, "version": version}
                    for operator, version in specifiers
                    if operator in {"<", "<="}
                ),
                None,
            )
            normalized = normalize_package_name(name)
            packages[normalized] = {
                "name": name,
                "minimum": minimum,
                "upper": upper,
                "requirement": line,
                "files": [path.name],
            }
    return packages


def fetch_pypi_version(package_name: str, timeout: float = 10.0) -> Optional[str]:
    """回傳 PyPI 最新穩定版本；查不到時回傳 None。"""
    req = urllib.request.Request(
        f"https://pypi.org/pypi/{package_name}/json",
        headers={"Accept": "application/json", "User-Agent": "voxprose-dependency-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - 固定 https
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("info", {}).get("version")
    except Exception:
        return None


def is_blocked_by_upper_bound(version: str, upper: Optional[Dict[str, str]]) -> bool:
    """version 是否被 requirements 的版本上限排除。"""
    if not upper:
        return False
    candidate = parse_version(version)
    ceiling = parse_version(upper["version"])
    if upper["operator"] == "<":
        return candidate >= ceiling
    return candidate > ceiling


def load_deferrals(path: Path = DEFERRALS_PATH) -> "Dict[str, Dict[str, str]]":
    """讀取已核准的暫緩清單；檔案不存在或格式壞掉時一律視為沒有暫緩。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {normalize_package_name(name): entry for name, entry in data.items()}


def deferred_reason(
    name: str, latest: Optional[str], deferrals: "Dict[str, Dict[str, str]]"
) -> Optional[str]:
    """暫緩只對「當初判斷的那個版本」有效。

    上游一發更新的版本，deferredLatest 就對不上，這一列會重新浮出來要求再看一次——
    這正是暫緩與「永久忽略」的差別。
    """
    entry = deferrals.get(normalize_package_name(name))
    if not isinstance(entry, dict):
        return None
    reason = entry.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        return None
    if entry.get("deferredLatest") != latest:
        return None
    return reason


def collect_status(
    packages: "Dict[str, Dict[str, object]]",
) -> "List[Dict[str, object]]":
    """收集 repo 宣告範圍、PyPI 最新版與維護狀態。"""
    deferrals = load_deferrals()
    rows = []
    for package in packages.values():
        minimum = str(package["minimum"])
        latest = fetch_pypi_version(str(package["name"]))
        check_failed = not minimum or latest is None
        baseline_behind = bool(minimum and latest and is_newer_version(latest, minimum))
        blocked = bool(latest and is_blocked_by_upper_bound(latest, package.get("upper")))
        deferred = deferred_reason(str(package["name"]), latest, deferrals)
        # 有核准暫緩就不再要求注意，但 blocked_by_upper 保留原值：報告要看得出
        # 這一列本來就超出上限，只是已經判斷過。
        needs_attention = bool((blocked and deferred is None) or check_failed)
        rows.append(
            {
                **package,
                "latest": latest or "unknown",
                "baseline_behind": baseline_behind,
                "blocked_by_upper": blocked,
                "check_failed": check_failed,
                "deferred_reason": deferred,
                "needs_attention": needs_attention,
            }
        )
    return rows


def render_markdown(rows: "List[Dict[str, object]]") -> str:
    """輸出 GitHub issue 與 Actions summary 可讀的 Markdown。"""
    lines = [
        "# VoxProse 依賴新鮮度檢查",
        "",
        "| 套件 | Repo 宣告範圍 | PyPI 最新 | 狀態 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        if row["check_failed"]:
            status = "檢查失敗"
        elif row.get("deferred_reason"):
            status = f"已核准暫緩：{row['deferred_reason']}"
        elif row["blocked_by_upper"]:
            status = "有新版主線，需評估相容性"
        elif row["baseline_behind"]:
            status = "最新版未超出版本範圍"
        else:
            status = "OK"
        files = "、".join(f"`{name}`" for name in row["files"])
        lines.append(
            f"| `{row['name']}` | `{row['requirement']}`（{files}） "
            f"| `{row['latest']}` | {status} |"
        )
    lines.extend(
        [
            "",
            "本報告只比較 repo 宣告與 PyPI，不使用 runner 或維護者電腦目前安裝的版本，",
            "因此每次執行結果可重現。最新版未超出版本上限時，pip 仍會依 Python 版本與",
            "wheel 可用性解析相容版本；不需僅因最低支援版較舊而開啟維護 issue。",
            "版本上限外的新主線才表示「需要評估」，不代表可以直接升級。",
            "",
            "標為「已核准暫緩」的列是判斷過、暫時不動的，理由與當初判斷的版本記在",
            "`.github/dependency-deferrals.json`。上游一發更新的版本，暫緩就失效、",
            "該列會重新浮出來要求再看一次。",
            "",
            "## 處理流程",
            "",
            "1. 查看同批 Dependabot PR、套件 changelog、Python 3.10–3.14 wheel 與 Windows 相容性。",
            "2. 執行期、PyQt6、Whisper、ONNX Runtime、CUDA 與 GitHub Actions 更新一律人工審查；",
            "   本 repo 不自動合併依賴 PR。",
            "3. 通過完整 CI；會影響錄音、STT、CUDA、UI 或打包鏈時，再完成對應 Windows",
            "   實機／Release 驗證後合併。",
            "4. 最新版均在 repo 允許範圍內且沒有 open Dependabot PR 時，排程會自動關閉維護 issue。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_github_output(
    baseline_behind: bool,
    blocked_by_upper: bool,
    check_failed: bool,
    report_path: Path,
) -> None:
    """寫入 GitHub Actions output。"""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as output:
        output.write(f"baseline_behind={'true' if baseline_behind else 'false'}\n")
        output.write(f"blocked_by_upper={'true' if blocked_by_upper else 'false'}\n")
        output.write(f"check_failed={'true' if check_failed else 'false'}\n")
        output.write(
            f"needs_attention={'true' if blocked_by_upper or check_failed else 'false'}\n"
        )
        output.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "檢查 VoxProse requirements-win.txt / requirements-cuda-win.txt "
            "是否仍涵蓋 PyPI 最新版"
        )
    )
    parser.add_argument(
        "--output",
        default="dependency-freshness-report.md",
        help="Markdown 報告輸出路徑",
    )
    parser.add_argument(
        "--github-output",
        action="store_true",
        help="同時寫入 GitHub Actions output",
    )
    args = parser.parse_args()

    packages = parse_requirements(REQUIREMENTS_FILES)
    if not packages:
        print("[WARN] 未解析到任何依賴套件，requirements 檔案是否存在？", file=sys.stderr)

    rows = collect_status(packages)
    report = render_markdown(rows)
    output_path = Path(args.output)
    output_path.write_text(report, encoding="utf-8")
    print(report)

    baseline_behind = any(bool(row["baseline_behind"]) for row in rows)
    blocked_by_upper = any(
        bool(row["blocked_by_upper"]) and not row.get("deferred_reason") for row in rows
    )
    check_failed = not rows or any(bool(row["check_failed"]) for row in rows)
    if args.github_output:
        write_github_output(
            baseline_behind,
            blocked_by_upper,
            check_failed,
            output_path,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
