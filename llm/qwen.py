import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

class QwenLLM(BaseLLM):
    """Alibaba Qwen LLM (DashScope API)"""

    def __init__(self, config: dict):
        self.api_key = config.get("qwen_api_key", "")
        self.model = config.get("qwen_model", "qwen-plus")
        self.language = config.get("language", "zh")

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
            "input": {
                "messages": [
                    {"role": "system", "content": effective_prompt},
                    {"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"}
                ]
            },
            "parameters": {
                "temperature": 0.1
            }
        }
        try:
            resp = httpx.post(
                "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["output"]["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[Qwen LLM Error] {e}")
            return text
