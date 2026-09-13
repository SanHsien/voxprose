import ast
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"


def test_run_starts_tray_before_hotkey_listener_and_event_loop():
    tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
    app_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "VoiceTypeApp"
    )
    run_method = next(
        node
        for node in app_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "run"
    )
    call_lines = {
        ast.unparse(node.func): node.lineno
        for node in ast.walk(run_method)
        if isinstance(node, ast.Call)
    }

    assert call_lines["self.tray.start"] < call_lines["self.hotkey_listener.start"]
    assert call_lines["self.hotkey_listener.start"] < call_lines["app_inst.exec"]
