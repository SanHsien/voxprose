"""Pure PCM gain / AGC math for audio/recorder.py.

Split out from audio/recorder.py so this logic can be unit-tested without
needing `sounddevice` installed (audio/recorder.py imports sounddevice at
module load time and therefore cannot be imported in an environment that
lacks the PortAudio bindings; this module only depends on numpy).

Ported from the Mac mainline (`git show 51094bf:audio/recorder.py`, v2.9.7,
items 7-2/7-3 in docs/mac-mainline-absorption-analysis.md):
- 7-2 manual gain: real PCM amplification (not just a visual meter), 50~300
  (%), clipped to int16 range.
- 7-3 AGC: an independent `_agc_factor` that adapts to recent peak loudness
  without ever overwriting the user's manual gain setting.

Also holds the item 7-4 post-recording silence precheck (same source file,
`51094bf:audio/recorder.py:8,158-163`): after stop(), if the loudest chunk of
the whole recording never rose above SILENCE_THRESHOLD, the recording is
flagged silent so the caller can skip an STT round-trip entirely instead of
sending dead air (and risking a Whisper hallucination on top of it).
"""
import numpy as np

# AGC 動態調整參數（51094bf:audio/recorder.py:120-131 移植）
AGC_MIN_FACTOR = 0.1
AGC_MAX_FACTOR = 8.0
AGC_GROW_RATE = 1.15    # 太安靜時放大 AGC 的速率
AGC_SHRINK_RATE = 0.88  # 快飽和時縮小 AGC 的速率
AGC_LOW_WATERMARK = 0.30   # 近期峰值低於此值視為太安靜
AGC_HIGH_WATERMARK = 0.85  # 近期峰值高於此值視為快飽和
AGC_WINDOW = 10  # 用最近幾個 chunk 的峰值判斷

# 7-4：放大後任一 chunk 峰值 RMS < 0.3% 才視為整段靜音（51094bf:audio/recorder.py:8）
SILENCE_THRESHOLD = 0.003


def effective_gain_factor(gain: int, agc_factor: float) -> float:
    """有效放大倍率 = 手動 gain(50~300) × AGC 動態係數。"""
    return (gain / 100.0) * agc_factor


def apply_gain(indata: np.ndarray, gain: int, agc_factor: float) -> np.ndarray:
    """對 int16 PCM 樣本套用實際放大（非純視覺），clip 避免溢位。"""
    factor = effective_gain_factor(gain, agc_factor)
    if factor == 1.0:
        return indata
    return np.clip(
        indata.astype(np.float32) * factor, -32768, 32767
    ).astype(np.int16)


def rms_of(samples: np.ndarray) -> float:
    """計算 int16 PCM chunk 的正規化 RMS（0.0~1.0）。"""
    return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2))) / 32768.0


def peak_rms(frames: list) -> float:
    """整段錄音的峰值 RMS：逐 chunk 算 RMS，取其中最大值。

    用峰值而非平均值，是為了避免長段錄音中間夾雜長靜音時把平均值拉低、
    誤判整段為靜音（只要任何一段有聲音就不算靜音）。frames 為空時視為 0.0
    （呼叫端應視為靜音）。
    """
    if not frames:
        return 0.0
    return max(rms_of(chunk) for chunk in frames)


def is_silent(frames: list, threshold: float = SILENCE_THRESHOLD) -> bool:
    """7-4：錄音是否整段靜音（峰值 RMS 低於門檻），可跳過 STT。"""
    return peak_rms(frames) < threshold


def update_agc_factor(recent_peaks: list, current_factor: float) -> float:
    """AGC：根據近期峰值動態調整並回傳新的 _agc_factor，不動手動 gain。

    recent_peaks 應已包含最新一筆 rms（呼叫端負責 append/裁剪視窗長度）。
    """
    if len(recent_peaks) < AGC_WINDOW:
        return current_factor
    peak = max(recent_peaks[-AGC_WINDOW:])
    if peak <= 0:
        return current_factor
    if peak < AGC_LOW_WATERMARK:
        return min(current_factor * AGC_GROW_RATE, AGC_MAX_FACTOR)
    if peak > AGC_HIGH_WATERMARK:
        return max(current_factor * AGC_SHRINK_RATE, AGC_MIN_FACTOR)
    return current_factor
