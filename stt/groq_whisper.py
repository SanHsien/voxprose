import io
from groq import Groq
from .base import BaseSTT
from net_config import CLOUD_REQUEST_TIMEOUT_SECONDS


class GroqWhisperSTT(BaseSTT):
    def __init__(self, config: dict):
        api_key = config.get("groq_api_key", "")
        # REVIEW.md 第 3 節：舊版未設定 timeout，落回 SDK 預設值（600s）。
        self.client = Groq(api_key=api_key, timeout=CLOUD_REQUEST_TIMEOUT_SECONDS)

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        if not audio_bytes:
            return ""
        transcription = self.client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=("audio.wav", io.BytesIO(audio_bytes), "audio/wav"),
            language=language,
            response_format="text",
        )
        text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
        print(f"[stt] Groq transcribed: {text}")
        return text
