import anthropic
from .base import BaseLLM
from .prompts import get_default_system_prompt


class ClaudeLLM(BaseLLM):
    def __init__(self, config: dict):
        api_key = config.get("anthropic_api_key", "")
        model = config.get("anthropic_model", "claude-3-haiku-20240307")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.language = config.get("language", "zh")

    def refine(self, text: str, prompt: str) -> str:
        effective_prompt = prompt or get_default_system_prompt(self.language)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=effective_prompt,
            messages=[{"role": "user", "content": f"<Draft>\n{text}\n</Draft>"}],
        )
        result = message.content[0].text.strip()
        print(f"[llm] Claude refined: {result}")
        return result
