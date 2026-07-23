import ast
from pathlib import Path

from ui.menu_bar import VoiceTypeMenuBar


def _make_menu_bar(on_show_settings):
    return VoiceTypeMenuBar(
        config={},
        on_quit=lambda: None,
        on_toggle_llm=lambda: None,
        on_set_translation=lambda _lang: None,
        on_show_settings=on_show_settings,
    )


def test_tray_brand_and_settings_items_both_open_settings():
    calls = []
    menu_bar = _make_menu_bar(lambda: calls.append("settings"))
    items = menu_bar.get_tray_menu_items()

    items[0]["callback"](None)
    items[3]["callback"](None)

    assert calls == ["settings", "settings"]


def test_about_dialog_is_modeless_and_reused():
    source_path = Path(__file__).resolve().parents[1] / "ui" / "menu_bar.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    menu_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "VoiceTypeMenuBar"
    )
    show_about = next(
        node
        for node in menu_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "_show_about"
    )
    calls = {
        ast.unparse(node.func)
        for node in ast.walk(show_about)
        if isinstance(node, ast.Call)
    }

    assert "self.about_dialog.show" in calls
    assert "QTimer.singleShot" in calls
    assert not any(call.endswith(".exec") for call in calls)
