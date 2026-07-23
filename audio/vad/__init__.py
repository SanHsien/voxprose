"""VAD 引擎抽象與工廠函式。

`audio/auto_trigger.py` 透過 `get_vad_engine()` 依 config 的 `vad_engine`
欄位（`"rms"`｜`"silero"`）取得引擎實例；狀態機（起音/靜音 hysteresis、
`min_speech_sec`、`max_segment_sec`）完全不變，只有「這塊音訊的語音強度」
這一步被抽換（見 `audio/vad/base.py`）。
"""
import logging

from audio.vad.base import BaseVAD
from audio.vad.rms_vad import RmsVAD

log = logging.getLogger("voicetype.vad")

__all__ = ["BaseVAD", "RmsVAD", "get_vad_engine", "describe_silero_availability"]


def get_vad_engine(engine: str = "rms") -> BaseVAD:
    """建立 VAD 引擎。

    `engine="silero"` 但 onnxruntime 未安裝，或模型下載/初始化失敗時，記一
    筆警告並優雅降級為 `RmsVAD`——絕不讓全時模式因此無法啟動或崩潰（見
    docs/DECISIONS.md 全時模式 VAD 引擎決策：「缺任一 → log 警告並 fallback
    rms」）。
    """
    if engine == "silero":
        try:
            from audio.vad.silero_vad import SileroVAD
            return SileroVAD()
        except ImportError as e:
            log.warning(f"[vad] onnxruntime 未安裝，Silero VAD 不可用，改用 RMS：{e}")
        except Exception as e:
            log.warning(f"[vad] Silero VAD 初始化失敗（模型下載或載入問題），改用 RMS：{e}")
    return RmsVAD()


def describe_silero_availability() -> tuple:
    """回傳 `(是否可用, 原因文案)`，給設定 UI 顯示誠實狀態用（比照
    `stt/cuda_check.py` 的 CUDA 三態文案原則：不確定的不要說可用）。只檢查
    onnxruntime 是否已安裝——模型檔案是首次啟用 Silero 時才下載，這裡不做
    網路呼叫，避免打開設定頁就觸發下載或卡住。"""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False, "未安裝 onnxruntime（需手動安裝：pip install onnxruntime）"
    return True, "可用（首次啟用時自動下載模型，約 2MB）"
