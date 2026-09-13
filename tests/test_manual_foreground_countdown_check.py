"""前景倒數實機驗證器的 fail-closed 契約。"""

from pathlib import Path


SCRIPT = Path(__file__).parent / "manual" / "manual_foreground_countdown_check.py"


def test_manual_foreground_check_uses_real_product_callback_and_source_guard():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "_detect_foreground_app_for_rule()" in source
    assert "VOXPROSE_EXPECT_FOREGROUND" in source
    assert "VOXPROSE_FOREGROUND_ARM_FILE" in source
    assert "module_path.relative_to(ROOT)" in source
    assert "detected.casefold() == expected.casefold()" in source
    assert "QMessageBox.information = capture_message" in source
