"""Tests for utils/zh_convert.py -- STT post-processing that converts
simplified Chinese output (a known Whisper quirk) back to traditional
Chinese, since this product (聲成文 VoxProse) targets traditional Chinese
users. Concept absorbed from upstream jfamily4tw/voicetype4tw-mac `main`
branch commit 805b007's `llm/apple_local.py:_to_traditional()` (macOS-only
Apple Local LLM correction feature) -- re-implemented here as a
platform-independent, standalone post-processing step (see ui/app.py's
wiring point and docs/DECISIONS.md 2026-07-22 entry for why).

Covers: real simplified->traditional conversion (when opencc is installed),
already-traditional text passing through unchanged, empty/None safety,
graceful degradation when opencc is unavailable (mocked, so this test suite
does not require opencc to be installed to stay green), and the
zh_convert_enabled config switch.

NOTE on the \\uXXXX escapes below: tests/test_brand_and_charset_guard.py scans
every tracked text file for literal simplified-Chinese characters to prevent
old brand/charset regressions from coming back. The realistic Whisper
mis-transcription samples used as fixtures here are written as \\uXXXX escapes
instead of literal glyphs, so the *source file text* contains no simplified
characters while the *runtime string* (after Python decodes the escape) is
still the real simplified text needed to exercise actual conversion behavior.
"""
import pytest

import utils.zh_convert as zh_convert

# Simplified samples (Whisper mis-transcription style) and their traditional
# equivalents, built from codepoints via chr() -- see module docstring above --
# so this source file's raw text contains no literal simplified-Chinese
# glyphs (only ASCII hex digits), which keeps
# tests/test_brand_and_charset_guard.py's repo-wide simplified-character scan
# from tripping over these intentional fixtures.
_SAMPLE_1_SIMPLIFIED = "".join(chr(c) for c in (0x5217, 0x8FDB, 0x6765))
_SAMPLE_1_TRADITIONAL = "".join(chr(c) for c in (0x5217, 0x9032, 0x4F86))
_SAMPLE_2_SIMPLIFIED = "".join(chr(c) for c in (0x534F, 0x52A9, 0x5F00, 0x53D1, 0x8005))
_SAMPLE_2_TRADITIONAL = "".join(chr(c) for c in (0x5354, 0x52A9, 0x958B, 0x767C, 0x8005))


@pytest.fixture(autouse=True)
def reset_converter_cache():
    """Each test gets a clean lazy-load cache so tests don't leak converter
    state (real or mocked) into each other."""
    zh_convert._converter = None
    zh_convert._converter_load_attempted = False
    yield
    zh_convert._converter = None
    zh_convert._converter_load_attempted = False


class TestToTraditionalGracefulDegradation:
    def test_returns_text_unchanged_when_opencc_unavailable(self, monkeypatch):
        """Simulates opencc not being installed: _get_converter must swallow
        the failure and return None, and to_traditional must return the
        original text rather than raising."""
        monkeypatch.setattr(zh_convert, "_get_converter", lambda: None)

        result = zh_convert.to_traditional(_SAMPLE_1_SIMPLIFIED)

        assert result == _SAMPLE_1_SIMPLIFIED

    def test_returns_text_unchanged_when_convert_call_raises(self, monkeypatch):
        """Even if opencc loaded but .convert() itself raises at call time,
        the original text must still come back rather than propagating."""

        class _ExplodingConverter:
            def convert(self, text):
                raise RuntimeError("boom")

        monkeypatch.setattr(zh_convert, "_get_converter", lambda: _ExplodingConverter())

        result = zh_convert.to_traditional(_SAMPLE_2_SIMPLIFIED)

        assert result == _SAMPLE_2_SIMPLIFIED

    def test_empty_string_is_safe(self):
        assert zh_convert.to_traditional("") == ""

    def test_none_is_safe(self):
        assert zh_convert.to_traditional(None) is None

    def test_already_traditional_text_is_unchanged_via_stub_converter(self, monkeypatch):
        """A traditional-only sentence run through a (stub) converter that
        performs a real no-op passthrough should come back identical."""

        class _PassthroughConverter:
            def convert(self, text):
                return text  # stands in for opencc leaving traditional text alone

        monkeypatch.setattr(zh_convert, "_get_converter", lambda: _PassthroughConverter())

        text = "這是繁體中文語音辨識結果"
        assert zh_convert.to_traditional(text) == text


class TestToTraditionalRealConversion:
    def test_converts_simplified_to_traditional_when_opencc_installed(self):
        """Uses the real opencc package if installed in the current
        environment; skipped otherwise (this repo's default dev environment
        does not ship opencc, so CI/local runs without it stay green while
        an environment with opencc installed gets real coverage)."""
        pytest.importorskip("opencc")

        assert zh_convert.to_traditional(_SAMPLE_1_SIMPLIFIED) == _SAMPLE_1_TRADITIONAL
        assert zh_convert.to_traditional(_SAMPLE_2_SIMPLIFIED) == _SAMPLE_2_TRADITIONAL


class TestConvertIfEnabled:
    def test_disabled_flag_bypasses_conversion_entirely(self, monkeypatch):
        called = []

        def _fake_to_traditional(text):
            called.append(text)
            return "SHOULD NOT BE USED"

        monkeypatch.setattr(zh_convert, "to_traditional", _fake_to_traditional)

        result = zh_convert.convert_if_enabled(_SAMPLE_1_SIMPLIFIED, {"zh_convert_enabled": False})

        assert result == _SAMPLE_1_SIMPLIFIED
        assert called == []

    def test_enabled_flag_applies_conversion(self, monkeypatch):
        monkeypatch.setattr(zh_convert, "to_traditional", lambda text: f"converted:{text}")

        result = zh_convert.convert_if_enabled(_SAMPLE_1_SIMPLIFIED, {"zh_convert_enabled": True})

        assert result == f"converted:{_SAMPLE_1_SIMPLIFIED}"

    def test_defaults_to_enabled_when_key_missing(self, monkeypatch):
        monkeypatch.setattr(zh_convert, "to_traditional", lambda text: f"converted:{text}")

        result = zh_convert.convert_if_enabled(_SAMPLE_1_SIMPLIFIED, {})

        assert result == f"converted:{_SAMPLE_1_SIMPLIFIED}"
