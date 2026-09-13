from faster_whisper import WhisperModel
import io
import logging
from .base import BaseSTT

log = logging.getLogger("voicetype.stt")


class LocalWhisperSTT(BaseSTT):
    def __init__(self, config: dict):
        model_size = config.get("whisper_model", "medium")
        
        import sys
        import platform
        is_windows_exe = getattr(sys, 'frozen', False) and platform.system() == "Windows"
        
        device = "auto"
        compute_type = "int8"
        
        # v2.8.27_V62: Ensure model cache is in writable AppData for EXE
        from paths import APP_DATA_DIR
        from pathlib import Path
        model_cache_dir = str(APP_DATA_DIR / "whisper_models")
        Path(model_cache_dir).mkdir(parents=True, exist_ok=True)
        
        log.info(f"[stt] V62: Loading local Whisper model: {model_size} (Device: {device}, Type: {compute_type}, Cache: {model_cache_dir})")
        
        try:
            self.model = WhisperModel(model_size, device=device, compute_type=compute_type, cpu_threads=2, download_root=model_cache_dir)
            log.info(f"[stt] V62: Model loaded successfully.")
        except Exception as e:
            log.warning(f"[stt] V62: Auto device failed ({e}), falling back to CPU...")
            self.model = WhisperModel(model_size, device="cpu", compute_type="float32", cpu_threads=4, download_root=model_cache_dir)
            log.info(f"[stt] V62: CPU fallback model loaded.")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        if not audio_bytes:
            return ""
        try:
            from vocab.manager import build_vocab_prompt
            prompt = build_vocab_prompt()
        except Exception as e:
            # 2026-07-23（broad except 清查）：同 stt/subprocess_whisper.py 的
            # 同一類風險（見該檔案對應註解）——補 log 而非繼續沉默。
            log.warning(f"[stt] build_vocab_prompt failed, using default prompt: {e}")
            prompt = "以下是繁體中文的語音內容："

        audio_io = io.BytesIO(audio_bytes)
        segments, info = self.model.transcribe(
            audio_io,
            language=language,
            beam_size=1,
            vad_filter=True,
            initial_prompt=prompt,
            # Mac 主線 13-2（51094bf:stt/mlx_whisper.py）移植：抗幻覺轉錄參數。
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
        )
        text = "".join(seg.text for seg in segments).strip()
        log.info(f"[stt] Transcribed ({info.language}): {text}")
        return text

