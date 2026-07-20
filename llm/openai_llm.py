from openai import OpenAI
from .base import BaseLLM
from .prompts import get_default_system_prompt


class OpenAILLM(BaseLLM):
    def __init__(self, config: dict):
        self.api_key = config.get("openai_api_key", "")
        self.model = config.get("openai_model", "gpt-4o-mini")
        self.language = config.get("language", "zh")
        from openai import OpenAI
        self.client = OpenAI(api_key=self.api_key)

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": effective_prompt},
                    {"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"},
                ],
                max_tokens=1024,
                temperature=0.1,
                timeout=30
            )
            result = response.choices[0].message.content.strip()
            print(f"[llm] OpenAI refined: {result}")
            return result
        except Exception as e:
            print(f"[llm] OpenAI error: {e}")
            return text
