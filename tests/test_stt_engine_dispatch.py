"""Guard against the UI's STT engine dropdown and stt.get_stt()'s dispatch
logic drifting apart (see REVIEW.md 2026-07-19 finding: the "Gemini (雲端 API)"
option in ui/settings_window.py used to have no matching branch in
get_stt(), so selecting it silently fell back to local Whisper).

ui/settings_window.py imports PyQt6 at module scope, which may not be
installed in every dev/CI environment (see tests/test_smoke.py's treatment
of ui.positions). To keep this guard runnable everywhere, we statically
extract the STT_ENGINES literal via source parsing instead of importing the
module, then verify stt.get_stt() returns the expected concrete class for
every engine value listed there -- without spawning real subprocesses,
loading real Whisper models, or making real network calls.
"""
import ast
import re
from pathlib import Path

import pytest

import stt

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_WINDOW_SRC = (REPO_ROOT / "ui" / "settings_window.py").read_text(encoding="utf-8")


def _extract_stt_engines() -> list[str]:
    match = re.search(r"STT_ENGINES\s*=\s*(\[[^\]]*\])", SETTINGS_WINDOW_SRC)
    assert match, "Could not find STT_ENGINES = [...] in ui/settings_window.py"
    return ast.literal_eval(match.group(1))


STT_ENGINES = _extract_stt_engines()


def test_stt_engines_list_matches_expected_snapshot():
    """Fails loudly if someone adds/removes a UI engine option, as a nudge to
    also update this test's per-engine expectations below."""
    assert STT_ENGINES == ["local_whisper", "groq", "gemini", "openrouter"]


def test_groq_engine_dispatches_to_groq_whisper_stt(monkeypatch):
    groq_module = pytest.importorskip("groq", reason="groq SDK not installed in this environment")
    from stt.groq_whisper import GroqWhisperSTT

    monkeypatch.setattr(GroqWhisperSTT, "__init__", lambda self, config: None)
    result = stt.get_stt({"stt_engine": "groq", "groq_api_key": "test-key"})
    assert isinstance(result, GroqWhisperSTT)


def test_openrouter_engine_dispatches_to_openrouter_stt():
    from stt.openrouter_stt import OpenRouterSTT

    result = stt.get_stt({"stt_engine": "openrouter", "openrouter_api_key": "test-key"})
    assert isinstance(result, OpenRouterSTT)


def test_gemini_engine_dispatches_to_gemini_stt():
    """The bug this whole test module exists to prevent: previously "gemini"
    fell through to the else-branch (local Whisper) instead of GeminiSTT."""
    from stt.gemini_stt import GeminiSTT

    result = stt.get_stt({"stt_engine": "gemini", "gemini_api_key": "test-key"})
    assert isinstance(result, GeminiSTT)


def test_local_whisper_engine_dispatches_by_platform(monkeypatch):
    from stt.subprocess_whisper import SubprocessWhisperSTT
    from stt.local_whisper import LocalWhisperSTT

    monkeypatch.setattr(SubprocessWhisperSTT, "__init__", lambda self, config: None)
    monkeypatch.setattr(LocalWhisperSTT, "__init__", lambda self, config: None)

    import platform as platform_module

    monkeypatch.setattr(platform_module, "system", lambda: "Windows")
    result_windows = stt.get_stt({"stt_engine": "local_whisper"})
    assert isinstance(result_windows, SubprocessWhisperSTT)

    monkeypatch.setattr(platform_module, "system", lambda: "Darwin")
    result_other = stt.get_stt({"stt_engine": "local_whisper"})
    assert isinstance(result_other, LocalWhisperSTT)


def test_every_ui_engine_option_has_a_real_dispatch_branch(monkeypatch):
    """The general form of the regression test: for every value the settings
    UI can put into config["stt_engine"], get_stt() must not silently fall
    through to the generic platform-default branch under a name that looks
    like it should be its own dedicated engine.
    """
    from stt.openrouter_stt import OpenRouterSTT
    from stt.gemini_stt import GeminiSTT
    from stt.subprocess_whisper import SubprocessWhisperSTT
    from stt.local_whisper import LocalWhisperSTT

    monkeypatch.setattr(SubprocessWhisperSTT, "__init__", lambda self, config: None)
    monkeypatch.setattr(LocalWhisperSTT, "__init__", lambda self, config: None)

    import platform as platform_module
    monkeypatch.setattr(platform_module, "system", lambda: "Windows")

    expected_class = {
        "local_whisper": SubprocessWhisperSTT,  # forced to "Windows" above; this project is Windows-only
        "gemini": GeminiSTT,
        "openrouter": OpenRouterSTT,
    }

    for engine in STT_ENGINES:
        if engine == "groq":
            try:
                from stt.groq_whisper import GroqWhisperSTT
            except ImportError:
                continue  # groq SDK not installed in this environment; covered separately when present
            monkeypatch.setattr(GroqWhisperSTT, "__init__", lambda self, config: None)
            expected_class["groq"] = GroqWhisperSTT

        result = stt.get_stt({"stt_engine": engine, f"{engine}_api_key": "test-key"})
        assert isinstance(result, expected_class[engine]), (
            f"stt_engine={engine!r} dispatched to {type(result).__name__}, "
            f"expected {expected_class[engine].__name__}"
        )
