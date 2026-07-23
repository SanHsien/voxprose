"""測試 utils/permissions.py（2026-07-23 隱私與加固任務第 4 項：Windows 化清查）。

清查結論：本檔早就沒有 macOS 專屬邏輯殘留（v2.9.6 Windows Stable 已清乾淨），
但 `check_microphone()` 過去永遠回傳 True、`ensure_all_permissions()` 從未被
呼叫過，等於整個模組是死碼。這裡驗證換成真實的 Windows 隱私權登錄檔讀取後，
各種情境下的行為都符合預期，且讀不到機碼/例外時不會對使用者誤報「被拒」。
"""
import logging
from unittest.mock import MagicMock, patch

import pytest

import utils.permissions as permissions_module


class TestCheckMicrophone:
    def test_returns_true_when_registry_says_allow(self, monkeypatch):
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", True)
        fake_key = MagicMock()
        fake_key.__enter__ = MagicMock(return_value=fake_key)
        fake_key.__exit__ = MagicMock(return_value=False)
        with patch("winreg.OpenKey", return_value=fake_key), \
             patch("winreg.QueryValueEx", return_value=("Allow", 1)):
            assert permissions_module.check_microphone() is True

    def test_returns_false_when_registry_says_deny(self, monkeypatch):
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", True)
        fake_key = MagicMock()
        fake_key.__enter__ = MagicMock(return_value=fake_key)
        fake_key.__exit__ = MagicMock(return_value=False)
        with patch("winreg.OpenKey", return_value=fake_key), \
             patch("winreg.QueryValueEx", return_value=("Deny", 1)):
            assert permissions_module.check_microphone() is False

    def test_returns_true_when_registry_key_missing(self, monkeypatch):
        """機碼不存在（舊版 Windows／企業原則管理等）：不能誤報使用者被拒。"""
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", True)
        with patch("winreg.OpenKey", side_effect=FileNotFoundError()):
            assert permissions_module.check_microphone() is True

    def test_returns_true_on_unexpected_registry_error(self, monkeypatch, caplog):
        """任何其他例外也一律視為已授權——這是「額外提示」不是唯一依據。"""
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", True)
        with patch("winreg.OpenKey", side_effect=OSError("boom")):
            with caplog.at_level(logging.DEBUG, logger="voicetype"):
                assert permissions_module.check_microphone() is True

    def test_non_windows_always_returns_true(self, monkeypatch):
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", False)
        assert permissions_module.check_microphone() is True


class TestEnsureAllPermissions:
    def test_logs_warning_when_microphone_denied(self, monkeypatch, caplog):
        monkeypatch.setattr(permissions_module, "check_microphone", lambda: False)
        with caplog.at_level(logging.WARNING, logger="voicetype"):
            permissions_module.ensure_all_permissions()
        assert any("麥克風" in r.message for r in caplog.records)

    def test_no_warning_when_microphone_allowed(self, monkeypatch, caplog):
        monkeypatch.setattr(permissions_module, "check_microphone", lambda: True)
        with caplog.at_level(logging.WARNING, logger="voicetype"):
            permissions_module.ensure_all_permissions()
        assert not any("麥克風" in r.message for r in caplog.records)

    def test_does_not_raise_and_takes_no_further_action(self, monkeypatch):
        """啟動流程不該有意外的跳窗副作用：denied 時只 log，不自動開啟設定。"""
        monkeypatch.setattr(permissions_module, "check_microphone", lambda: False)
        with patch("os.startfile") as mock_startfile:
            permissions_module.ensure_all_permissions()
        mock_startfile.assert_not_called()


class TestRequestMicrophonePermission:
    def test_opens_windows_privacy_settings(self, monkeypatch):
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", True)
        with patch("os.startfile") as mock_startfile:
            permissions_module.request_microphone_permission()
        mock_startfile.assert_called_once_with("ms-settings:privacy-microphone")

    def test_non_windows_is_a_noop(self, monkeypatch):
        monkeypatch.setattr(permissions_module, "IS_WINDOWS", False)
        with patch("os.startfile") as mock_startfile:
            permissions_module.request_microphone_permission()
        mock_startfile.assert_not_called()


def test_check_accessibility_always_true():
    assert permissions_module.check_accessibility() is True
