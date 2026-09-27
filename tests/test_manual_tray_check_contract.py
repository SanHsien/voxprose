"""Windows tray 實機驗證器的 source guard 與可見選單契約。"""

from pathlib import Path


SCRIPT = Path(__file__).parent / "manual" / "manual_tray_windows_check.py"


def test_manual_tray_check_uses_release_modules_and_visible_menu_path():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "VOXPROSE_SOURCE_ROOT" in source
    assert "module_path != expected_path" in source
    assert 'parser.add_argument("--target", choices=TARGETS, required=True)' in source
    assert 'tray.toolTip() != "聲成文"' in source
    assert "tray.icon().isNull()" in source
    assert "menu.popup(QCursor.pos())" in source
    assert "QTimer.singleShot(400, trigger_action)" in source
    assert "actions[action_label].trigger()" in source
    assert source.index("menu.popup(QCursor.pos())") < source.index(
        "actions[action_label].trigger()"
    )
    assert "def cleanup() -> None:" in source
    assert "def fail_check(phase: str, exc: Exception) -> None:" in source
    assert "except Exception as exc:" in source
    assert 'result["exit_code"] = 0' in source
    assert 'return result["exit_code"]' in source
