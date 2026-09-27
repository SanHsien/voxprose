"""Regression tests for Windows QSystemTrayIcon lifecycle and callbacks.

Regression: QA-TRAY-001 — loop callbacks captured the final QAction, and stop()
called a QSystemTrayIcon method that does not exist.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import os

import pytest


pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QIcon  # noqa: E402
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon  # noqa: E402

from ui.tray_manager import TrayManager  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_each_menu_callback_receives_its_own_action(qapp):
    received = []
    tray = TrayManager(
        "聲成文",
        "",
        [
            {"label": "第一個", "callback": lambda action: received.append(action.text())},
            {"label": "第二個", "callback": lambda action: received.append(action.text())},
        ],
    )

    menu = tray._build_qt_menu(tray.menu_items)
    actions = menu.actions()
    actions[0].trigger()
    actions[1].trigger()

    assert received == ["第一個", "第二個"]


def test_stop_hides_and_releases_qsystemtrayicon(qapp):
    tray = TrayManager("聲成文", "", [])
    tray._tray = QSystemTrayIcon(QIcon(), qapp)
    tray._qt_menu = tray._build_qt_menu([])
    tray._tray.show()
    qapp.processEvents()

    tray.stop()
    qapp.processEvents()

    assert tray._tray is None
    assert tray._qt_menu is None
