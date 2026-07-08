import unittest

from stt.language import get_transcription_language


class STTLanguageSelectionTest(unittest.TestCase):
    def test_translation_language_does_not_override_transcription_language(self):
        config = {"language": "zh", "translation_lang": "en"}

        self.assertEqual(get_transcription_language(config), "zh")

    def test_defaults_to_chinese_when_missing(self):
        self.assertEqual(get_transcription_language({}), "zh")


if __name__ == "__main__":
    unittest.main()
