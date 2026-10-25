"""JSON 檔的原子寫入：先寫同目錄暫存檔、fsync，再 os.replace 換上去。

直接 `open(path, "w")` 在寫到一半被中斷（斷電、程序被砍、磁碟滿）時會留下被截斷
的 JSON，載入端再退回預設值，使用者的設定／記憶／統計就無聲歸零。換檔是原子的，
讀取端永遠只會看到完整的舊檔或完整的新檔。
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path


def write_json_atomic(path, data, *, indent: int = 2) -> None:
    path = Path(path)
    # 暫存檔名帶 pid 與 thread id：stats／memory 會從多個執行緒寫，不能共用同一個暫存檔。
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
