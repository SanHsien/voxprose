"""Tests for stt/gemini_stt.py's GeminiSTT.

Regression coverage for a bug found while wiring the "Gemini" STT engine into
get_stt() (REVIEW.md 2026-07-19): GeminiSTT.transcribe() used to call
soundfile.write(buf, audio_bytes, sample_rate, format="WAV") -- but the bytes
handed to it by ui/app.py (self.stt.transcribe(audio_data, language=lang)) are
already a fully-formed WAV file produced by AudioRecorder._to_wav_bytes(), not
a raw PCM sample array. Passing an already-encoded WAV blob to
soundfile.write's `data` parameter raises IndexError internally, which was
silently swallowed by the broad `except Exception` in transcribe() -- so this
engine always returned "" regardless of whether the API key was valid. The
fix drops the pointless soundfile re-encoding step entirely and base64-encodes
the incoming WAV bytes directly, matching the pattern already used by
stt/groq_whisper.py.

No real network calls are made: httpx.post is monkeypatched.
"""
import base64
import io
import wave

import numpy as np
import pytest

from stt.gemini_stt import GeminiSTT


def _make_wav_bytes(num_samples: int = 1600, samplerate: int = 16000) -> bytes:
    """Build a tiny valid WAV file, mirroring AudioRecorder._to_wav_bytes()."""
    audio = (np.random.rand(num_samples).astype(np.float32) * 1000).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


def test_transcribe_returns_empty_string_without_api_key():
    stt = GeminiSTT({"gemini_api_key": ""})
    assert stt.transcribe(_make_wav_bytes()) == ""


def test_transcribe_returns_empty_string_for_empty_audio():
    stt = GeminiSTT({"gemini_api_key": "test-key"})
    assert stt.transcribe(b"") == ""


def test_transcribe_sends_base64_of_the_original_wav_bytes_and_returns_text(monkeypatch):
    """This is the core regression check: previously this call path always
    raised IndexError internally (soundfile misuse) and silently returned "".
    """
    wav_bytes = _make_wav_bytes()
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse({
            "candidates": [{"content": {"parts": [{"text": "測試轉錄結果"}]}}]
        })

    monkeypatch.setattr("stt.gemini_stt.httpx.post", fake_post)

    gemini_stt = GeminiSTT({"gemini_api_key": "test-key", "gemini_stt_model": "gemini-2.0-flash", "language": "zh"})
    result = gemini_stt.transcribe(wav_bytes, language="zh")

    assert result == "測試轉錄結果"
    assert "test-key" in captured["url"]
    sent_audio_b64 = captured["json"]["contents"][0]["parts"][1]["inline_data"]["data"]
    assert base64.b64decode(sent_audio_b64) == wav_bytes  # exact round-trip, no re-encoding


def test_transcribe_swallows_http_errors_and_returns_empty_string(monkeypatch):
    def raising_post(*args, **kwargs):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr("stt.gemini_stt.httpx.post", raising_post)

    gemini_stt = GeminiSTT({"gemini_api_key": "test-key"})
    assert gemini_stt.transcribe(_make_wav_bytes()) == ""
