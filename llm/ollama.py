import requests
from .base import BaseLLM
from .prompts import get_default_system_prompt


class OllamaLLM(BaseLLM):
    def __init__(self, config: dict = None, model: str = "llama3", base_url: str = "http://localhost:11434"):
        if isinstance(config, dict):
            self.model = config.get("ollama_model", "llama3")
            self.base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip("/")
            self.language = config.get("language", "zh")
        else:
            # 向後相容：直接傳 model/base_url 字串
            self.model = config if isinstance(config, str) else model
            self.base_url = base_url.rstrip("/")
            self.language = "zh"

    def refine(self, text: str, prompt: str) -> str:
        effective_prompt = prompt or get_default_system_prompt(self.language)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": effective_prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"},
            ],
            "stream": False,
        }
        try:
            # Use smaller timeout for local Ollama to fail fast if not running
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=5)
            resp.raise_for_status()
            result = resp.json()["message"]["content"].strip()
            print(f"[llm] Ollama refined: {result}")
            return result
        except Exception as e:
            print(f"[llm] Ollama error: {e}")
            # Fallback to original text to prevent thread crash
            return text
