#!/usr/bin/env python3
"""檢查 VoiceType4TW 依賴（requirements-win.txt / requirements-cuda-win.txt）是否落後。

此工具供 GitHub Actions 排程與本地維護使用；它只檢查版本並輸出報告，
不會自行升級套件或建立 Release。比照 yt_fetch 專案的
tools/check_dependency_freshness.py 改寫，改為解析本 repo 的兩份
requirements 檔案（而非固定套件清單），並用 PyPI JSON API 比對最新版。
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from importlib import metadata
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent

REQUIREMENTS_FILES = (
    ROOT / "requirements-win.txt",
    ROOT / "requirements-cuda-win.txt",
)

# `name>=1.2.3`、`name==1.2.3`、`name~=1.2` 之類的宣告；忽略註解與空行。
_REQ_LINE_RE = re.compile(
    r"^([A-Za-z0-9_.\-]+)\s*(?:(>=|==|~=|>)\s*([0-9][0-9A-Za-z.\-]*))?"
)


def parse_requirements(paths: Iterable[Path]) -> "Dict[str, str]":
    """解析 requirements 檔案，回傳 {套件名稱: 宣告的最低版本（可能是空字串）}。"""
    packages: Dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            match = _REQ_LINE_RE.match(line)
            if not match:
                continue
            name = match.group(1)
            version = match.group(3) or ""
            packages[name] = version
    return packages


def parse_version(text: str) -> tuple:
    """把版本字串（可帶前綴 v）轉成可比較的整數 tuple，例如 'v1.2.0' -> (1, 2, 0)。"""
    text = (text or "").strip().lstrip("vV")
    parts = []
    for piece in text.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str) -> bool:
    """latest 是否比 current 新（語義化版本比較）。"""
    return parse_version(latest) > parse_version(current)


def fetch_pypi_version(package_name: str, timeout: float = 10.0) -> Optional[str]:
    """回傳 PyPI 最新版本；查不到時回傳 None。"""
    req = urllib.request.Request(
        f"https://pypi.org/pypi/{package_name}/json",
        headers={"Accept": "application/json", "User-Agent": "voicetype-dependency-check"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - 固定 https
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("info", {}).get("version")
    except Exception:
        return None


def installed_version(package_name: str) -> Optional[str]:
    """回傳目前環境安裝版本；未安裝時回傳 None。"""
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def collect_status(packages: "Dict[str, str]") -> "List[Dict[str, object]]":
    """收集每個套件的目前版本（優先用實際安裝版本，其次用 requirements 宣告的最低版本）、
    PyPI 最新版本，以及是否落後。"""
    rows = []
    for package_name, declared_min in packages.items():
        installed = installed_version(package_name)
        current = installed or declared_min or None
        source = "installed" if installed else "requirements-min"
        latest = fetch_pypi_version(package_name)
        outdated = bool(current and latest and is_newer_version(latest, current))
        rows.append(
            {
                "name": package_name,
                "current": current or "unknown",
                "source": source,
                "latest": latest or "unknown",
                "outdated": outdated,
            }
        )
    return rows


def render_markdown(rows: "List[Dict[str, object]]") -> str:
    """輸出 GitHub issue / log 可讀的 Markdown。"""
    lines = [
        "# VoiceType4TW 依賴新鮮度檢查",
        "",
        "| 套件 | 目前版本（來源） | PyPI 最新 | 狀態 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        status = "需要維護" if row["outdated"] else "OK"
        lines.append(
            f"| `{row['name']}` | `{row['current']}`（{row['source']}） "
            f"| `{row['latest']}` | {status} |"
        )
    lines.extend(
        [
            "",
            "「目前版本」優先取自目前 Python 環境已安裝的版本；若未安裝，"
            "退回 requirements-win.txt / requirements-cuda-win.txt 宣告的最低版本"
            "（`requirements-min`）。",
            "",
            "若核心依賴（PyQt6、faster-whisper、nvidia-cublas-cu12/nvidia-cudnn-cu12 等）落後，"
            "建議確認測試後更新 requirements 檔案下限、重新驗證，再切新版 tag 讓 "
            "release workflow 重新打包可攜版。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_github_output(outdated: bool, report_path: Path) -> None:
    """寫入 GitHub Actions output。"""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"outdated={'true' if outdated else 'false'}\n")
        f.write(f"report_path={report_path.as_posix()}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="檢查 VoiceType4TW requirements-win.txt / requirements-cuda-win.txt 是否落後"
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

    outdated = any(bool(row["outdated"]) for row in rows)
    if args.github_output:
        write_github_output(outdated, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
