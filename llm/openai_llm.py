from openai import OpenAI
from .base import BaseLLM
from .prompts import get_default_system_prompt


class OpenAILLM(BaseLLM):
    def __init__(self, config: dict):
        api_key = config.get("openai_api_key", "")
        self.client = OpenAI(api_key=api_key)
        self.model = config.get("openai_model", "gpt-4o-mini")
        self.language = config.get("language", "zh")

    def refine(self, text: str, prompt: str) -> str:
        effective_prompt = prompt or get_default_system_prompt(self.language)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": effective_prompt},
                {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"},
            ],
            max_tokens=1024,
        )
        result = response.choices[0].message.content.strip()
        print(f"[llm] OpenAI refined: {result}")
        return result
