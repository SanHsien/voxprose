"""錄音串流開不起來時，recorder 不能卡在「錄音中」。

Regression: AudioRecorder.start() 先把 _recording 設成 True 才開 sounddevice
串流；沒有麥克風（或裝置被占用）時串流丟例外，_recording 卻維持 True。
之後 _on_toggle_test 等以 `recorder._recording` 判斷的路徑會誤以為正在錄音，
start() 也因「已在錄音」直接 return，錄音永遠起不來。
"""
import pytest

pytest.importorskip("sounddevice", reason="sounddevice not installed")

import audio.recorder as recorder_module  # noqa: E402


def test_failed_start_does_not_leave_recorder_in_recording_state(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("no input device")

    monkeypatch.setattr(recorder_module.sd, "InputStream", boom)
    rec = recorder_module.AudioRecorder()

    with pytest.raises(OSError):
        rec.start()

    assert rec._recording is False
    assert rec._stream is None


def test_failed_start_with_fallback_device_also_resets(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("still no device")

    monkeypatch.setattr(recorder_module.sd, "InputStream", boom)
    rec = recorder_module.AudioRecorder(device=3)

    with pytest.raises(OSError):
        rec.start()

    assert rec._recording is False


def test_can_start_again_after_a_failed_start(monkeypatch):
    class _Stream:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    calls = {"n": 0}

    def flaky(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("busy")
        return _Stream()

    monkeypatch.setattr(recorder_module.sd, "InputStream", flaky)
    rec = recorder_module.AudioRecorder()
    with pytest.raises(OSError):
        rec.start()
    rec.start()
    assert calls["n"] == 2  # 第二次真的重新開串流，而不是被「已在錄音」擋掉
    assert rec._recording is True
