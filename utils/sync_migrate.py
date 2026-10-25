"""把本機資料搬進同步目錄（ui/settings/sync_page.py 的遷移步驟）。

抽成純函式以便測試。核心防護：目的地與來源是同一個目錄、或互為子／父目錄時
一律跳過——舊寫法先 rmtree(目的地) 再 copytree，會在此情況把來源資料先刪光。
"""
from __future__ import annotations

import shutil
from pathlib import Path

FOLDERS_TO_SYNC = ("soul", "vocab", "memory", "stats")
FILES_TO_SYNC = ("ai_permanent_memory.md",)


def _overlaps(a: Path, b: Path) -> bool:
    a, b = a.resolve(), b.resolve()
    return a == b or a in b.parents or b in a.parents


def migrate_to_sync(app_data_dir: Path, target_base: Path) -> None:
    app_data_dir, target_base = Path(app_data_dir), Path(target_base)
    for folder in FOLDERS_TO_SYNC:
        src = app_data_dir / folder
        dst = target_base / folder
        if not src.exists():
            continue
        if _overlaps(src, dst):
            print(f"[Sync] Skip migrating {folder}: destination overlaps the source ({dst})")
            continue
        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        except Exception as e:
            print(f"[Sync] Error migrating folder {folder}: {e}")

    for filename in FILES_TO_SYNC:
        src = app_data_dir / filename
        dst = target_base / filename
        if not src.exists():
            continue
        if _overlaps(src, dst):
            continue
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"[Sync] Error migrating file {filename}: {e}")
