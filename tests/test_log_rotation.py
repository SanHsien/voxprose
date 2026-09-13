"""測試 utils/log_rotation.py：debug.log／worker_debug.log 無限增長加固
（2026-07-23 隱私與加固任務第 2 項）。

驗證重點：
1. `make_rotating_file_handler()` 回傳的是真正的 `RotatingFileHandler`，
   且 maxBytes/backupCount 套用預期預設值（5MB×2）。
2. 實際寫入超過 maxBytes 後真的會觸發輪替（產生 `.1` 備份檔），不是
   「看起來設定了但從未觸發」的假輪替。
3. `main.py`／`stt/subprocess_whisper.py` 都改用這個共用函式，而非各自
   殘留的 `logging.FileHandler`／`basicConfig(filename=...)` 附加寫入。
"""
import logging
import logging.handlers
import re
from pathlib import Path

from utils.log_rotation import (
    DEFAULT_BACKUP_COUNT,
    DEFAULT_MAX_BYTES,
    make_rotating_file_handler,
)


def test_returns_rotating_file_handler_with_default_limits(tmp_path):
    handler = make_rotating_file_handler(tmp_path / "debug.log")
    try:
        assert isinstance(handler, logging.handlers.RotatingFileHandler)
        assert handler.maxBytes == DEFAULT_MAX_BYTES == 5 * 1024 * 1024
        assert handler.backupCount == DEFAULT_BACKUP_COUNT == 2
    finally:
        handler.close()


def test_custom_limits_are_respected(tmp_path):
    handler = make_rotating_file_handler(
        tmp_path / "custom.log", max_bytes=1000, backup_count=5
    )
    try:
        assert handler.maxBytes == 1000
        assert handler.backupCount == 5
    finally:
        handler.close()


def test_rotation_actually_triggers_when_size_exceeded(tmp_path):
    """核心驗證：不是只設了數字，實際寫爆之後真的會產生輪替備份檔。"""
    log_path = tmp_path / "rotating.log"
    # 故意設一個很小的 maxBytes，讓輪替快速觸發
    handler = make_rotating_file_handler(log_path, max_bytes=200, backup_count=2)
    logger = logging.getLogger("test_log_rotation_trigger")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    try:
        for i in range(200):
            logger.info(f"line {i} " + "x" * 20)
    finally:
        logger.removeHandler(handler)
        handler.close()

    assert log_path.exists()
    # 輪替後主檔案應該遠小於「若從不輪替」所需累積的總量
    backups = list(tmp_path.glob("rotating.log.*"))
    assert backups, "寫入量遠超過 maxBytes 卻沒有任何 .1/.2 備份檔，輪替沒有真的觸發"
    # 主檔＋所有備份檔加總都不該無限增長：每個檔案大小都應該在 maxBytes 附近
    for p in [log_path, *backups]:
        assert p.stat().st_size < 200 * 3  # 容許單筆訊息跨界，但不應該是全部 200 行的總量


def test_main_py_uses_shared_rotating_handler_not_bare_filehandler():
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    src = main_py.read_text(encoding="utf-8")
    assert "make_rotating_file_handler" in src
    assert "logging.FileHandler(str(log_path)" not in src


def test_subprocess_whisper_uses_shared_rotating_handler_not_basicconfig_filename():
    worker_py = (
        Path(__file__).resolve().parent.parent / "stt" / "subprocess_whisper.py"
    )
    src = worker_py.read_text(encoding="utf-8")
    assert "make_rotating_file_handler" in src
    assert not re.search(r"basicConfig\(\s*filename=", src)
