"""Ported from the old (pre-Windows-purification) Mac main line's
`test_stt_hallucination_filter.py` (recovered from commit 51094bf via
`git show`). The original tested `stt.mlx_whisper._is_hallucination`, an
Apple-Silicon-only module that does not exist in this Windows-only tree.

The underlying filtering logic is pure text processing with no MLX/platform
dependency, so it has been ported into stt/hallucination_filter.py (public
name `is_hallucination`) and wired into ui/app.py's `_process_audio` right
after the STT engine returns text -- applying uniformly to every engine
(local subprocess Whisper, Groq, OpenRouter, Gemini), not just one MLX-only
implementation as before. This closes the functional regression noted in
REVIEW.md 2026-07-19 (win-stable had no hallucination filter at all).
"""
import unittest

from stt.hallucination_filter import is_hallucination


class WhisperHallucinationFilterTest(unittest.TestCase):
    def test_drops_repeated_pass_noise_with_youtube_ending(self):
        text = "通過 " * 74 + " Thanks for watching!"

        self.assertTrue(is_hallucination(text))

    def test_drops_dominant_repeated_english_tail(self):
        text = "除非你已經取得 " + "anterior access " * 70

        self.assertTrue(is_hallucination(text))

    def test_drops_cantonese_youtube_ending_variant(self):
        self.assertTrue(is_hallucination("多謝您的觀看。"))

    def test_keeps_normal_sentence_that_mentions_thanks_for_watching(self):
        text = "我覺得謝謝收看的設計很好"

        self.assertFalse(is_hallucination(text))

    def test_empty_text_is_not_a_hallucination(self):
        self.assertFalse(is_hallucination(""))

    def test_single_word_hallucination_phrase(self):
        self.assertTrue(is_hallucination("Subscribe"))

    def test_repeated_full_phrase_concatenation(self):
        text = "Thank you for watching.Thank you for watching."

        self.assertTrue(is_hallucination(text))

    def test_single_filler_word_is_dropped(self):
        """REVIEW.md 24-3: a lone filler word ("嗯") is the intended-to-drop case."""
        self.assertTrue(is_hallucination("嗯"))

    def test_single_filler_word_with_trailing_punctuation_is_dropped(self):
        """Trailing punctuation/comma noise around a lone filler word should
        still match — Whisper often appends a stray period/comma to a bare
        filler-word hallucination."""
        self.assertTrue(is_hallucination("嗯。"))
        self.assertTrue(is_hallucination("嗯，"))

    def test_sentence_containing_filler_word_mid_sentence_is_kept(self):
        """REVIEW.md 24-3: filler words embedded in a real sentence must NOT
        be dropped. is_hallucination() requires the whole (punctuation-
        trimmed) text to exactly match a blacklist entry -- not substring
        containment -- so a genuine sentence that happens to start with a
        filler word survives."""
        self.assertFalse(is_hallucination("嗯，我想想這個問題"))

    def test_sentence_ending_with_filler_word_is_kept(self):
        """Same guarantee as above but with the filler word trailing a real
        sentence instead of leading it."""
        self.assertFalse(is_hallucination("今天天氣真好啊"))


if __name__ == "__main__":
    unittest.main()
