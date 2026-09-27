import httpx
import base64
from .base import BaseSTT

class GeminiSTT(BaseSTT):
    """Google Gemini STT (Audio understanding)"""

    def __init__(self, config: dict):
        self.api_key = config.get("gemini_api_key", "")
        self.model = config.get("gemini_stt_model", "gemini-2.0-flash")
        self.language = config.get("language", "zh")

    def transcribe(self, audio_bytes: bytes, language: str = "zh") -> str:
        # 呼叫端 (ui/app.py) 傳入的 audio_bytes 已經是 AudioRecorder._to_wav_bytes()
        # 產生的完整 WAV 容器（含 header），不是裸 PCM 樣本陣列。之前這裡誤用
        # soundfile.write(buf, audio_bytes, sample_rate, format="WAV") 把一段
        # bytes 當作陣列樣本重新編碼一次，soundfile 會直接丟 IndexError，被下面
        # 的 except 吞掉後永遠回傳 ""（等同這個引擎從未真的工作過）。
        # 修法：不重新編碼，直接把既有的 WAV bytes base64 送出即可。
        if not self.api_key or not audio_bytes:
            return ""
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode()

            lang_hint = "Traditional Chinese" if self.language == "zh" else "English"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": f"Please transcribe this audio accurately in {lang_hint}. Return only the transcribed text, nothing else."},
                        {"inline_data": {"mime_type": "audio/wav", "data": audio_b64}}
                    ]
                }]
            }
            resp = httpx.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[Gemini STT Error] {e}")
            return ""
