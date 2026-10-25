"""「快速翻譯」選單／語音指令設定的 translation_lang 要真的進到 LLM prompt。

Regression: 選單的「翻譯成 英文／日文」與語音指令「切換至英文」會寫入
config["translation_lang"]，README 與 docs/DEVELOPMENT.md 檢核表也承諾「開啟翻譯
（英/日）時優先翻譯為目標語文」，但全 repo 沒有任何地方讀取這個設定——
選了翻譯，輸出完全不翻。
"""
from llm.prompts import get_translation_instruction


def test_known_targets_produce_an_instruction():
    assert "English" in get_translation_instruction("en")
    assert "日本語" in get_translation_instruction("ja")


def test_no_translation_means_no_instruction():
    assert get_translation_instruction(None) == ""
    assert get_translation_instruction("") == ""
    assert get_translation_instruction("zh") == ""
    assert get_translation_instruction("klingon") == ""
