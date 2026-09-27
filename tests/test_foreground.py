"""Tests for utils/foreground.py — the ctypes Win32 foreground-window process
detector backing the "前景視窗感知情境模板自動切換" feature (config.py's
auto_scenario_enabled/auto_scenario_rules, ui/app.py._detect_auto_scenario()).

get_foreground_process_name() talks to real Win32 DLL function pointers stored
as module-level globals (_user32/_kernel32) specifically so tests can swap in
fakes without touching ctypes internals — see the module docstring. Every
fake here mimics the real Win32 out-parameter semantics (writing through
ctypes.byref()) closely enough to exercise the actual code path.
"""
import ctypes
from ctypes import wintypes

import pytest

import utils.foreground as foreground


class _FakeUser32:
    def __init__(self, hwnd=1, pid=4321):
        self.hwnd = hwnd
        self.pid = pid
        self.calls = []

    def GetForegroundWindow(self):
        self.calls.append("GetForegroundWindow")
        return self.hwnd

    def GetWindowThreadProcessId(self, hwnd, pid_ref):
        self.calls.append(("GetWindowThreadProcessId", hwnd))
        pid_ref._obj.value = self.pid
        return 111  # thread id, irrelevant to the code under test


class _FakeKernel32:
    def __init__(self, handle=99, image_path="C:\\Program Files\\Outlook\\OUTLOOK.EXE",
                 open_process_fails=False, query_fails=False):
        self.handle = handle
        self.image_path = image_path
        self.open_process_fails = open_process_fails
        self.query_fails = query_fails
        self.closed_handles = []

    def OpenProcess(self, flags, inherit, pid):
        if self.open_process_fails:
            return 0
        return self.handle

    def QueryFullProcessImageNameW(self, handle, flags, buf, size_ref):
        if self.query_fails:
            return 0
        buf.value = self.image_path
        return 1

    def CloseHandle(self, handle):
        self.closed_handles.append(handle)
        return 1


@pytest.fixture
def force_windows(monkeypatch):
    """Force IS_WINDOWS True regardless of the actual host OS, so the
    "success path" tests exercise the real Win32-calling branch even if some
    future CI runner isn't Windows. This project is Windows-only per
    AGENTS.md, but the fixture keeps the test's intent explicit."""
    monkeypatch.setattr(foreground, "IS_WINDOWS", True)


def test_non_windows_returns_none_without_touching_any_api(monkeypatch):
    monkeypatch.setattr(foreground, "IS_WINDOWS", False)
    # Deliberately leave _user32/_kernel32 as whatever they are; if the
    # non-Windows branch actually invoked them despite IS_WINDOWS=False this
    # would only accidentally pass, so also force them to explode if touched.
    monkeypatch.setattr(foreground, "_user32", object())
    monkeypatch.setattr(foreground, "_kernel32", object())

    assert foreground.get_foreground_process_name() is None


def test_dll_handles_unavailable_returns_none(force_windows, monkeypatch):
    monkeypatch.setattr(foreground, "_user32", None)
    monkeypatch.setattr(foreground, "_kernel32", None)

    assert foreground.get_foreground_process_name() is None


def test_no_foreground_window_returns_none(force_windows, monkeypatch):
    fake_user32 = _FakeUser32(hwnd=0)
    monkeypatch.setattr(foreground, "_user32", fake_user32)
    monkeypatch.setattr(foreground, "_kernel32", _FakeKernel32())

    assert foreground.get_foreground_process_name() is None


def test_zero_pid_returns_none(force_windows, monkeypatch):
    fake_user32 = _FakeUser32(pid=0)
    monkeypatch.setattr(foreground, "_user32", fake_user32)
    monkeypatch.setattr(foreground, "_kernel32", _FakeKernel32())

    assert foreground.get_foreground_process_name() is None


def test_open_process_failure_returns_none(force_windows, monkeypatch):
    monkeypatch.setattr(foreground, "_user32", _FakeUser32())
    monkeypatch.setattr(foreground, "_kernel32", _FakeKernel32(open_process_fails=True))

    assert foreground.get_foreground_process_name() is None


def test_query_image_name_failure_returns_none(force_windows, monkeypatch):
    monkeypatch.setattr(foreground, "_user32", _FakeUser32())
    monkeypatch.setattr(foreground, "_kernel32", _FakeKernel32(query_fails=True))

    assert foreground.get_foreground_process_name() is None


def test_success_returns_basename_with_original_case(force_windows, monkeypatch):
    fake_kernel32 = _FakeKernel32(image_path="C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE")
    monkeypatch.setattr(foreground, "_user32", _FakeUser32())
    monkeypatch.setattr(foreground, "_kernel32", fake_kernel32)

    assert foreground.get_foreground_process_name() == "OUTLOOK.EXE"
    # The process handle must always be closed, success or not.
    assert fake_kernel32.closed_handles == [fake_kernel32.handle]


def test_handle_closed_even_when_query_fails(force_windows, monkeypatch):
    fake_kernel32 = _FakeKernel32(query_fails=True)
    monkeypatch.setattr(foreground, "_user32", _FakeUser32())
    monkeypatch.setattr(foreground, "_kernel32", fake_kernel32)

    foreground.get_foreground_process_name()

    assert fake_kernel32.closed_handles == [fake_kernel32.handle]


def test_unexpected_exception_is_swallowed_and_returns_none(force_windows, monkeypatch):
    class ExplodingUser32:
        def GetForegroundWindow(self):
            raise OSError("simulated Win32 failure")

    monkeypatch.setattr(foreground, "_user32", ExplodingUser32())
    monkeypatch.setattr(foreground, "_kernel32", _FakeKernel32())

    assert foreground.get_foreground_process_name() is None


# --- resolve_scenario_for_process(): pure function, no ctypes involved ---

def test_resolve_exact_match_case_insensitive():
    rules = {"OUTLOOK.EXE": "商務回應"}
    assert foreground.resolve_scenario_for_process("outlook.exe", rules) == "商務回應"
    assert foreground.resolve_scenario_for_process("OUTLOOK.EXE", rules) == "商務回應"
    assert foreground.resolve_scenario_for_process("Outlook.Exe", rules) == "商務回應"


def test_resolve_tolerates_missing_extension_on_either_side():
    # Rule key without ".exe" still matches a process name that has it.
    assert foreground.resolve_scenario_for_process("LINE.EXE", {"line": "社群貼文"}) == "社群貼文"
    # Rule key with ".exe" still matches if (hypothetically) proc_name lacks it.
    assert foreground.resolve_scenario_for_process("line", {"LINE.EXE": "社群貼文"}) == "社群貼文"


def test_resolve_no_match_returns_none():
    assert foreground.resolve_scenario_for_process("notepad.exe", {"outlook.exe": "商務回應"}) is None


def test_resolve_empty_rules_returns_none():
    assert foreground.resolve_scenario_for_process("outlook.exe", {}) is None
    assert foreground.resolve_scenario_for_process("outlook.exe", None) is None


def test_resolve_none_or_empty_proc_name_returns_none():
    rules = {"outlook.exe": "商務回應"}
    assert foreground.resolve_scenario_for_process(None, rules) is None
    assert foreground.resolve_scenario_for_process("", rules) is None


def test_resolve_first_match_wins_on_ambiguous_rules():
    # dict preserves insertion order (Python 3.7+); first matching key wins.
    rules = {"outlook.exe": "商務回應", "OUTLOOK.EXE": "情商大師"}
    assert foreground.resolve_scenario_for_process("outlook.exe", rules) == "商務回應"


def test_resolve_ignores_falsy_rule_keys():
    rules = {"": "should-not-match", "outlook.exe": "商務回應"}
    assert foreground.resolve_scenario_for_process("outlook.exe", rules) == "商務回應"
