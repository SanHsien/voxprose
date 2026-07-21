"""Guard against the UI's STT engine dropdown and stt.get_stt()'s dispatch
logic drifting apart (see REVIEW.md 2026-07-19 finding: the "Gemini (雲端 API)"
option in ui/settings_window.py used to have no matching branch in
get_stt(), so selecting it silently fell back to local Whisper).

2026-07-21（REVIEW.md #7 god-file 拆分）：STT_ENGINES 的字面定義隨拆分搬到
`ui/settings/common.py`（原本住在 ui/settings_window.py 模組層級），
ui/settings_window.py 現在只是 `from ui.settings.common import ...` 轉手，
静態原始碼裡已經沒有 `STT_ENGINES = [...]` 這行字面量可以 parse 了，因此本檔
的解析目標同步改指向 ui/settings/common.py。

ui/settings/common.py 一樣在模組頂層 import PyQt6，可能在部分 dev/CI 環境沒
裝（見 tests/test_smoke.py 對 ui.positions 的處理方式）。為了讓這個防護在任何
環境都能跑，我們一樣改用靜態原始碼解析取出 STT_ENGINES 字面量，而不是真的
import 該模組，再驗證 stt.get_stt() 對清單裡每個引擎值都能分派到正確的具體
類別——不需要開真實子行程、載入真實 Whisper 模型、或打真實網路請求。
"""
import ast
import re
from pathlib import Path

import pytest

import stt

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_COMMON_SRC = (REPO_ROOT / "ui" / "settings" / "common.py").read_text(encoding="utf-8")


def _extract_stt_engines() -> list[str]:
    match = re.search(r"STT_ENGINES\s*=\s*(\[[^\]]*\])", SETTINGS_COMMON_SRC)
    assert match, "Could not find STT_ENGINES = [...] in ui/settings/common.py"
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
