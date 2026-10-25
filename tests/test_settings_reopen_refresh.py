"""重新開啟設定視窗時要重讀磁碟上的設定。

Regression: VoiceTypeApp._show_settings 只建立一次 SettingsWindow 之後一律重用，
視窗的 self.config 是建立當下的快照。使用者之後從托盤／選單切換情境、LLM、
動作模式、全時觸發（這些直接寫入磁碟），再開設定視窗按「儲存」，過期快照會把
這些切換悄悄還原。refresh_config() 本來就是為此而生，卻從沒被呼叫。
"""
import os

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ui.app as app_module  # noqa: E402


class _FakeWindow:
    def __init__(self, visible=False):
        self.refreshed_with = None
        self.shown = 0
        self._visible = visible

    def isVisible(self):
        return self._visible

    def refresh_config(self, cfg):
        self.refreshed_with = cfg

    def show(self):
        self.shown += 1


class _Host:
    def __init__(self, window):
        self.settings_window = window

    def _activate_settings_window(self):
        pass


def test_reusing_existing_settings_window_reloads_config_from_disk(monkeypatch):
    disk_config = {"active_scenario": "社群貼文", "action_mode": True}
    monkeypatch.setattr(app_module, "load_config", lambda: disk_config)
    window = _FakeWindow()

    app_module.VoiceTypeApp._show_settings(_Host(window))

    assert window.refreshed_with == disk_config
    assert window.shown == 1


def test_already_open_window_keeps_unsaved_edits(monkeypatch):
    monkeypatch.setattr(app_module, "load_config", lambda: {"x": 1})
    window = _FakeWindow(visible=True)

    app_module.VoiceTypeApp._show_settings(_Host(window))

    assert window.refreshed_with is None
    assert window.shown == 1
