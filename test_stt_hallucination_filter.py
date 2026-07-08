import unittest

from stt.mlx_whisper import _is_hallucination


class WhisperHallucinationFilterTest(unittest.TestCase):
    def test_drops_repeated_pass_noise_with_youtube_ending(self):
        text = "通過 " * 74 + " Thanks for watching!"

        self.assertTrue(_is_hallucination(text))

    def test_drops_dominant_repeated_english_tail(self):
        text = "除非你已經取得 " + "anterior access " * 70

        self.assertTrue(_is_hallucination(text))

    def test_drops_cantonese_youtube_ending_variant(self):
        self.assertTrue(_is_hallucination("多謝您的觀看。"))

    def test_keeps_normal_sentence_that_mentions_thanks_for_watching(self):
        text = "我覺得謝謝收看的設計很好"

        self.assertFalse(_is_hallucination(text))


if __name__ == "__main__":
    unittest.main()
