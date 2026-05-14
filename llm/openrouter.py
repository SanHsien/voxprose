import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

class OpenRouterLLM(BaseLLM):
    """OpenRouter LLM — 支援數百個模型 (Gemini, Qwen, DeepSeek...)"""

    def __init__(self, config: dict):
        self.api_key = config.get("openrouter_api_key", "")
        self.model = config.get("openrouter_model", "google/gemini-2.0-flash-001")
        self.language = config.get("language", "zh")
        self.prompt = config.get("llm_prompt", "")

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/voicetype-mac",
            "X-Title": "VoiceType Mac",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": effective_prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"}
            ],
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
