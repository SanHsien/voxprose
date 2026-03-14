import anthropic
from .base import BaseLLM


class ClaudeLLM(BaseLLM):
    def __init__(self, config: dict):
        self.api_key = config.get("claude_api_key", "")
        self.model = config.get("claude_model", "claude-3-haiku-20240307")
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.1,
            system=prompt,
            messages=[{"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"}],
        )
        result = message.content[0].text.strip()
        print(f"[llm] Claude refined: {result}")
        return result
