import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QKeyEvent

class Tester(QWidget):
    def keyPressEvent(self, event: QKeyEvent):
        try:
            print("nativeVirtualKey:", event.nativeVirtualKey())
            print("nativeModifiers:", event.nativeModifiers())
        except Exception as e:
            print("Error:", e)
        sys.exit(0)

app = QApplication(sys.argv)
w = Tester()
w.show()
# Send a synthetic event
from PyQt6.QtCore import Qt
ev = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier, 0, 0, 0, "a", False, 1)
QApplication.sendEvent(w, ev)
