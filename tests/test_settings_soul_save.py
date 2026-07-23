"""Regression tests for SettingsWindow soul prompt persistence.

Regression: QA-SETTINGS-001 — a bare except hid write failures and still showed
the user a false "settings saved" success message.
Found by /qa on 2026-07-24.
Report: REVIEW.md
"""

import os

import pytest


pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QMessageBox  # noqa: E402

import ui.settings_window as settings_module  # noqa: E402
from ui.settings_window import SettingsWindow  # noqa: E402


class _Prompt:
    def __init__(self, text):
        self._text = text

    def toPlainText(self):
        return self._text


class _Host:
    def __init__(self, text):
        self.soul_prompt = _Prompt(text)


def test_save_soul_prompt_writes_trimmed_utf8_text(tmp_path, monkeypatch):
    soul_path = tmp_path / "soul.md"
    monkeypatch.setattr(settings_module, "SOUL_BASE_PATH", soul_path)

    result = SettingsWindow._save_soul_prompt(_Host("  你好，世界  \n"))

    assert result is True
    assert soul_path.read_text(encoding="utf-8") == "你好，世界"


def test_save_soul_prompt_reports_failure_instead_of_false_success(
    tmp_path, monkeypatch, caplog
):
    soul_path = tmp_path / "missing" / "soul.md"
    monkeypatch.setattr(settings_module, "SOUL_BASE_PATH", soul_path)
    messages = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda *args: messages.append(args[-1]),
    )

    result = SettingsWindow._save_soul_prompt(_Host("內容"))

    assert result is False
    assert len(messages) == 1
    assert "其他設定尚未儲存" in messages[0]
    assert str(soul_path) in messages[0]
    assert any("Failed to write soul prompt" in record.message for record in caplog.records)
