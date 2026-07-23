"""Regression tests for the foreground-app detection countdown.

Regression: REVIEW 27-2 — time.sleep() blocked Qt, so users and UI automation
could not switch to the target app during the advertised three-second window.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import os
import time

import pytest


pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget  # noqa: E402

from ui.settings.common import CommonPageMixin  # noqa: E402
from ui.settings.soul_page import SoulPageMixin  # noqa: E402
import utils.foreground as foreground  # noqa: E402


class _Host(QWidget, CommonPageMixin, SoulPageMixin):
    def __init__(self):
        super().__init__()
        self.config = {
            "auto_scenario_enabled": False,
            "auto_scenario_rules": {},
        }
        layout = QVBoxLayout(self)
        layout.addWidget(self._create_auto_scenario_section())


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_countdown_returns_immediately_and_detects_without_modal_dialog(
    qapp, monkeypatch
):
    host = _Host()
    messages = []
    original_button_text = host.auto_scenario_detect_btn.text()

    monkeypatch.setattr(
        QMessageBox,
        "information",
        lambda *args: messages.append(("information", args[-1])),
    )
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args: messages.append(("warning", args[-1])),
    )

    def fake_foreground():
        assert host._foreground_detection_timer is not None
        assert not host.auto_scenario_detect_btn.isEnabled()
        return "notepad.exe"

    monkeypatch.setattr(foreground, "get_foreground_process_name", fake_foreground)

    started = time.monotonic()
    host._detect_foreground_app_for_rule()
    elapsed = time.monotonic() - started

    assert elapsed < 0.25
    assert host._foreground_detection_timer.isActive()
    assert not host.auto_scenario_detect_btn.isEnabled()
    assert host.auto_scenario_detect_btn.text() == "請切到目標視窗（3）"

    host._advance_foreground_detection()
    assert host.auto_scenario_detect_btn.text() == "請切到目標視窗（2）"
    host._advance_foreground_detection()
    assert host.auto_scenario_detect_btn.text() == "請切到目標視窗（1）"
    host._advance_foreground_detection()

    assert host._foreground_detection_timer is None
    assert host.auto_scenario_detect_btn.isEnabled()
    assert host.auto_scenario_detect_btn.text() == original_button_text
    assert host._collect_auto_scenario_rules() == {"notepad.exe": "default"}
    assert messages == [
        (
            "information",
            "偵測到前景程式：notepad.exe\n"
            "已新增一列規則，請從下拉選單選擇要套用的情境模板。",
        )
    ]


def test_second_click_during_countdown_does_not_start_another_timer(
    qapp, monkeypatch
):
    host = _Host()
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(foreground, "get_foreground_process_name", lambda: "line.exe")

    host._detect_foreground_app_for_rule()
    first_timer = host._foreground_detection_timer
    host._detect_foreground_app_for_rule()

    assert host._foreground_detection_timer is first_timer
    first_timer.stop()
