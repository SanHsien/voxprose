"""LLM 輸出的半形標點轉全形，不能破壞數字、時間與網址。

Regression: ui/app.py 原本對整段文字逐字 replace(",", "，") / replace(":", "：")，
「3:30」變「3：30」、「1,000」變「1，000」、「http://x」變「http：//x」。
"""
from utils.punctuation import to_fullwidth_punctuation


def test_sentence_punctuation_becomes_fullwidth():
    assert to_fullwidth_punctuation("你好, 世界! 真的嗎? 是的; 好:") == "你好， 世界！ 真的嗎？ 是的； 好："


def test_time_and_thousands_separator_untouched():
    assert to_fullwidth_punctuation("會議在3:30開始, 費用1,000元") == "會議在3:30開始， 費用1,000元"
    assert to_fullwidth_punctuation("12:30:45") == "12:30:45"


def test_url_scheme_colon_untouched():
    assert to_fullwidth_punctuation("網址是 https://example.com 請看:") == "網址是 https://example.com 請看："


def test_period_unchanged_and_empty_safe():
    assert to_fullwidth_punctuation("3.14") == "3.14"
    assert to_fullwidth_punctuation("") == ""


def test_english_translation_output_keeps_halfwidth_punctuation():
    text = "Hello, how are you? Great: thanks!"
    assert to_fullwidth_punctuation(text, "en") == text


def test_japanese_translation_still_uses_fullwidth():
    assert to_fullwidth_punctuation("こんにちは, 元気?", "ja") == "こんにちは， 元気？"
