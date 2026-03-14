import httpx
from .base import BaseLLM

class OpenRouterLLM(BaseLLM):
    """OpenRouter LLM — 支援數百個模型 (Gemini, Qwen, DeepSeek...)"""

    def __init__(self, config: dict):
        self.api_key = config.get("openrouter_api_key", "")
        self.model = config.get("openrouter_model", "google/gemini-2.0-flash-001")
        self.prompt = config.get("llm_prompt", "請將以下語音辨識結果整理成通順的文字，保持原意，只回傳結果：")

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/voicetype-mac",
            "X-Title": "VoiceType Mac",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"}
            ],
            "temperature": 0.1,
        }
        
        # v2.8.17: Detailed lifecycle logging
        print(f"[LLM] Request Sent. Model: {self.model}")
        
        try:
            resp = httpx.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15.0, # Reduced to 15s for fast-fail
            )
            print(f"[LLM] Response Received. (HTTP {resp.status_code})")
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
            
        except httpx.TimeoutException:
            print(f"[LLM] Timeout (15s) - Fast fail fallback to raw text")
            return text
        except httpx.HTTPStatusError as e:
            print(f"[LLM] API Error (HTTP {e.response.status_code}): {e.response.text[:200]}")
            return text
        except Exception as e:
            print(f"[LLM] Connection Failed / Unknown Error: {e}")
            return text
