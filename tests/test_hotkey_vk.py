"""熱鍵設定字串 -> Windows 虛擬鍵碼。

Regression: config.py 的預設熱鍵是 hotkey_toggle="f13"、hotkey_llm="f14"，但
hotkey/listener.py 的舊式字串對照表只到 f12，預設值解析成 0 而被輪詢迴圈
直接跳過——全新安裝（尚未在設定頁錄過熱鍵）的切換／LLM 熱鍵完全沒反應。
"""
from config import DEFAULT_CONFIG
from hotkey.listener import resolve_vk


def test_code_form_from_settings_ui():
    assert resolve_vk("page_up (code:116)") == 116
    assert resolve_vk("x (CODE:88)") == 88


def test_legacy_names():
    assert resolve_vk("alt_r") == 0xA5
    assert resolve_vk("F12") == 0x7B


def test_f13_to_f24_supported():
    assert resolve_vk("f13") == 0x7C
    assert resolve_vk("f14") == 0x7D
    assert resolve_vk("f24") == 0x87


def test_every_default_hotkey_resolves_to_a_real_key():
    for name in ("hotkey_ptt", "hotkey_toggle", "hotkey_llm"):
        assert resolve_vk(DEFAULT_CONFIG[name]) != 0, name


def test_unknown_returns_zero():
    assert resolve_vk("nonsense") == 0
