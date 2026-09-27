"""Tests that the two SDK-based providers which previously had no explicit
network timeout (REVIEW.md 第 3 節「網路請求逾時」) now pass one through to
their client constructor instead of relying on the SDK's own long default
(anthropic/groq SDKs default to 600s).

Both use the shared net_config.CLOUD_REQUEST_TIMEOUT_SECONDS constant. The
httpx/requests-based providers that already carried their own per-call
timeout (llm/ollama.py, llm/openai_llm.py, llm/openrouter.py, llm/gemini.py,
llm/deepseek.py, llm/qwen.py, stt/gemini_stt.py, stt/openrouter_stt.py,
actions/builtins.py) are intentionally untouched and not covered here.

Like tests/test_smoke.py's OPTIONAL_DEPENDENCY_MODULES, these only run when
the optional provider SDK (anthropic / groq) is actually installed —
this repo's convention is not to install heavy/optional deps just for tests
(AGENTS.md / docs/DEVELOPMENT.md).
"""
from net_config import CLOUD_REQUEST_TIMEOUT_SECONDS

import pytest


def test_claude_llm_client_gets_explicit_timeout(monkeypatch):
    anthropic = pytest.importorskip("anthropic")
    from llm.claude import ClaudeLLM

    captured = {}

    def fake_init(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(anthropic.Anthropic, "__init__", fake_init)

    ClaudeLLM({"anthropic_api_key": "sk-test", "anthropic_model": "claude-3-haiku-20240307"})

    assert captured.get("timeout") == CLOUD_REQUEST_TIMEOUT_SECONDS


def test_groq_whisper_client_gets_explicit_timeout(monkeypatch):
    groq = pytest.importorskip("groq")
    from stt.groq_whisper import GroqWhisperSTT

    captured = {}

    def fake_init(self, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(groq.Groq, "__init__", fake_init)

    GroqWhisperSTT({"groq_api_key": "gsk-test"})

    assert captured.get("timeout") == CLOUD_REQUEST_TIMEOUT_SECONDS
