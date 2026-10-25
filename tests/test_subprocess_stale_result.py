"""逾時的上一輪辨識結果不能被下一輪當成自己的答案。

Regression: SubprocessWhisperSTT.transcribe 逾時（30 秒）就丟例外，但 worker 之後
仍會把那一輪的結果放進 _result_queue；下一次 transcribe 一送出就從佇列拿到那份
過期結果，把「上一段話」貼到現在的輸入框，而這一段的真正結果又留在佇列裡錯位下去。
"""
import queue
import threading
from types import SimpleNamespace

from stt import subprocess_whisper


def _make_stt(on_send):
    stt = object.__new__(subprocess_whisper.SubprocessWhisperSTT)
    stt._lock = threading.Lock()
    stt._ready_status = True
    stt._result_queue = queue.Queue()
    stt.worker_process = SimpleNamespace(is_alive=lambda: True)
    stt._parent_conn = SimpleNamespace(send=lambda msg: on_send(stt, msg))
    return stt


def test_stale_result_from_a_timed_out_request_is_discarded(monkeypatch):
    import vocab.manager

    monkeypatch.setattr(vocab.manager, "build_vocab_prompt", lambda: "p")

    def worker_replies(stt, msg):
        stt._result_queue.put({"type": "result", "text": "這一段的結果"})

    stt = _make_stt(worker_replies)
    # 上一輪逾時後才抵達的過期結果
    stt._result_queue.put({"type": "result", "text": "上一段的過期結果"})

    assert stt.transcribe(b"\x00" * 200, language="zh") == "這一段的結果"
    assert stt._result_queue.empty()
