"""Unit tests for audio/vad/rms_vad.py — RmsVAD 必須與
audio/auto_trigger.py 移除前的內嵌 RMS 公式位元級一致（見
docs/DECISIONS.md 全時模式 VAD 引擎決策）。

無任何額外依賴（只用 numpy），與 audio/gain.py 的測試風格一致，不需要
sounddevice/onnxruntime 就能跑。
"""
import numpy as np
import pytest

from audio.vad.base import BaseVAD
from audio.vad.rms_vad import RmsVAD


def _reference_level(indata: np.ndarray) -> float:
    """auto_trigger.py 重構前的原始公式，原封不動搬來當比對基準。"""
    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
    return min(rms * 10, 1.0)


def test_rms_vad_is_a_base_vad():
    assert isinstance(RmsVAD(), BaseVAD)


def test_silence_gives_zero_level():
    vad = RmsVAD()
    silent = np.zeros((800, 1), dtype=np.int16)
    assert vad.compute_level(silent) == 0.0


def test_full_scale_saturates_at_one():
    vad = RmsVAD()
    loud = np.full((800, 1), 32767, dtype=np.int16)
    assert vad.compute_level(loud) == 1.0


@pytest.mark.parametrize("amplitude", [50, 500, 2000, 5000, 15000, 32767])
def test_matches_reference_formula_bit_for_bit(amplitude):
    vad = RmsVAD()
    indata = np.full((800, 1), amplitude, dtype=np.int16)
    assert vad.compute_level(indata) == _reference_level(indata)


def test_negative_amplitude_treated_same_as_positive():
    vad = RmsVAD()
    pos = np.full((800, 1), 5000, dtype=np.int16)
    neg = np.full((800, 1), -5000, dtype=np.int16)
    assert vad.compute_level(pos) == vad.compute_level(neg)


def test_reset_is_a_noop_and_does_not_raise():
    vad = RmsVAD()
    vad.reset()  # RMS has no cross-block state; must not error.
    indata = np.full((800, 1), 1000, dtype=np.int16)
    assert vad.compute_level(indata) == _reference_level(indata)
