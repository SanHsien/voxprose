import httpx
import io
from .base import BaseSTT

class OpenRouterSTT(BaseSTT):
    """OpenRouter STT — 使用 Whisper Large v3 (via OpenRouter)"""

    def __init__(self, config: dict):
        self.api_key = config.get("openrouter_api_key", "")
        self.language = config.get("language", "zh")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        # 與 stt/gemini_stt.py 修過的同型 bug：呼叫端 (ui/app.py) 傳入的
        # audio_bytes 已經是 AudioRecorder._to_wav_bytes() 產生的完整 WAV 容器
        # （含 header），不是裸 PCM 樣本陣列。之前這裡誤用
        # soundfile.write(buf, audio_bytes, sample_rate, format="WAV") 把一段
        # bytes 當作陣列樣本重新編碼，soundfile 直接丟 IndexError，被下面的
        # except 吞掉後永遠回傳 ""（等同這個引擎從未真的工作過）。
        # 修法：不重新編碼，直接把既有的 WAV bytes 包進 BytesIO 上傳。
        # 簽章同時對齊 BaseSTT / 呼叫端的 (audio_bytes, language="zh")——
        # 舊簽章 (audio_data, sample_rate=16000) 收到呼叫端的 language= 關鍵字
        # 引數會直接 TypeError。
        if not self.api_key or not audio_bytes:
            return ""
        try:
            buf = io.BytesIO(audio_bytes)
            files = {"file": ("audio.wav", buf, "audio/wav")}
            data = {"model": "openai/whisper-large-v3", "language": language or self.language}
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = httpx.post(
                "https://openrouter.ai/api/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("text", "").strip()
        except Exception as e:
            print(f"[OpenRouter STT Error] {e}")
            return ""
