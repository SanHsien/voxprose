import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

class GeminiLLM(BaseLLM):
    """Google Gemini LLM"""

    def __init__(self, config: dict):
        self.api_key = config.get("gemini_api_key", "")
        self.model = config.get("gemini_model", "gemini-2.0-flash")
        self.language = config.get("language", "zh")

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n{effective_prompt}\n\n<Draft>\n{text}\n</Draft>"}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024
            }
        }
        try:
            # 金鑰走標頭而非網址查詢字串：httpx 的 INFO log 會記錄完整網址，
            # debug.log 又會被診斷包匯出。
            resp = httpx.post(
                url,
                json=payload,
                headers={"x-goog-api-key": self.api_key},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"[Gemini LLM Error] {e}")
            return text
