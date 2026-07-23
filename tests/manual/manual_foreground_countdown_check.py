"""Windows 實機驗證：Qt 三秒倒數後取得真正的前景程式。

執行後看到 ``[READY]``，請在三秒內切到目標程式。腳本會走設定頁實際使用的
``SoulPageMixin._detect_foreground_app_for_rule()``，但把結果訊息盒改成 stdout，
避免無人值守驗證被 modal dialog 卡住。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QVBoxLayout, QWidget


SOURCE_OVERRIDE = os.environ.get("VOXPROSE_SOURCE_ROOT")
ROOT = Path(SOURCE_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
EXPECTED_MODULES = (
    ROOT / "ui" / "settings" / "soul_page.py",
    ROOT / "utils" / "foreground.py",
)
if SOURCE_OVERRIDE:
    for expected_module in EXPECTED_MODULES:
        if not expected_module.is_file():
            raise RuntimeError(
                f"VOXPROSE_SOURCE_ROOT 未包含預期模組：{expected_module}"
            )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.settings.soul_page as soul_page_module
import utils.foreground as foreground_module
from ui.settings.common import CommonPageMixin


IMPORTED_MODULES = {
    "soul_page": Path(soul_page_module.__file__).resolve(),
    "foreground": Path(foreground_module.__file__).resolve(),
}
for module_name, module_path in IMPORTED_MODULES.items():
    try:
        module_path.relative_to(ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"{module_name} 模組來源不在指定 root 內：{module_path}"
        ) from exc


class _Host(QWidget, CommonPageMixin, soul_page_module.SoulPageMixin):
    def __init__(self):
        super().__init__()
        self.config = {
            "auto_scenario_enabled": False,
            "auto_scenario_rules": {},
        }
        layout = QVBoxLayout(self)
        layout.addWidget(self._create_auto_scenario_section())


def main() -> int:
    expected = os.environ.get("VOXPROSE_EXPECT_FOREGROUND", "").strip()
    if not expected:
        raise RuntimeError("請設定 VOXPROSE_EXPECT_FOREGROUND（例如 LINE.exe）")
    arm_value = os.environ.get("VOXPROSE_FOREGROUND_ARM_FILE", "").strip()
    arm_file = Path(arm_value).resolve() if arm_value else None

    print(f"[INFO] Source root: {ROOT}", flush=True)
    for module_name, module_path in IMPORTED_MODULES.items():
        print(f"[INFO] {module_name} module: {module_path}", flush=True)

    app = QApplication.instance() or QApplication(sys.argv)
    host = _Host()
    result = {"exit_code": 1}
    messages = []

    def capture_message(_parent, title, text):
        messages.append((title, text))
        print(f"[MESSAGE] {title}: {text}", flush=True)
        return QMessageBox.StandardButton.Ok

    QMessageBox.information = capture_message
    QMessageBox.warning = capture_message

    def begin_countdown():
        host.show()
        host.raise_()
        host.activateWindow()
        host._detect_foreground_app_for_rule()
        print(
            f"[READY] 請在三秒內切到目標程式：{expected}",
            flush=True,
        )
        QTimer.singleShot(4000, finish)

    def wait_for_arm():
        if arm_file is not None and not arm_file.exists():
            QTimer.singleShot(100, wait_for_arm)
            return
        begin_countdown()

    if arm_file is not None:
        print(f"[WAITING] Arm file: {arm_file}", flush=True)

    def finish():
        rules = host._collect_auto_scenario_rules()
        detected = next(iter(rules), "")
        if detected.casefold() == expected.casefold():
            print(f"[PASS] Foreground process: {detected}", flush=True)
            result["exit_code"] = 0
        else:
            print(
                f"[FAIL] Expected {expected}, detected {detected or '<none>'}; "
                f"messages={messages}",
                flush=True,
            )
        progress = getattr(host, "_foreground_detection_progress", None)
        if progress is not None:
            progress.close()
        host.close()
        app.quit()

    QTimer.singleShot(0, wait_for_arm)
    app.exec()
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
