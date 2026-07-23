import threading
import time
from inspect import signature
from queue import Queue

import pytest

from stt.subprocess_whisper import SubprocessWhisperSTT


class _FakeConnection:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


class _AliveWorker:
    @staticmethod
    def is_alive():
        return True


class _MessageConnection:
    def __init__(self, message):
        self.message = message
        self.received = False
        self.stop_event = None

    def poll(self, _timeout):
        if self.received:
            raise EOFError
        return True

    def recv(self):
        if self.received:
            raise EOFError
        self.received = True
        if self.stop_event is not None:
            self.stop_event.set()
        return self.message


class _ClosedConnection:
    @staticmethod
    def poll(_timeout):
        raise EOFError


def _make_stt():
    stt = SubprocessWhisperSTT.__new__(SubprocessWhisperSTT)
    stt._lock = threading.Lock()
    stt._parent_conn = _FakeConnection()
    stt._warmup_done = threading.Event()
    stt._warmup_error = None
    stt._ready_status = False
    stt.worker_process = _AliveWorker()
    return stt


def test_warmup_waits_for_worker_completion():
    stt = _make_stt()
    outcome = []

    thread = threading.Thread(target=lambda: outcome.append(stt.warmup(timeout=1)))
    thread.start()

    deadline = time.monotonic() + 0.5
    while not stt._parent_conn.sent and time.monotonic() < deadline:
        time.sleep(0.01)

    assert stt._parent_conn.sent == [{"type": "warmup"}]
    assert thread.is_alive(), "warmup() returned before worker completion"

    stt._ready_status = True
    stt._warmup_done.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert outcome == [True]


def test_warmup_raises_worker_error():
    stt = _make_stt()
    errors = []

    def run_warmup():
        try:
            stt.warmup(timeout=1)
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_warmup)
    thread.start()

    deadline = time.monotonic() + 0.5
    while not stt._parent_conn.sent and time.monotonic() < deadline:
        time.sleep(0.01)

    stt._warmup_error = "dummy transcription failed"
    stt._warmup_done.set()
    thread.join(timeout=1)

    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)
    assert "dummy transcription failed" in str(errors[0])


def test_warmup_times_out_instead_of_marking_ready():
    stt = _make_stt()
    stt._ready_status = True

    with pytest.raises(TimeoutError, match="timed out"):
        stt.warmup(timeout=0.01)
    assert stt.is_ready is False


def test_warmup_has_no_default_absolute_timeout_for_first_model_download():
    parameter = signature(SubprocessWhisperSTT.warmup).parameters["timeout"]

    assert parameter.default is None


@pytest.mark.parametrize(
    ("message", "expected_error"),
    [
        ({"type": "warmup_done", "success": True}, None),
        (
            {
                "type": "warmup_done",
                "success": False,
                "error": "dummy inference failed",
            },
            "dummy inference failed",
        ),
    ],
)
def test_pipe_reader_records_warmup_result(message, expected_error):
    stt = _make_stt()
    stt._ready_status = True
    stt._parent_conn = _MessageConnection(message)
    stt._stop_reader = threading.Event()
    stt._parent_conn.stop_event = stt._stop_reader
    stt._result_queue = Queue()

    stt._pipe_reader()

    assert stt._warmup_done.is_set()
    assert stt._warmup_error == expected_error
    assert stt.is_ready is (expected_error is None)


def test_pipe_reader_unblocks_warmup_when_connection_closes():
    stt = _make_stt()
    stt._ready_status = True
    stt._parent_conn = _ClosedConnection()
    stt._stop_reader = threading.Event()
    stt._result_queue = Queue()

    stt._pipe_reader()

    assert stt._warmup_done.is_set()
    assert stt._warmup_error == "STT worker connection closed"
    assert stt.is_ready is False


def test_pipe_reader_clears_ready_when_connection_closes_after_warmup():
    stt = _make_stt()
    stt._ready_status = True
    stt._warmup_done.set()
    stt._parent_conn = _ClosedConnection()
    stt._stop_reader = threading.Event()
    stt._result_queue = Queue()

    stt._pipe_reader()

    assert stt.is_ready is False
    assert stt._warmup_error is None
