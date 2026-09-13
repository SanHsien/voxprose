"""真人 VAD 驗證腳本的純邏輯測試；不存取麥克風或真 ONNX 模型。"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

import numpy as np


SCRIPT = Path(__file__).parent / "manual" / "manual_audio_vad_check.py"
SPEC = importlib.util.spec_from_file_location("manual_audio_vad_check", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _SequenceVad:
    def __init__(self, values):
        self._values = iter(values)

    def compute_level(self, _block):
        return next(self._values)


def test_analyze_pcm_uses_same_audio_and_threshold_for_both_engines():
    pcm = np.full(1600, 1000, dtype=np.int16)
    result = MODULE.analyze_pcm(
        pcm,
        0.15,
        rms_factory=lambda: _SequenceVad([0.1, 0.2]),
        silero_factory=lambda: _SequenceVad([0.3, 0.05]),
    )

    assert result["samples"] == 1600
    assert result["rms"]["trigger_blocks"] == 1
    assert result["silero"]["trigger_blocks"] == 1
    assert result["rms"]["total_blocks"] == result["silero"]["total_blocks"] == 2


def test_assessment_passes_only_when_speech_works_and_silero_reduces_noise():
    def item(rms, silero, physical=0.01):
        return {
            "physical_rms": physical,
            "rms": {"triggered": rms},
            "silero": {"triggered": silero},
        }

    status, reasons = MODULE.assess_results(
        {
            "speech": item(True, True),
            "cough": item(True, False),
            "breathing": item(True, False),
            "ambient": item(False, False),
        }
    )

    assert status == "PASS"
    assert "RMS=2、Silero=0" in reasons[0]


def test_assessment_blocks_when_microphone_did_not_capture_speech():
    silent = {
        "physical_rms": 0.0,
        "rms": {"triggered": False},
        "silero": {"triggered": False},
    }
    status, reasons = MODULE.assess_results(
        {name: silent for name, _instruction in MODULE.SCENARIOS}
    )

    assert status == "BLOCKED"
    assert "能量過低" in reasons[0]


def test_source_override_rejects_incomplete_release_root(tmp_path):
    expected = tmp_path / "audio" / "vad" / "silero_vad.py"
    expected.parent.mkdir(parents=True)
    expected.write_text("# deliberately incomplete staging root\n", encoding="utf-8")
    env = os.environ.copy()
    env["VOXPROSE_SOURCE_ROOT"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=SCRIPT.parents[2],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )

    assert result.returncode == 1
    assert "VOXPROSE_SOURCE_ROOT" in result.stderr
    assert "rms_vad.py" in result.stderr
