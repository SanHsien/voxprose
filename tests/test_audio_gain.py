"""Unit tests for audio/gain.py — pure PCM gain/AGC math ported from the Mac
mainline (`git show 51094bf:audio/recorder.py`, v2.9.7).

Covers docs/mac-mainline-absorption-analysis.md items:
- 7-2 manual gain: real PCM amplification (not just a UI meter), clipped.
- 7-3 AGC: independent dynamic factor that never overwrites manual gain.
- 7-4 silence precheck: skip STT entirely when the whole recording's peak
  RMS never rises above SILENCE_THRESHOLD.

This module deliberately has no sounddevice/PyQt6 dependency (see module
docstring in audio/gain.py) so these tests run unconditionally, unlike
audio/recorder.py itself which needs sounddevice to even import.
"""
import unittest

import numpy as np

from audio.gain import (
    AGC_HIGH_WATERMARK,
    AGC_LOW_WATERMARK,
    AGC_MAX_FACTOR,
    AGC_MIN_FACTOR,
    AGC_WINDOW,
    SILENCE_THRESHOLD,
    apply_gain,
    effective_gain_factor,
    is_silent,
    peak_rms,
    rms_of,
    update_agc_factor,
)


class EffectiveGainFactorTest(unittest.TestCase):
    def test_gain_100_and_agc_1_is_unity(self):
        self.assertEqual(effective_gain_factor(100, 1.0), 1.0)

    def test_manual_gain_scales_linearly(self):
        self.assertAlmostEqual(effective_gain_factor(200, 1.0), 2.0)
        self.assertAlmostEqual(effective_gain_factor(50, 1.0), 0.5)

    def test_agc_factor_multiplies_on_top_of_manual_gain(self):
        self.assertAlmostEqual(effective_gain_factor(200, 2.0), 4.0)


class ApplyGainTest(unittest.TestCase):
    def test_unity_gain_returns_same_array_untouched(self):
        indata = np.array([[100], [-200], [300]], dtype=np.int16)
        out = apply_gain(indata, gain=100, agc_factor=1.0)
        np.testing.assert_array_equal(out, indata)

    def test_gain_actually_amplifies_pcm_samples(self):
        indata = np.array([[1000], [-1000]], dtype=np.int16)
        out = apply_gain(indata, gain=200, agc_factor=1.0)  # x2.0
        np.testing.assert_array_equal(out, np.array([[2000], [-2000]], dtype=np.int16))

    def test_gain_clips_to_int16_range_without_overflow_wraparound(self):
        indata = np.array([[30000], [-30000]], dtype=np.int16)
        out = apply_gain(indata, gain=300, agc_factor=1.0)  # x3.0 -> would overflow int16
        # Must clip to the valid int16 range, not wrap around to negative/positive garbage.
        self.assertTrue(np.all(out <= 32767))
        self.assertTrue(np.all(out >= -32768))
        self.assertEqual(out[0][0], 32767)
        self.assertEqual(out[1][0], -32768)

    def test_agc_factor_also_applies(self):
        indata = np.array([[1000]], dtype=np.int16)
        out = apply_gain(indata, gain=100, agc_factor=3.0)
        np.testing.assert_array_equal(out, np.array([[3000]], dtype=np.int16))


class RmsOfTest(unittest.TestCase):
    def test_silence_is_zero(self):
        silent = np.zeros((100, 1), dtype=np.int16)
        self.assertEqual(rms_of(silent), 0.0)

    def test_full_scale_is_close_to_one(self):
        loud = np.full((100, 1), 32767, dtype=np.int16)
        self.assertGreater(rms_of(loud), 0.99)


class UpdateAgcFactorTest(unittest.TestCase):
    def test_factor_unchanged_until_window_is_full(self):
        peaks = [0.01] * (AGC_WINDOW - 1)  # one short of the window
        self.assertEqual(update_agc_factor(peaks, 1.0), 1.0)

    def test_quiet_signal_grows_factor(self):
        peaks = [0.05] * AGC_WINDOW  # well below AGC_LOW_WATERMARK
        new_factor = update_agc_factor(peaks, 1.0)
        self.assertGreater(new_factor, 1.0)

    def test_loud_signal_shrinks_factor(self):
        peaks = [0.95] * AGC_WINDOW  # well above AGC_HIGH_WATERMARK
        new_factor = update_agc_factor(peaks, 2.0)
        self.assertLess(new_factor, 2.0)

    def test_moderate_signal_leaves_factor_unchanged(self):
        peaks = [(AGC_LOW_WATERMARK + AGC_HIGH_WATERMARK) / 2] * AGC_WINDOW
        self.assertEqual(update_agc_factor(peaks, 1.5), 1.5)

    def test_factor_never_exceeds_max(self):
        peaks = [0.0001] * AGC_WINDOW
        factor = AGC_MAX_FACTOR
        # Already at the ceiling: repeated quiet peaks must not push it higher.
        self.assertEqual(update_agc_factor(peaks, factor), AGC_MAX_FACTOR)

    def test_factor_never_goes_below_min(self):
        peaks = [1.0] * AGC_WINDOW
        factor = AGC_MIN_FACTOR
        self.assertEqual(update_agc_factor(peaks, factor), AGC_MIN_FACTOR)

    def test_does_not_mutate_manual_gain_concept(self):
        """AGC only ever returns a new _agc_factor; the manual gain value
        itself is a separate, untouched input (see effective_gain_factor)."""
        peaks = [0.9] * AGC_WINDOW
        agc_factor = update_agc_factor(peaks, 1.0)
        # Manual gain of 200 combined with the shrunk AGC factor should not
        # collapse back to the raw manual-gain-only value.
        self.assertNotEqual(effective_gain_factor(200, agc_factor), 2.0)


class PeakRmsAndSilenceTest(unittest.TestCase):
    """7-4: post-recording silence precheck (docs/mac-mainline-absorption-analysis.md)."""

    def test_peak_rms_of_empty_frames_is_zero(self):
        self.assertEqual(peak_rms([]), 0.0)

    def test_peak_rms_takes_the_loudest_chunk_not_the_average(self):
        silent_chunk = np.zeros((100, 1), dtype=np.int16)
        loud_chunk = np.full((100, 1), 32767, dtype=np.int16)
        # A long recording that is mostly silence but has one loud chunk in
        # the middle must not be washed out by averaging.
        frames = [silent_chunk] * 20 + [loud_chunk] + [silent_chunk] * 20
        self.assertGreater(peak_rms(frames), 0.9)

    def test_is_silent_true_for_no_frames(self):
        self.assertTrue(is_silent([]))

    def test_is_silent_true_when_all_frames_below_threshold(self):
        quiet = [np.full((100, 1), 5, dtype=np.int16) for _ in range(10)]  # tiny amplitude
        self.assertTrue(is_silent(quiet))

    def test_is_silent_false_when_any_chunk_has_real_speech(self):
        silent_chunk = np.zeros((100, 1), dtype=np.int16)
        # amplitude well above the 0.3% threshold
        speech_chunk = np.full((100, 1), 2000, dtype=np.int16)
        frames = [silent_chunk] * 5 + [speech_chunk] + [silent_chunk] * 5
        self.assertFalse(is_silent(frames))

    def test_default_threshold_is_0_3_percent(self):
        self.assertAlmostEqual(SILENCE_THRESHOLD, 0.003)

    def test_custom_threshold_is_respected(self):
        chunk = np.full((100, 1), 2000, dtype=np.int16)  # rms ~ 0.061
        self.assertFalse(is_silent([chunk], threshold=0.003))
        self.assertTrue(is_silent([chunk], threshold=0.5))


if __name__ == "__main__":
    unittest.main()
