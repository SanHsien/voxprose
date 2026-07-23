"""Windows 實機驗證：STT warmup 必須等 worker 真正完成後才返回。"""

import multiprocessing
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stt.subprocess_whisper import SubprocessWhisperSTT


def main() -> int:
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
