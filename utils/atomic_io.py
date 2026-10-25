"""JSON 檔的原子寫入：先寫同目錄暫存檔、fsync，再 os.replace 換上去。

直接 `open(path, "w")` 在寫到一半被中斷（斷電、程序被砍、磁碟滿）時會留下被截斷
的 JSON，載入端再退回預設值，使用者的設定／記憶／統計就無聲歸零。換檔是原子的，
讀取端永遠只會看到完整的舊檔或完整的新檔。
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


_REPLACE_ATTEMPTS = 10
_REPLACE_DELAY_SEC = 0.05


def _replace_with_retry(tmp: Path, path: Path, data, indent: int) -> None:
    """Windows 上目標檔被別的程序（雲端同步、防毒、索引）以不含 FILE_SHARE_DELETE 的
    方式開著時，os.replace 會丟 PermissionError，而直接覆寫反而成功。先短暫重試；
    仍不行就退回直接覆寫（等同改動前的行為），不讓寫入因此失敗。"""
    for attempt in range(_REPLACE_ATTEMPTS):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt < _REPLACE_ATTEMPTS - 1:
                time.sleep(_REPLACE_DELAY_SEC)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    try:
        tmp.unlink()
    except OSError:
        pass


def write_json_atomic(path, data, *, indent: int = 2) -> None:
    path = Path(path)
    # 暫存檔名帶 pid 與 thread id：stats／memory 會從多個執行緒寫，不能共用同一個暫存檔。
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        _replace_with_retry(tmp, path, data, indent)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
