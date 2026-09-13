"""共用的日誌輪替設定。

2026-07-23（隱私與加固任務）：`debug.log`／`worker_debug.log` 過去用
`logging.FileHandler`／`logging.basicConfig(filename=...)` 附加模式寫入，
沒有任何大小上限或輪替機制——長期執行（尤其是常駐背景程式）會讓這兩個檔案
無限增長。這裡抽出一個共用的 `RotatingFileHandler` 建構函式，讓
`main.py`（debug.log）與 `stt/subprocess_whisper.py`（worker_debug.log）
共用同一套上限設定，避免各自硬編不同數字。

上限值判斷：單檔 5MB、保留 2 個備份（共最多 15MB／log），足夠涵蓋單次錄音
工作階段的除錯需求，又不會在長期執行下無限占用磁碟。此數字為工程判斷，
非上游規格；如需調整見 `docs/DECISIONS.md`。
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Union

# 單檔大小上限與備份數（見上方 docstring 的判斷理由）
DEFAULT_MAX_BYTES = 5 * 1024 * 1024  # 5MB
DEFAULT_BACKUP_COUNT = 2


def make_rotating_file_handler(
    path: Union[str, Path],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    encoding: str = "utf-8",
) -> logging.handlers.RotatingFileHandler:
    """建立一個標準設定的 `RotatingFileHandler`。

    純粹是 `logging.handlers.RotatingFileHandler(...)` 的一層薄包裝，
    存在的理由是讓呼叫端不用各自記住/硬編 maxBytes、backupCount 的數值，
    且方便測試 mock（一個函式，兩處呼叫）。
    """
    return logging.handlers.RotatingFileHandler(
        str(path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding=encoding,
    )
