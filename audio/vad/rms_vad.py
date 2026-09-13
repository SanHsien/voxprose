"""RMS 能量 VAD — 把 `audio/auto_trigger.py` 原本內嵌的能量計算原封不動
包裝成 `BaseVAD` 介面。刻意逐行搬移、不做任何數值調整，確保這是全時模式
既有行為的位元級不變版本（見 docs/DECISIONS.md 全時模式 VAD 引擎決策，
以及 `tests/test_vad_rms.py` 的回歸驗證）。"""
import numpy as np

from audio.vad.base import BaseVAD


class RmsVAD(BaseVAD):
    """預設引擎（`vad_engine="rms"`）。無任何額外依賴，永遠可用。"""

    def compute_level(self, indata: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
        return min(rms * 10, 1.0)
