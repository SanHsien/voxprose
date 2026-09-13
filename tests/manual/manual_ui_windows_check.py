r"""Windows 實機驗證：主選單、設定視窗與 About 視窗可被喚回。

預設完成檢查後自動關閉。若要人工目視：

    set VOXPROSE_UI_CHECK_INTERACTIVE=1
    python tests\manual\manual_ui_windows_check.py
"""

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication


SOURCE_OVERRIDE = os.environ.get("VOXPROSE_SOURCE_ROOT")
CHECK_TARGET = os.environ.get("VOXPROSE_UI_CHECK_TARGET", "all").strip().lower()
if CHECK_TARGET not in {"all", "settings", "about"}:
    raise RuntimeError(
        "VOXPROSE_UI_CHECK_TARGET 必須是 all、settings 或 about"
    )
ROOT = Path(SOURCE_OVERRIDE or Path(__file__).resolve().parents[2]).resolve()
EXPECTED_MODULE = ROOT / "ui" / "app.py"
if SOURCE_OVERRIDE and not EXPECTED_MODULE.is_file():
    raise RuntimeError(
        f"VOXPROSE_SOURCE_ROOT 未包含預期模組：{EXPECTED_MODULE}"
    )
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui.app as app_module

IMPORTED_MODULE = Path(app_module.__file__).resolve()
try:
    IMPORTED_MODULE.relative_to(ROOT)
except ValueError as exc:
    raise RuntimeError(
        f"UI 模組來源不在指定 root 內：{IMPORTED_MODULE}"
    ) from exc

VoiceTypeApp = app_module.VoiceTypeApp


def main() -> int:
    print(f"[INFO] Source root: {ROOT}")
    print(f"[INFO] UI module: {IMPORTED_MODULE}")
    app = QApplication.instance() or QApplication(sys.argv)
    voice = VoiceTypeApp()

    def open_windows():
        if CHECK_TARGET in {"all", "settings"}:
            voice.menu_bar._open_settings()
        if CHECK_TARGET in {"all", "about"}:
            voice.menu_bar._show_about()
        QTimer.singleShot(250, verify_windows)

    def verify_windows():
        settings = voice.settings_window
        about = voice.menu_bar.about_dialog
        geometry = []
        if CHECK_TARGET in {"all", "settings"}:
            assert settings is not None and settings.isVisible()
            assert not settings.isMinimized()
            geometry.append(f"settings={settings.geometry().getRect()}")
        if CHECK_TARGET in {"all", "about"}:
            assert about is not None and about.isVisible()
            assert not about.isMinimized()
            assert about.width() >= 620 and about.height() >= 620
            geometry.append(f"about={about.geometry().getRect()}")
        print("[PASS] UI windows visible:", *geometry, flush=True)
        output_dir = os.environ.get("VOXPROSE_UI_CHECK_OUTPUT")
        if output_dir:
            destination = Path(output_dir).resolve()
            destination.mkdir(parents=True, exist_ok=True)
            screenshots = []
            if CHECK_TARGET in {"all", "settings"}:
                settings_path = destination / "settings-window.png"
                assert settings.grab().save(str(settings_path), "PNG")
                screenshots.append(str(settings_path))
            if CHECK_TARGET in {"all", "about"}:
                about_path = destination / "about-window.png"
                assert about.grab().save(str(about_path), "PNG")
                screenshots.append(str(about_path))
            print(f"[PASS] Screenshots: {' | '.join(screenshots)}", flush=True)
        if os.environ.get("VOXPROSE_UI_CHECK_INTERACTIVE") != "1":
            if about is not None:
                about.close()
            if settings is not None:
                settings.close()
            voice.floating_btn.close()
            app.quit()

    QTimer.singleShot(0, open_windows)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
