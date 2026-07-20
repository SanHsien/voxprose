"""Manual check: print the nativeVirtualKey/nativeModifiers PyQt6 reports for
a synthetic key press, on the machine's actual keyboard/OS. Needs a
displayable window environment (RDP/local desktop) — this is NOT collected by
pytest (file name intentionally does not match the `test_*.py` pattern; see
`pyproject.toml`'s `[tool.pytest.ini_options]`), and it never exits cleanly
under a pure headless CI runner.

Recovered from commit 51094bf (`git show 51094bf:test_qkey.py`, formerly
`voicetype/test_qkey.py` before the Windows-purification cleanup in v3.0.0).
Kept here per AGENTS.md/SKILL.md as a reference tool for hotkey/listener.py
work — `hotkey/listener.py` on Windows uses `ctypes.windll.user32` polling
rather than PyQt6 key events, but this script is still useful when debugging
how Qt reports native virtual-key codes for a given physical key, e.g. when
diagnosing the documented Right-Alt / alt_gr keyboard-locale mismatch in
`windows_cuda_qt_crash_postmortem.md`.

Run manually:
    python tests\\manual\\manual_qkey_check.py
"""
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication, QWidget


class Tester(QWidget):
    def keyPressEvent(self, event: QKeyEvent):
        try:
            print("nativeVirtualKey:", event.nativeVirtualKey())
            print("nativeModifiers:", event.nativeModifiers())
        except Exception as e:
            print("Error:", e)
        sys.exit(0)


def main():
    app = QApplication(sys.argv)
    w = Tester()
    w.show()
    # Send a synthetic event (Key_A) so the script is runnable without
    # requiring the operator to actually press a key.
    ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, 0, 0, 0, "a", False, 1)
    QApplication.sendEvent(w, ev)


if __name__ == "__main__":
    main()
