from abc import ABC, abstractmethod


class BaseSTT(ABC):
    @abstractmethod
    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        """Transcribe WAV audio bytes to text."""
        ...

    def warmup(self, timeout: float | None = None):
        """Pre-load models or initialize hardware (optional)."""
        return True
