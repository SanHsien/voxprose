import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

class MiniMaxLLM(BaseLLM):
    """MiniMax LLM (OpenAI-compatible API)"""

    def __init__(self, config: dict):
        self.api_key = config.get("minimax_api_key", "")
        self.model = config.get("minimax_model", "MiniMax-Text-01")
        self.language = config.get("language", "zh")
        self.prompt = config.get("llm_prompt", "")

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": effective_prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"}
            ],
        }
        try:
            resp = httpx.post(
                "https://api.minimaxi.chat/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[MiniMax LLM Error] {e}")
            return text
