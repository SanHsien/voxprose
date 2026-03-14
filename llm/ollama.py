import requests
from .base import BaseLLM


class OllamaLLM(BaseLLM):
    def __init__(self, config: dict):
        self.model = config.get("ollama_model", "llama3")
        self.base_url = config.get("ollama_base_url", "http://localhost:11434").rstrip("/")

    def refine(self, text: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"},
            ],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
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
