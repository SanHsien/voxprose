"""Windows UI 手動驗證器的 target 分流契約。"""

from pathlib import Path


SCRIPT = Path(__file__).parent / "manual" / "manual_ui_windows_check.py"


def test_manual_ui_check_supports_independent_window_targets():
    source = SCRIPT.read_text(encoding="utf-8")

    assert 'VOXPROSE_UI_CHECK_TARGET", "all"' in source
    assert '{"all", "settings", "about"}' in source
    assert 'CHECK_TARGET in {"all", "settings"}' in source
    assert 'CHECK_TARGET in {"all", "about"}' in source
