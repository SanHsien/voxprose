"""驗證 Windows 可攜版 ZIP 的檔名與必要中文資源。

GitHub runner 是英文 Windows；若壓縮工具把檔名送進系統 ANSI code page，
中文會在打包當下變成 literal ``?``。本工具在 Release 上傳前檢查中央目錄，
避免再次發佈無法由 Windows 內建工具解壓的產物。
"""

from __future__ import annotations

import sys
import zipfile
from collections import Counter
from pathlib import Path


REQUIRED_SUFFIXES = {
    "可攜版說明.txt",
    "啟動聲成文.bat",
    "安裝下載教學.MD",
    "soul/scenario/社群貼文.md",
    "soul/scenario/商務回應.md",
    "soul/scenario/情商大師.md",
    "soul/scenario/逐字稿.md",
}


def _display_names(names: list[str]) -> str:
    """用純 ASCII escape 顯示 ZIP entry，避免本機主控台二次編碼失敗。"""
    return "[" + ", ".join(ascii(name) for name in names) + "]"


def validate_release_zip(path: Path) -> list[str]:
    """回傳驗證錯誤；空 list 代表通過。"""
    errors: list[str] = []
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            corrupt_entry = archive.testzip()
    except (OSError, zipfile.BadZipFile) as exc:
        return [f"無法讀取 ZIP：{exc}"]

    names = [entry.filename for entry in entries]
    duplicates = sorted(
        name for name, count in Counter(names).items() if count > 1
    )
    if duplicates:
        errors.append(f"發現重複 entry：{_display_names(duplicates)}")

    invalid = sorted(
        name for name in names if "?" in name or "\ufffd" in name
    )
    if invalid:
        errors.append(f"發現非法或已損壞檔名：{_display_names(invalid)}")

    for suffix in sorted(REQUIRED_SUFFIXES):
        matches = [name for name in names if name.endswith("/" + suffix)]
        if len(matches) != 1:
            errors.append(f"必要檔案 {suffix!r} 應恰好出現一次，實際 {len(matches)} 次")

    non_ascii_without_utf8 = sorted(
        entry.filename
        for entry in entries
        if any(ord(char) > 127 for char in entry.filename)
        and not (entry.flag_bits & 0x800)
    )
    if non_ascii_without_utf8:
        errors.append(
            "下列非 ASCII entry 未設定 ZIP UTF-8 flag："
            f"{_display_names(non_ascii_without_utf8)}"
        )

    if corrupt_entry is not None:
        errors.append(f"CRC 驗證失敗：{ascii(corrupt_entry)}")

    return errors


def main(argv: list[str]) -> int:
    if not argv:
        print("用法：python tools/verify_release_zip.py <zip> [<zip> ...]", file=sys.stderr)
        return 2

    failed = False
    for raw_path in argv:
        path = Path(raw_path)
        errors = validate_release_zip(path)
        if errors:
            failed = True
            print(f"[FAIL] {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[PASS] {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
