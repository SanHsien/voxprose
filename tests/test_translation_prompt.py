"""「快速翻譯」選單／語音指令設定的 translation_lang 要真的進到 LLM prompt。

Regression: 選單的「翻譯成 英文／日文」與語音指令「切換至英文」會寫入
config["translation_lang"]，README 與 docs/DEVELOPMENT.md 檢核表也承諾「開啟翻譯
（英/日）時優先翻譯為目標語文」，但全 repo 沒有任何地方讀取這個設定——
選了翻譯，輸出完全不翻。
"""
import os

import pytest

from llm.prompts import get_translation_instruction


def test_known_targets_produce_an_instruction():
    assert "English" in get_translation_instruction("en")
    assert "日本語" in get_translation_instruction("ja")


def test_no_translation_means_no_instruction():
    assert get_translation_instruction(None) == ""
    assert get_translation_instruction("") == ""
    assert get_translation_instruction("zh") == ""
    assert get_translation_instruction("klingon") == ""


pytest.importorskip("PyQt6", reason="PyQt6 not installed in this environment")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ui.app as app_module  # noqa: E402


class _Host:
    def __init__(self, config):
        self.config = config

    def _get_effective_scenario(self):
        return "default"


def _build(config, monkeypatch, is_assistant=False):
    import vocab.manager

    monkeypatch.setattr(vocab.manager, "load_custom_vocab", lambda: [])
    return app_module.VoiceTypeApp._build_llm_prompt(_Host(config), "你好", is_assistant=is_assistant)


def test_translation_lang_reaches_the_llm_prompt(monkeypatch):
    prompt = _build({"translation_lang": "en"}, monkeypatch)
    assert get_translation_instruction("en") in prompt


def test_no_translation_lang_leaves_prompt_unchanged(monkeypatch):
    prompt = _build({"translation_lang": None}, monkeypatch)
    assert "翻譯指令" not in prompt


def test_assistant_mode_is_not_translated(monkeypatch):
    prompt = _build({"translation_lang": "ja"}, monkeypatch, is_assistant=True)
    assert "翻譯指令" not in prompt
