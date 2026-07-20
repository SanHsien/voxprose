"""Ported from the Mac mainline (`git show 51094bf:test_stt_language_selection.py`).

Regression test for the bug found via `docs/mac-mainline-absorption-analysis.md`
item 16-3: `ui/app.py`'s `_process_audio` used to read `translation_lang` and feed
it straight to `self.stt.transcribe(audio_data, language=lang)`. Translation is
an LLM output-layer concern (see `active_scenario` prompt selection); once a
user picked "translate to English" once, `translation_lang` stayed `"en"` in
config and every subsequent Chinese dictation session got an English STT
language hint, degrading recognition. `stt/language.py:get_transcription_language()`
now sources the hint from `config["language"]` (the user's actual STT language
setting) and ignores `translation_lang` entirely.
"""
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
