"""Unit tests for audio/vad/silero_vad.py — window buffering/state-passing
logic and the first-use model download, all with a mocked onnxruntime
session/requests (no network, no real ~2MB download). The real model is
separately exercised in scratchpad/venv_real (see docs/DECISIONS.md — 真
模型實測數字).
"""
import sys
import types

import numpy as np
import pytest

from audio.vad.base import BaseVAD
from audio.vad.silero_vad import (
    CONTEXT_SAMPLES,
    SAMPLE_RATE,
    WINDOW_SAMPLES,
    SileroVAD,
    ensure_model_downloaded,
)

MODEL_INPUT_LEN = CONTEXT_SAMPLES + WINDOW_SAMPLES  # 576: context prefix + new window


class _FakeSession:
    """Records every call and returns a scripted probability sequence, so
    tests can assert exactly how many 512-sample windows were run and with
    what state/context, without needing a real ONNX graph."""

    def __init__(self, probs=None):
        self.calls = []
        self._probs = list(probs) if probs is not None else None
        self._next_state_marker = 0

    def run(self, output_names, feed):
        assert output_names == ["output", "stateN"]
        assert feed["input"].shape == (1, MODEL_INPUT_LEN)
        assert feed["state"].shape == (2, 1, 128)
        assert int(feed["sr"]) == SAMPLE_RATE
        self.calls.append(feed["input"].copy())

        if self._probs is not None:
            prob = self._probs[len(self.calls) - 1]
        else:
            prob = 0.5

        self._next_state_marker += 1
        new_state = np.full((2, 1, 128), float(self._next_state_marker), dtype=np.float32)
        return np.array([[prob]], dtype=np.float32), new_state


def test_silero_vad_is_a_base_vad():
    vad = SileroVAD(session=_FakeSession())
    assert isinstance(vad, BaseVAD)


def test_block_smaller_than_window_buffers_without_calling_model():
    """BLOCK_SEC(=50ms)*16kHz = 800 樣本 > 512，所以正常情況下每個 block 都
    會觸發至少一次推論；這裡故意丟一個小於 512 的區塊，驗證還沒湊滿一個
    窗口前不應該呼叫模型（level 回傳 0.0，不是誤判）。"""
    session = _FakeSession()
    vad = SileroVAD(session=session)

    indata = np.zeros((100, 1), dtype=np.int16)  # far fewer than WINDOW_SAMPLES
    level = vad.compute_level(indata)

    assert level == 0.0
    assert session.calls == []


def test_800_sample_block_runs_exactly_one_window_and_buffers_remainder():
    """真實 auto_trigger.py 的 callback 每次丟 800 樣本（BLOCK_SEC=0.05 @
    16kHz），512 樣本一個窗口，應該恰好觸發一次推論，剩下 288 樣本留到下次。"""
    session = _FakeSession(probs=[0.42])
    vad = SileroVAD(session=session)

    indata = np.full((800, 1), 1000, dtype=np.int16)
    level = vad.compute_level(indata)

    assert len(session.calls) == 1
    assert level == pytest.approx(0.42)
    assert len(vad._buffer) == 800 - WINDOW_SAMPLES  # 288 leftover samples


def test_state_is_threaded_across_consecutive_calls():
    """LSTM state 必須是上一次呼叫的輸出，餵進下一次呼叫（跨 block 延續
    上下文），不能每次都重新歸零。"""
    session = _FakeSession(probs=[0.1, 0.2, 0.3])
    vad = SileroVAD(session=session)

    vad.compute_level(np.full((800, 1), 1000, dtype=np.int16))  # 800 -> 1 window, 288 leftover, marker 1
    vad.compute_level(np.full((800, 1), 1000, dtype=np.int16))  # 288+800=1088 -> 2 windows, marker 2, 3
    # Each _FakeSession.run() call bumps the marker by 1; if state were
    # reset to zero between calls (bug) the final marker would be 1, not 3.
    assert np.all(vad._state == 3.0)


def test_multiple_windows_in_one_block_takes_max_probability():
    """緩衝區累積到能跑兩個窗口時，這次 callback 的 level 要是「這個 block
    涵蓋到的所有窗口裡最高的機率」（保守判斷，避免語音只出現在其中一個
    窗口卻被另一個安靜窗口拉低平均）。"""
    session = _FakeSession(probs=[0.1, 0.9])
    vad = SileroVAD(session=session)
    # Pre-fill the buffer so this call covers exactly two windows (1024 samples).
    vad._buffer = np.zeros((1024,), dtype=np.float32)

    level = vad.compute_level(np.zeros((0, 1), dtype=np.int16))

    assert len(session.calls) == 2
    assert level == pytest.approx(0.9)


def test_reset_clears_buffer_state_and_context():
    session = _FakeSession(probs=[0.7])
    vad = SileroVAD(session=session)
    vad.compute_level(np.full((800, 1), 1000, dtype=np.int16))
    assert len(vad._buffer) > 0
    assert np.any(vad._state != 0)

    vad.reset()

    assert len(vad._buffer) == 0
    assert np.all(vad._state == 0)
    assert vad._context.shape == (CONTEXT_SAMPLES,)
    assert np.all(vad._context == 0)


def test_context_prefix_carries_last_samples_of_previous_window():
    """每次推論要帶上「上一個窗口最後 CONTEXT_SAMPLES 個樣本」當前綴——
    第一版實作漏掉這個前綴，真模型實測發現真實語音機率貼近 0 才抓到
    （見 docs/DECISIONS.md）。這裡驗證 context 確實是上一個窗口的尾段。"""
    session = _FakeSession(probs=[0.5, 0.5])
    vad = SileroVAD(session=session)

    first_window = np.arange(1, WINDOW_SAMPLES + 1, dtype=np.int16).reshape(-1, 1)
    vad.compute_level(first_window)
    first_call_input = session.calls[0].reshape(-1)
    # First call: context starts at all-zero, so the tail of the fed input
    # (after the zero context prefix) must equal the raw first window.
    expected_first_pcm = (first_window.reshape(-1).astype(np.float32) / 32768.0)
    np.testing.assert_allclose(first_call_input[CONTEXT_SAMPLES:], expected_first_pcm)
    assert np.all(first_call_input[:CONTEXT_SAMPLES] == 0.0)

    second_window = np.arange(1, WINDOW_SAMPLES + 1, dtype=np.int16).reshape(-1, 1) * 2
    vad.compute_level(second_window)
    second_call_input = session.calls[1].reshape(-1)
    # Second call's context prefix must equal the last CONTEXT_SAMPLES
    # samples of the first window (not zeros, not the second window).
    np.testing.assert_allclose(second_call_input[:CONTEXT_SAMPLES], expected_first_pcm[-CONTEXT_SAMPLES:])


def test_level_never_exceeds_valid_probability_range():
    session = _FakeSession(probs=[0.999999])
    vad = SileroVAD(session=session)
    level = vad.compute_level(np.full((800, 1), 30000, dtype=np.int16))
    assert 0.0 <= level <= 1.0


# ── ensure_model_downloaded() ──

def test_ensure_model_downloaded_skips_when_already_cached(tmp_path):
    dest = tmp_path / "silero_vad.onnx"
    dest.write_bytes(b"already-here")

    result = ensure_model_downloaded(dest_dir=tmp_path)

    assert result == dest
    assert result.read_bytes() == b"already-here"


def test_ensure_model_downloaded_fetches_when_missing(tmp_path, monkeypatch):
    fake_requests = types.ModuleType("requests")

    class _FakeResponse:
        content = b"fake-model-bytes"

        def raise_for_status(self):
            pass

    calls = []

    def _fake_get(url, timeout=None):
        calls.append((url, timeout))
        return _FakeResponse()

    fake_requests.get = _fake_get
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    result = ensure_model_downloaded(dest_dir=tmp_path)

    assert result.read_bytes() == b"fake-model-bytes"
    assert len(calls) == 1
    assert calls[0][0].startswith("https://raw.githubusercontent.com/snakers4/silero-vad/")


def test_ensure_model_downloaded_propagates_network_errors(tmp_path, monkeypatch):
    """下載失敗必須讓例外往上傳，讓 get_vad_engine() 的 fallback 邏輯接住
    ——這裡本身不能吞掉錯誤，否則呼叫端會誤以為模型已就緒。"""
    fake_requests = types.ModuleType("requests")

    def _fake_get(url, timeout=None):
        raise ConnectionError("no internet")

    fake_requests.get = _fake_get
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    with pytest.raises(ConnectionError):
        ensure_model_downloaded(dest_dir=tmp_path)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
