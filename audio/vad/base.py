"""VAD (Voice Activity Detection) 引擎抽象介面。

`audio/auto_trigger.py` 的全時模式狀態機（起音/靜音 hysteresis、
min_speech_sec、max_segment_sec 等時間邏輯與 sensitivity 門檻比對）完全由
`AutoTriggerController` 負責，不因引擎不同而改變；引擎只需要回答一個問題：
「這一塊音訊的語音強度是多少（0~1 尺度）」。

RMS 引擎（`rms_vad.py`）回傳能量正規化值，Silero 引擎（`silero_vad.py`）
回傳神經網路判斷的語音機率——兩者天然都落在 0~1 區間，因此共用同一套
`auto_trigger_sensitivity`/`auto_trigger_silence_sec` 門檻語義，使用者既有
設定不需要因為切換引擎而重新調整（見 docs/DECISIONS.md 全時模式 VAD
引擎決策）。
"""
from abc import ABC, abstractmethod

import numpy as np


class BaseVAD(ABC):
    """VAD 引擎介面。實作只需要處理「這塊音訊像不像語音」，不涉及任何
    hysteresis/計時邏輯（那些留在 AutoTriggerController）。"""

    @abstractmethod
    def compute_level(self, indata: np.ndarray) -> float:
        """輸入一塊單聲道 int16 PCM（sounddevice callback 的 indata，形狀
        `(frames, 1)` 或 `(frames,)`），回傳 0~1 的語音強度／機率。"""
        raise NotImplementedError

    def reset(self) -> None:
        """串流重新開始時呼叫（`AutoTriggerController.start()`），用來清除
        任何跨 block 的內部狀態（例如 Silero 的 LSTM state）。RMS 引擎沒有
        這類狀態，預設 no-op，子類別視需要覆寫。"""
        pass
