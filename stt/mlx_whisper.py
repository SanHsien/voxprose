import gc
import io
import time
import wave
import numpy as np
from .base import BaseSTT

MODEL_REPO_MAP = {
    "tiny":   "mlx-community/whisper-tiny-mlx",
    "base":   "mlx-community/whisper-base-mlx",
    "small":  "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large":  "mlx-community/whisper-large-v3-mlx",
}

# 每 N 次轉錄後自動清理 Metal 快取，防止長時間使用後記憶體膨脹
_CACHE_CLEAR_INTERVAL = 10


class MLXWhisperSTT(BaseSTT):
    def __init__(self, config: dict):
        model_size = config.get("whisper_model", "medium")
        self.model_repo = MODEL_REPO_MAP.get(model_size, MODEL_REPO_MAP["medium"])
        self._transcribe_count = 0
        print(f"[stt] MLX Whisper model: {self.model_repo} (waiting for warmup)")

    def download_model(self, progress_callback=None):
        """
        預先下載模型並回報進度。
        progress_callback(pct: int, msg: str)
          pct = 0-100 實際進度, -1 = 不確定進度
        """
        def cb(pct, msg):
            print(f"[stt] download {pct}% — {msg}")
            if progress_callback:
                progress_callback(pct, msg)

        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(self.model_repo, "config.json")
            if cached:
                cb(100, "模型已在本機，無需下載")
                return
        except Exception:
            pass

        cb(0, "正在取得模型檔案清單...")
        try:
            from huggingface_hub import list_repo_files, hf_hub_download
            files = [f for f in list_repo_files(self.model_repo)]
            total = max(len(files), 1)
            for i, filename in enumerate(files):
                pct = int(i / total * 95)
                cb(pct, f"({i + 1}/{total}) {filename}")
                try:
                    hf_hub_download(self.model_repo, filename)
                except Exception as e:
                    print(f"[stt] skip {filename}: {e}")
            cb(100, "下載完成！")
        except Exception as e:
            print(f"[stt] file-level download failed ({e}), fallback to snapshot_download")
            cb(-1, "正在下載模型（請稍候）...")
            try:
                from huggingface_hub import snapshot_download
                snapshot_download(self.model_repo)
                cb(100, "下載完成！")
            except Exception as e2:
                print(f"[stt] snapshot_download failed: {e2}")

    def warmup(self):
        """Pre-initialize MLX and Metal by doing a tiny dummy transcription."""
        print(f"[stt] Warming up MLX Whisper ({self.model_repo})...")
        try:
            import mlx_whisper
            silence = np.zeros(16000, dtype=np.float32)
            mlx_whisper.transcribe(silence, path_or_hf_repo=self.model_repo)
            print(f"[stt] MLX Whisper warmup complete.")
        except Exception as e:
            print(f"[stt] Warmup error: {e}")

    def _clear_metal_cache(self):
        """釋放 MLX Metal 快取與 Python 垃圾，降低長時間使用後的記憶體占用。"""
        try:
            import mlx.core as mx
            mx.metal.clear_cache()
        except Exception:
            pass
        gc.collect()

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        if not audio_bytes:
            return ""

        try:
            from vocab.manager import build_vocab_prompt
            prompt = build_vocab_prompt()
        except Exception:
            prompt = "以下是繁體中文的語音內容："

        # WAV bytes → float32 numpy array [-1, 1]
        audio_io = io.BytesIO(audio_bytes)
        with wave.open(audio_io, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)

        if sampwidth == 2:
            audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            audio_np = np.frombuffer(raw_data, dtype=np.float32)

        if n_channels > 1:
            audio_np = audio_np.reshape(-1, n_channels).mean(axis=1)

        import mlx_whisper
        result = mlx_whisper.transcribe(
            audio_np,
            path_or_hf_repo=self.model_repo,
            language=language,
            initial_prompt=prompt,
            verbose=False,
        )
        text = result.get("text", "").strip()
        print(f"[stt] MLX Whisper transcribed: {text}")

        # 定期清理記憶體
        self._transcribe_count += 1
        if self._transcribe_count % _CACHE_CLEAR_INTERVAL == 0:
            print(f"[stt] Clearing MLX Metal cache (every {_CACHE_CLEAR_INTERVAL} transcriptions)...")
            self._clear_metal_cache()

        return text
