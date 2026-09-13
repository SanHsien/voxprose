"""Windows 實機驗證：系統匣 live state 與可見選單 callback。

PyQt 6.11 在 Windows 上若把已掛到 QSystemTrayIcon、但尚未顯示的 context
menu 直接 ``QAction.trigger()``，QA 程序可能 native fail-fast；那不是使用者
操作路徑。本腳本會先 ``QMenu.popup()`` 顯示選單，再觸發指定 action。
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication


SOURCE_OVERRIDE = os.environ.get("VOXPROSE_SOURCE_ROOT")
ROOT = Path(SOURCE_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
EXPECTED_MODULES = {
    "app": ROOT / "ui" / "app.py",
    "tray_manager": ROOT / "ui" / "tray_manager.py",
}
if SOURCE_OVERRIDE:
    for expected_module in EXPECTED_MODULES.values():
        if not expected_module.is_file():
            raise RuntimeError(
                f"VOXPROSE_SOURCE_ROOT 未包含預期模組：{expected_module}"
            )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.app as app_module
import ui.tray_manager as tray_module


IMPORTED_MODULES = {
    "app": Path(app_module.__file__).resolve(),
    "tray_manager": Path(tray_module.__file__).resolve(),
}
for module_name, module_path in IMPORTED_MODULES.items():
    expected_path = EXPECTED_MODULES[module_name].resolve()
    if module_path != expected_path:
        raise RuntimeError(
            f"{module_name} 模組來源錯誤：{module_path}（預期 {expected_path}）"
        )


TARGETS = {
    "settings": ("聲成文 VoxProse", "settings_window"),
    "about": ("關於", "about_dialog"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=TARGETS, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    action_label, window_attr = TARGETS[args.target]
    print(f"[INFO] Source root: {ROOT}", flush=True)
    for module_name, module_path in IMPORTED_MODULES.items():
        print(f"[INFO] {module_name} module: {module_path}", flush=True)

    app = QApplication.instance() or QApplication(sys.argv)
    voice = None
    result = {"exit_code": 1}

    def cleanup() -> None:
        if voice is None:
            app.quit()
            return
        for window in (
            voice.settings_window,
            voice.menu_bar.about_dialog,
        ):
            if window is not None:
                try:
                    window.close()
                except Exception as exc:
                    print(f"[WARN] cleanup window: {exc}", flush=True)
        for label, callback in (
            ("tray", voice.tray.stop),
            ("floating button", voice.floating_btn.close),
        ):
            try:
                callback()
            except Exception as exc:
                print(f"[WARN] cleanup {label}: {exc}", flush=True)
        app.quit()

    try:
        voice = app_module.VoiceTypeApp()
        voice.tray.start()
        tray = voice.tray._tray
        if tray is None or not tray.isVisible():
            raise RuntimeError("QSystemTrayIcon 未建立或不可見")
        if tray.toolTip() != "聲成文":
            raise RuntimeError(f"系統匣 tooltip 錯誤：{tray.toolTip()!r}")
        if tray.icon().isNull():
            raise RuntimeError("系統匣 icon 為空")

        menu = tray.contextMenu()
        actions = {
            action.text(): action
            for action in menu.actions()
            if not action.isSeparator()
        }
        if action_label not in actions:
            raise RuntimeError(f"系統匣選單缺少 action：{action_label}")
    except Exception as exc:
        print(f"[FAIL] setup: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        cleanup()
        return result["exit_code"]

    print(
        "[PASS] Tray live:",
        f"visible={tray.isVisible()}",
        f"tooltip={tray.toolTip()}",
        f"icon_null={tray.icon().isNull()}",
        flush=True,
    )

    def fail_check(phase: str, exc: Exception) -> None:
        print(f"[FAIL] {phase}: {type(exc).__name__}: {exc}", flush=True)
        traceback.print_exc()
        cleanup()

    def show_menu() -> None:
        try:
            menu.popup(QCursor.pos())
            QTimer.singleShot(400, trigger_action)
        except Exception as exc:
            fail_check("show_menu", exc)

    def trigger_action() -> None:
        try:
            actions[action_label].trigger()
            QTimer.singleShot(700, verify_window)
        except Exception as exc:
            fail_check("trigger_action", exc)

    def verify_window() -> None:
        try:
            if window_attr == "settings_window":
                window = voice.settings_window
            else:
                window = voice.menu_bar.about_dialog
            if window is None or not window.isVisible():
                raise RuntimeError(f"{args.target} 視窗未出現")
            if window.isMinimized():
                raise RuntimeError(f"{args.target} 視窗仍是最小化狀態")
            print(
                "[PASS] Tray popup action:",
                f"target={args.target}",
                f"geometry={window.geometry().getRect()}",
                flush=True,
            )
            result["exit_code"] = 0
            cleanup()
        except Exception as exc:
            fail_check("verify_window", exc)

    QTimer.singleShot(0, show_menu)
    app.exec()
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
