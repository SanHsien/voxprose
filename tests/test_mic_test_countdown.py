"""Regression tests for the Settings microphone test countdown.

Regression: QA-MIC-001 — time.sleep() blocked the Qt event loop for the full
recording, making the app look hung while asking the user to speak.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import os
import sys
import time
import types

import numpy as np
import pytest


pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget  # noqa: E402

from ui.settings.general_page import GeneralPageMixin  # noqa: E402


class _Host(QWidget, GeneralPageMixin):
    pass


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _fake_sounddevice(monkeypatch, level):
    module = types.ModuleType("sounddevice")
    module.wait_calls = 0

    def rec(frames, samplerate, channels, dtype):
        assert samplerate == 16000
        assert channels == 1
        assert dtype == "float32"
        return np.full((frames, channels), level, dtype=np.float32)

    def wait():
        module.wait_calls += 1

    module.rec = rec
    module.wait = wait
    monkeypatch.setitem(sys.modules, "sounddevice", module)
    return module


def test_microphone_recording_is_nonblocking_and_reports_success(
    qapp, monkeypatch
):
    host = _Host()
    fake_sd = _fake_sounddevice(monkeypatch, 0.02)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args: messages.append(("information", args[-1])),
    )

    started = time.monotonic()
    host._run_mic_test()
    elapsed = time.monotonic() - started

    assert elapsed < 0.25
    assert host._mic_test_timer.isActive()

    host._advance_mic_test()
    host._advance_mic_test()
    host._advance_mic_test()

    assert fake_sd.wait_calls == 1
    assert host._mic_test_timer is None
    assert host._mic_test_recording is None
    assert messages and messages[0][0] == "information"
    assert "麥克風運作正常" in messages[0][1]


def test_microphone_silence_is_reported_as_failure(qapp, monkeypatch):
    host = _Host()
    _fake_sounddevice(monkeypatch, 0.0)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args: QMessageBox.StandardButton.Yes,
    )
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: messages.append(args[-1]),
    )

    host._run_mic_test()
    host._finish_mic_test()

    assert messages
    assert "完全靜音" in messages[0]
