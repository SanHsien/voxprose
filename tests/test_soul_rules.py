"""測試 Mac 主線 7-5（`docs/mac-mainline-absorption-analysis.md`）移植：LLM 未啟用時
的輕量版靈魂規則（贅詞清除）。純邏輯測試，見 utils/soul_rules.py。
"""
import unittest

from utils.soul_rules import (
    apply_basic_soul_rules,
    extract_filler_words,
    strip_filler_words,
)

SAMPLE_SOUL_MD = """# SOUL.md

## 說話風格

一些不相干的內容。

## 贅詞清除規則（鐵律，永不輸出）
以下口頭禪與贅詞，在輸出時**一律刪除不寫**：
- 「所以說」、「就是說」
- 「就是」、「就來說」
- 「然後」、「然後呢」
- 「那」、「這個」

## 下一個區段
- 「不應該被抽到」
"""


class ExtractFillerWordsTest(unittest.TestCase):
    def test_extracts_words_within_section(self):
        words = extract_filler_words(SAMPLE_SOUL_MD)
        self.assertIn("所以說", words)
        self.assertIn("就是說", words)
        self.assertIn("就是", words)
        self.assertIn("就來說", words)
        self.assertIn("然後", words)
        self.assertIn("然後呢", words)
        self.assertIn("那", words)
        self.assertIn("這個", words)

    def test_stops_at_next_heading(self):
        words = extract_filler_words(SAMPLE_SOUL_MD)
        self.assertNotIn("不應該被抽到", words)

    def test_empty_or_none_input_returns_empty_list(self):
        self.assertEqual(extract_filler_words(""), [])
        self.assertEqual(extract_filler_words(None), [])

    def test_no_section_marker_returns_empty_list(self):
        self.assertEqual(extract_filler_words("# 一般內容\n沒有贅詞區段"), [])


class StripFillerWordsTest(unittest.TestCase):
    def test_removes_all_filler_words(self):
        text = "然後就是說這個嘛，那個我覺得可以。"
        result = strip_filler_words(text, ["然後", "就是說", "這個"])
        self.assertNotIn("然後", result)
        self.assertNotIn("就是說", result)
        self.assertNotIn("這個", result)

    def test_longer_words_processed_before_shorter_ones(self):
        """「那對」比「那」長，若「那」先刪會讓「那對」比對不到——驗證排序邏輯正確。"""
        text = "那對啊我覺得可以"
        result = strip_filler_words(text, ["那", "那對"])
        self.assertNotIn("那對", result)
        self.assertNotIn("那", result)

    def test_empty_filler_list_returns_stripped_text_unchanged(self):
        self.assertEqual(strip_filler_words("  原文  ", []), "原文")

    def test_empty_text_returns_empty_string(self):
        self.assertEqual(strip_filler_words("", ["然後"]), "")

    def test_empty_string_in_filler_words_is_ignored(self):
        # 不能把空字串當「詞語」拿去 text.replace("", "")（那是 no-op 但也不該報錯）
        result = strip_filler_words("正常文字", ["", "不存在的詞"])
        self.assertEqual(result, "正常文字")


class ApplyBasicSoulRulesTest(unittest.TestCase):
    def test_combines_multiple_soul_documents(self):
        base_md = "## 贅詞清除規則\n- 「嗯」、「呃」\n"
        scenario_md = "## 贅詞清除規則\n- 「基本上」\n"
        text = "嗯基本上呃我覺得可以"
        result = apply_basic_soul_rules(text, [base_md, scenario_md])
        self.assertNotIn("嗯", result)
        self.assertNotIn("呃", result)
        self.assertNotIn("基本上", result)
        self.assertIn("我覺得可以", result)

    def test_default_scenario_md_real_content(self):
        """用現樹實際的 soul/scenario/default.md 內容驗證（含 7-6 新增的「所以說」/「就是說」）。"""
        from pathlib import Path
        default_md = (Path(__file__).resolve().parent.parent / "soul" / "scenario" / "default.md").read_text(
            encoding="utf-8"
        )
        text = "所以說呢就是說這個然後我覺得可以啦"
        result = apply_basic_soul_rules(text, [default_md])
        self.assertNotIn("所以說", result)
        self.assertNotIn("就是說", result)
        self.assertNotIn("這個", result)
        self.assertNotIn("然後", result)


if __name__ == "__main__":
    unittest.main()
