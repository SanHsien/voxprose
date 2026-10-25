"""translation_lang 接進 ui/app.py 的 _build_llm_prompt（需要 PyQt6）。"""
import os

import pytest

from llm.prompts import get_translation_instruction

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
