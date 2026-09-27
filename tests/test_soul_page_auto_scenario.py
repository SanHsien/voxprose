"""PyQt6 offscreen smoke tests for the "前景視窗自動情境切換" UI block added to
ui/settings/soul_page.py (SoulPageMixin._create_auto_scenario_section() and its
helper methods).

Deliberately builds only a minimal host widget mixing in SoulPageMixin (not the
full SettingsWindow, which pulls in every other settings page — dashboard,
STT/LLM engine, vocab/memory, sync, stats — and touches unrelated filesystem
state). This keeps the test fast and scoped to exactly the code this task
added, while still exercising real PyQt6 widget construction/interaction
(QT_QPA_PLATFORM=offscreen, no visible window needed).

Skips (not fails) when PyQt6 isn't installed in the current environment,
consistent with tests/test_smoke.py's OPTIONAL_DEPENDENCY_MODULES pattern
(AGENTS.md: 不要為了測試去裝大型相依) — it *is* installed in CI via
requirements-win.txt, so this still runs there.
"""
import os

import pytest

pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from ui.settings.common import CommonPageMixin  # noqa: E402
from ui.settings.soul_page import SoulPageMixin  # noqa: E402


class _FakeSoulSettingsWidget(QWidget, CommonPageMixin, SoulPageMixin):
    """Minimal host object providing just what _create_auto_scenario_section()
    and friends read off `self`: a `self.config` dict. Everything else the
    mixin needs (the widgets themselves) it creates and stores on `self`."""

    def __init__(self, config):
        super().__init__()
        self.config = config


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _make_widget(qapp, config=None):
    """Build the fake host widget and actually parent the auto-scenario
    section into it (mirrors real usage: ui/settings/soul_page.py's
    `_create_soul_page()` does `layout.addWidget(self._create_auto_scenario_section())`).
    Without a Qt-parent relationship, the returned QWidget (and its child
    QTableWidget) has no owner keeping the underlying C/C++ object alive once
    the local variable inside `_create_auto_scenario_section()` goes out of
    scope, and PyQt6 raises `RuntimeError: wrapped C/C++ object ... has been
    deleted` on any later access."""
    w = _FakeSoulSettingsWidget(
        config if config is not None else {"auto_scenario_enabled": False, "auto_scenario_rules": {}}
    )
    layout = QVBoxLayout(w)
    layout.addWidget(w._create_auto_scenario_section())
    return w


def test_section_builds_with_defaults_disabled_and_empty(qapp):
    w = _make_widget(qapp)

    assert w.auto_scenario_enabled_cb.isChecked() is False
    assert w.auto_scenario_table.rowCount() == 0
    assert w.auto_scenario_table.columnCount() == 2


def test_section_reflects_enabled_config_on_build(qapp):
    w = _make_widget(qapp, {"auto_scenario_enabled": True, "auto_scenario_rules": {}})

    assert w.auto_scenario_enabled_cb.isChecked() is True


def test_populate_table_from_existing_config_rules(qapp):
    config = {
        "auto_scenario_enabled": True,
        "auto_scenario_rules": {"outlook.exe": "商務回應", "line.exe": "default"},
    }
    w = _make_widget(qapp, config)
    w._populate_auto_scenario_rules_table()

    assert w.auto_scenario_table.rowCount() == 2
    assert w._collect_auto_scenario_rules() == {"outlook.exe": "商務回應", "line.exe": "default"}


def test_add_and_remove_rule_row_round_trips(qapp):
    w = _make_widget(qapp)

    row = w._add_auto_scenario_rule_row("notepad.exe", "default")
    assert w.auto_scenario_table.rowCount() == 1
    assert w._collect_auto_scenario_rules() == {"notepad.exe": "default"}

    w.auto_scenario_table.selectRow(row)
    w._remove_selected_auto_scenario_rule()
    assert w.auto_scenario_table.rowCount() == 0
    assert w._collect_auto_scenario_rules() == {}


def test_collect_skips_blank_process_name_rows(qapp):
    w = _make_widget(qapp)

    w._add_auto_scenario_rule_row("", "default")
    w._add_auto_scenario_rule_row("outlook.exe", "default")

    assert w._collect_auto_scenario_rules() == {"outlook.exe": "default"}


def test_scenario_combo_preserves_unknown_existing_value(qapp):
    """A rule referencing a scenario file that no longer exists on disk must
    still show/keep that value in the dropdown instead of silently discarding
    it — no silent data loss when reopening settings after a scenario file
    was deleted outside the app."""
    w = _make_widget(qapp)

    w._add_auto_scenario_rule_row("outlook.exe", "已刪除的情境檔")
    combo = w.auto_scenario_table.cellWidget(0, 1)
    assert combo.currentText() == "已刪除的情境檔"


def test_available_scenario_names_always_includes_default(qapp):
    w = _make_widget(qapp)
    names = w._available_scenario_names()
    assert "default" in names
