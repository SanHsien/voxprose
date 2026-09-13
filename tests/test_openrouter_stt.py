"""Tests for stt/openrouter_stt.py's OpenRouterSTT.

Same-pattern regression coverage as tests/test_gemini_stt.py: transcribe()
used to (a) declare the signature (audio_data, sample_rate=16000) while the
caller ui/app.py invokes self.stt.transcribe(audio_data, language=lang) --
an immediate TypeError -- and (b) call
soundfile.write(buf, audio_bytes, sample_rate, format="WAV") on bytes that
are already a fully-formed WAV file from AudioRecorder._to_wav_bytes(),
raising IndexError internally, silently swallowed by the broad
`except Exception`, so the engine always returned "". The fix drops the
soundfile re-encoding, uploads the original WAV bytes directly, and aligns
the signature with BaseSTT's (audio_bytes, language="zh").

No real network calls are made: httpx.post is monkeypatched.
"""
import io
import wave

import numpy as np

from stt.openrouter_stt import OpenRouterSTT


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
    stt = OpenRouterSTT({"openrouter_api_key": ""})
    assert stt.transcribe(_make_wav_bytes()) == ""


def test_transcribe_returns_empty_string_for_empty_audio():
    stt = OpenRouterSTT({"openrouter_api_key": "test-key"})
    assert stt.transcribe(b"") == ""


def test_transcribe_uploads_the_original_wav_bytes_and_returns_text(monkeypatch):
    """Core regression check: previously this call path always raised
    IndexError internally (soundfile misuse) and silently returned "".
    """
    wav_bytes = _make_wav_bytes()
    captured = {}

    def fake_post(url, headers, files, data, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["files"] = files
        captured["data"] = data
        captured["timeout"] = timeout
        return _FakeResponse({"text": "  測試轉錄結果  "})

    monkeypatch.setattr("stt.openrouter_stt.httpx.post", fake_post)

    stt = OpenRouterSTT({"openrouter_api_key": "test-key", "language": "zh"})
    result = stt.transcribe(wav_bytes, language="zh")

    assert result == "測試轉錄結果"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    # The uploaded file must be the exact original WAV bytes, no re-encoding.
    filename, file_obj, mime = captured["files"]["file"]
    assert filename == "audio.wav"
    assert mime == "audio/wav"
    assert file_obj.getvalue() == wav_bytes


def test_transcribe_passes_caller_language_to_the_api(monkeypatch):
    """The caller (ui/app.py) passes language= per call; it must win over the
    config-level default captured at construction time."""
    captured = {}

    def fake_post(url, headers, files, data, timeout):
        captured["data"] = data
        return _FakeResponse({"text": "ok"})

    monkeypatch.setattr("stt.openrouter_stt.httpx.post", fake_post)

    stt = OpenRouterSTT({"openrouter_api_key": "test-key", "language": "zh"})
    stt.transcribe(_make_wav_bytes(), language="en")

    assert captured["data"]["language"] == "en"


def test_transcribe_swallows_http_errors_and_returns_empty_string(monkeypatch):
    def raising_post(*args, **kwargs):
        raise RuntimeError("simulated network failure")

    monkeypatch.setattr("stt.openrouter_stt.httpx.post", raising_post)

    stt = OpenRouterSTT({"openrouter_api_key": "test-key"})
    assert stt.transcribe(_make_wav_bytes()) == ""
