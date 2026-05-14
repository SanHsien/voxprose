import gc
import io
import threading
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

# Whisper 在靜音 / 雜訊 / 過短音檔時會憑空編出 YouTube 結尾片語（訓練資料偏差）。
# 整段命中（去掉空白/標點後）就丟掉。不做子字串匹配，避免誤殺正常句子裡含這些詞的情況。
_WHISPER_HALLUCINATIONS = frozenset({
    # YouTube 結尾片語
    "謝謝收看", "謝謝觀看", "謝謝大家", "謝謝大家的收看", "謝謝大家的觀看",
    "感謝收看", "感謝觀看", "感謝你的觀看", "感謝您的觀看", "感謝大家的收看", "感謝大家的觀看",
    "感謝你的收看", "感謝您的收看",
    "我們下次再見", "我們下集再見", "下次見", "下集再見", "下次再見", "我們下次見",
    "請訂閱", "請按讚", "請按讚訂閱", "別忘了訂閱", "記得訂閱", "請按讚並訂閱",
    "別忘了按讚訂閱", "別忘了按讚訂閱開啟小鈴鐺", "記得按讚訂閱開啟小鈴鐺",
    "按讚訂閱開啟小鈴鐺",
    # 字幕組 / 上傳者水印
    "字幕由Amara.org社群提供", "字幕由 Amara.org 社群提供",
    "由 Amara.org 社群提供", "由Amara.org社群提供",
    "MBC뉴스", "MBC 뉴스",
    # 過短口頭禪（單字節 hallucination）
    "嗯", "啊", "喔", "哦", "嗯哼", "呃", "嗯嗯",
    "。", "...", "…",
})


def _is_hallucination(text: str) -> bool:
    """Return True iff text (stripped of trailing punctuation/whitespace) exactly
    matches a known Whisper hallucination pattern."""
    if not text:
        return False
    # 去掉常見尾標點與空白後比對
    stripped = text.strip().rstrip("。.!?！？,，、 \t\n")
    return stripped in _WHISPER_HALLUCINATIONS


class MLXWhisperSTT(BaseSTT):
    # class-level (NOT instance-level) because Metal command queue is
    # process-global; per-instance locking would not eliminate the race.
    # Fixes GitHub Issue #6 (SIGSEGV in mlx::core::RandomBits::eval_gpu when
    # two daemon threads run mlx_whisper.transcribe() concurrently).
    _gpu_lock = threading.Lock()

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

        Note: intentionally NOT locked with _gpu_lock — this method only
        performs HTTP / filesystem operations and never touches Metal.
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
        """No-op since v2.9.12: MLX Metal warmup with silence triggers C-level abort()
        in mlx_whisper.detect_language on certain Mac/macOS combos (confirmed:
        Mac16,12 + macOS 15.5, regardless of model size). The abort is from MLX C
        extension and cannot be caught by Python try/except.

        Trade-off: first real transcription will be ~5-15s slower (Metal kernel
        JIT compile happens lazily). This is a one-time cost and far better than
        having the app crash on launch for affected users.

        Real audio (non-silent) does not trigger the same C-level abort, so lazy
        compilation on first use is safe."""
        with MLXWhisperSTT._gpu_lock:
            print(f"[stt] MLX Whisper warmup skipped (lazy Metal compile on first use to avoid abort on certain Mac/macOS combos)")

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

        # Serialise all MLX GPU access across threads. MLX's Metal command queue
        # is process-global; two daemon threads racing on transcribe() previously
        # crashed with SIGSEGV (GitHub Issue #6). Lock release is exception-safe
        # via the with-statement.
        import mlx_whisper
        with MLXWhisperSTT._gpu_lock:
            result = mlx_whisper.transcribe(
                audio_np,
                path_or_hf_repo=self.model_repo,
                language=language,
                initial_prompt=prompt,
                verbose=False,
                # 降低幻覺：no_speech_threshold 拉高 → Whisper 對「這段沒人聲」更敏感；
                # condition_on_previous_text=False → 不讓前一段的幻覺污染下一段。
                no_speech_threshold=0.6,
                condition_on_previous_text=False,
            )
            text = result.get("text", "").strip()
            if _is_hallucination(text):
                print(f"[stt] Hallucination dropped: {text!r}")
                text = ""
            else:
                print(f"[stt] MLX Whisper transcribed: {text}")

            # 定期清理記憶體（也在 lock 內，因為 mx.metal.clear_cache 觸碰 Metal state）
            self._transcribe_count += 1
            if self._transcribe_count % _CACHE_CLEAR_INTERVAL == 0:
                print(f"[stt] Clearing MLX Metal cache (every {_CACHE_CLEAR_INTERVAL} transcriptions)...")
                self._clear_metal_cache()

        return text
