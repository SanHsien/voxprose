"""Silero VAD（onnxruntime 版）— 神經網路語音偵測，取代 RMS 能量門檻判斷
（來源啟發：`docs/REFERENCES.md` 第 4 節，MIT 授權，snakers4/silero-vad）。

**後端選擇（onnxruntime 而非 torch）**：torch 完整安裝約 2GB，塞不進可攜
打包版；onnxruntime CPU 版只有數十 MB，模型本身（ONNX 版）約 2.2MB。

**依賴狀態**：`requirements-win.txt` 直接宣告 `onnxruntime>=1.14,<2`；
這是版本範圍而非單版 pin，pip 會依 Python 3.10–3.14 各自挑選有相容 wheel
的版本。自行裁切依賴的精簡環境若缺少它，
`audio/vad/__init__.py:get_vad_engine()` 會捕捉 `ImportError` 並優雅降級回 RMS。

**模型取得**：首次使用時下載到 `%APPDATA%\\VoxProse\\models\\silero_vad.onnx`
（比照 `tools/download_models.py` 的 Whisper 模型下載模式），來源釘住
snakers4/silero-vad 的穩定 tag（`v6.2.1`，非 `master` 分支，避免上游更新
造成不可預期的行為變化）——下載/模型缺失時同樣優雅降級回 RMS。

**推論介面（實測驗證，非憑印象）**：模型輸入 `input`（`float32[1, N]` PCM，
16kHz 每步驟固定吃 512 樣本的新音訊——其他長度會在內部 LSTM 節點丟
`INVALID_ARGUMENT`，已用 onnxruntime 1.27.0 實機驗證）、`state`
（`float32[2, 1, 128]` LSTM 狀態，跨呼叫延續）、`sr`（`int64` 純量取樣率）；
輸出 `output`（`float32[1, 1]` 語音機率）與 `stateN`（更新後的狀態）。

**context 前綴（實測抓出的第一版 bug，見 docs/DECISIONS.md）**：v5/v6 系列
模型實際吃的窗口不是單純 512 樣本，而是「上一步驟最後 64 樣本(context) +
這一步驟新的 512 樣本」共 576 樣本（比對官方 `utils_vad.py:
OnnxWrapper.__call__` 得出）。第一版實作只餵純 512 樣本、沒帶 context，
真模型實測發現真實語音音檔的機率始終貼近 0——跟純靜音/雜音幾乎無法區分；
補上 context 前綴後才恢復正常判別力（數字見 docs/DECISIONS.md 真模型
實測記錄）。
"""
import logging
from pathlib import Path
from typing import Optional

import numpy as np

from audio.vad.base import BaseVAD

log = logging.getLogger("voicetype.vad")

# 釘住穩定 tag（非 master），確保下載內容可重現；MIT 授權見 NOTICE.md。
MODEL_URL = (
    "https://raw.githubusercontent.com/snakers4/silero-vad/"
    "v6.2.1/src/silero_vad/data/silero_vad.onnx"
)
MODEL_FILENAME = "silero_vad.onnx"
SAMPLE_RATE = 16000
# 16kHz 模型每步驟固定吃 512 樣本(=32ms)的新音訊，非本專案 BLOCK_SEC(=50ms=
# 800 樣本)的整數倍，SileroVAD 內部用緩衝區吸收兩者的差異（見 compute_level）。
WINDOW_SAMPLES = 512
# 每步驟另外要帶上一步驟最後 64 樣本當 context 前綴（見上方模組說明），
# 實際餵進模型的長度是 CONTEXT_SAMPLES + WINDOW_SAMPLES = 576。
CONTEXT_SAMPLES = 64


def _default_model_dir() -> Path:
    from paths import APP_DATA_DIR
    return APP_DATA_DIR / "models"


def ensure_model_downloaded(dest_dir: Optional[Path] = None) -> Path:
    """回傳模型檔路徑；本機不存在就下載一份。下載失敗會拋出例外，由呼叫端
    （`get_vad_engine`）負責優雅降級，這裡不吞例外。"""
    dest_dir = dest_dir if dest_dir is not None else _default_model_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / MODEL_FILENAME
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    import requests

    log.info(f"[vad] Downloading Silero VAD model to {dest} ...")
    resp = requests.get(MODEL_URL, timeout=30)
    resp.raise_for_status()
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(resp.content)
    tmp.replace(dest)
    log.info(f"[vad] Silero VAD model downloaded ({dest.stat().st_size} bytes).")
    return dest


class SileroVAD(BaseVAD):
    """包裝 onnxruntime `InferenceSession`。"""

    def __init__(self, model_path: Optional[Path] = None, session=None):
        # session 參數只給測試用（注入 mock InferenceSession，不必真的裝
        # onnxruntime/下載模型）；正常路徑一律經由 onnxruntime 建立。
        if session is not None:
            self._session = session
            self.model_path = model_path
        else:
            import onnxruntime as ort

            self.model_path = model_path if model_path is not None else ensure_model_downloaded()
            self._session = ort.InferenceSession(
                str(self.model_path), providers=["CPUExecutionProvider"]
            )
        self._buffer = np.zeros((0,), dtype=np.float32)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((CONTEXT_SAMPLES,), dtype=np.float32)
        self._sr = np.array(SAMPLE_RATE, dtype=np.int64)

    def reset(self) -> None:
        self._buffer = np.zeros((0,), dtype=np.float32)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((CONTEXT_SAMPLES,), dtype=np.float32)

    def compute_level(self, indata: np.ndarray) -> float:
        # int16 PCM -> float32 [-1, 1]，攤平成一維後併入緩衝區。
        pcm = indata.astype(np.float32).reshape(-1) / 32768.0
        self._buffer = np.concatenate([self._buffer, pcm])

        best = 0.0
        while len(self._buffer) >= WINDOW_SAMPLES:
            chunk = self._buffer[:WINDOW_SAMPLES]
            self._buffer = self._buffer[WINDOW_SAMPLES:]
            # 帶上一步驟留下的 context 前綴，見模組說明。
            model_input = np.concatenate([self._context, chunk])
            prob, self._state = self._session.run(
                ["output", "stateN"],
                {
                    "input": model_input.reshape(1, CONTEXT_SAMPLES + WINDOW_SAMPLES),
                    "state": self._state,
                    "sr": self._sr,
                },
            )
            self._context = model_input[-CONTEXT_SAMPLES:]
            best = max(best, float(prob[0][0]))
        return best
