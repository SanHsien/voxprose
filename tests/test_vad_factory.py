"""Unit tests for audio/vad/__init__.py:get_vad_engine() — dispatch between
"rms"/"silero" and the graceful-fallback contract required by
docs/DECISIONS.md（全時模式 VAD 引擎決策）：

    「silero 需 onnxruntime 已安裝且模型可得，缺任一 → log 警告並 fallback
    rms（優雅降級，絕不崩潰）」

Three fallback scenarios covered, matching the acceptance criteria:
1. onnxruntime not installed at all (ImportError inside SileroVAD.__init__).
2. onnxruntime installed but model/session init fails for another reason
   (e.g. download failure, corrupt model) — any other Exception.
3. engine="rms" (or unset/unknown) — no Silero code path touched at all.
"""
import sys
import types

import pytest

from audio.vad import describe_silero_availability, get_vad_engine
from audio.vad.rms_vad import RmsVAD


def test_default_engine_is_rms():
    vad = get_vad_engine()
    assert isinstance(vad, RmsVAD)


def test_explicit_rms_engine():
    vad = get_vad_engine("rms")
    assert isinstance(vad, RmsVAD)


def test_unknown_engine_name_falls_back_to_rms():
    """未知字串（例如設定檔被手動改壞）也要優雅降級，不得拋例外。"""
    vad = get_vad_engine("not-a-real-engine")
    assert isinstance(vad, RmsVAD)


def test_silero_missing_onnxruntime_falls_back_to_rms(monkeypatch, caplog):
    """情境 1：onnxruntime 完全沒裝。"""
    monkeypatch.setitem(sys.modules, "onnxruntime", None)

    with caplog.at_level("WARNING"):
        vad = get_vad_engine("silero")

    assert isinstance(vad, RmsVAD)
    assert any("onnxruntime" in rec.message for rec in caplog.records)


def test_silero_init_failure_falls_back_to_rms(monkeypatch, caplog):
    """情境 2：onnxruntime 裝了，但模型下載/載入失敗（其他例外）。"""
    fake_ort = types.ModuleType("onnxruntime")

    def _raise(*args, **kwargs):
        raise RuntimeError("model download failed: network unreachable")

    fake_ort.InferenceSession = _raise
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    # Force ensure_model_downloaded() to fail deterministically without
    # touching the network or real %APPDATA%.
    import audio.vad.silero_vad as silero_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("model download failed: network unreachable")

    monkeypatch.setattr(silero_mod, "ensure_model_downloaded", _boom)

    with caplog.at_level("WARNING"):
        vad = get_vad_engine("silero")

    assert isinstance(vad, RmsVAD)
    assert any("Silero VAD" in rec.message for rec in caplog.records)


def test_silero_success_path_returns_silero_instance(monkeypatch, tmp_path):
    """情境 3（正常路徑的鏡像）：onnxruntime 存在且模型/session 都成功時，
    get_vad_engine 必須真的回傳 SileroVAD 而不是誤降級。"""
    fake_ort = types.ModuleType("onnxruntime")

    class _FakeSession:
        def __init__(self, *args, **kwargs):
            pass

    fake_ort.InferenceSession = _FakeSession
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    model_file = tmp_path / "silero_vad.onnx"
    model_file.write_bytes(b"fake-onnx-bytes")

    import audio.vad.silero_vad as silero_mod
    monkeypatch.setattr(silero_mod, "ensure_model_downloaded", lambda *a, **k: model_file)

    from audio.vad.silero_vad import SileroVAD

    vad = get_vad_engine("silero")
    assert isinstance(vad, SileroVAD)


def test_describe_silero_availability_reports_missing_onnxruntime(monkeypatch):
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    available, reason = describe_silero_availability()
    assert available is False
    assert "onnxruntime" in reason


def test_describe_silero_availability_reports_available(monkeypatch):
    fake_ort = types.ModuleType("onnxruntime")
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)
    available, reason = describe_silero_availability()
    assert available is True
    assert reason  # non-empty honest message


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
