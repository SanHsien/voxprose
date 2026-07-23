"""Windows 實機驗證：STT warmup 必須等 worker 真正完成後才返回。"""

import multiprocessing
import os
import sys
import time
from pathlib import Path


SOURCE_OVERRIDE = os.environ.get("VOXPROSE_SOURCE_ROOT")
ROOT = Path(SOURCE_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
EXPECTED_MODULE = ROOT / "stt" / "subprocess_whisper.py"
if SOURCE_OVERRIDE and not EXPECTED_MODULE.is_file():
    raise RuntimeError(
        f"VOXPROSE_SOURCE_ROOT 未包含預期模組：{EXPECTED_MODULE}"
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import stt.subprocess_whisper as subprocess_whisper_module

IMPORTED_MODULE = Path(subprocess_whisper_module.__file__).resolve()
try:
    IMPORTED_MODULE.relative_to(ROOT)
except ValueError as exc:
    raise RuntimeError(
        f"STT 模組來源不在指定 root 內：{IMPORTED_MODULE}"
    ) from exc

SubprocessWhisperSTT = subprocess_whisper_module.SubprocessWhisperSTT


def main() -> int:
    print(f"[INFO] Source root: {ROOT}")
    print(f"[INFO] STT module: {IMPORTED_MODULE}")
    stt = SubprocessWhisperSTT(
        {
            "stt_engine": "local_whisper",
            "whisper_model": "tiny",
            "whisper_device": "cpu",
            "whisper_compute_type": "int8",
        }
    )
    started = time.monotonic()
    try:
        stt.warmup(timeout=120)
        elapsed = time.monotonic() - started
        if not stt.is_ready:
            raise RuntimeError("warmup returned but worker is not ready")
        print(f"[PASS] STT warmup completed in {elapsed:.2f}s; ready=True")
        return 0
    finally:
        del stt


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
