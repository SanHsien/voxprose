import anthropic
from .base import BaseLLM
from .prompts import get_default_system_prompt
from net_config import CLOUD_REQUEST_TIMEOUT_SECONDS


class ClaudeLLM(BaseLLM):
    def __init__(self, config: dict):
        # 欄位名以 config.py DEFAULT_CONFIG／設定 UI 實際儲存的
        # anthropic_api_key / anthropic_model 為準。舊版誤讀
        # claude_api_key / claude_model——這兩個欄位不存在於 DEFAULT_CONFIG，
        # 設定視窗也從未寫入，導致 Claude 引擎永遠拿到空 key，refine() 直接
        # 回傳原文（使用者以為有潤飾，實際上從未呼叫過 API）。
        self.api_key = config.get("anthropic_api_key", "")
        self.model = config.get("anthropic_model", "claude-3-haiku-20240307")
        self.language = config.get("language", "zh")
        # REVIEW.md 第 3 節：舊版未設定 timeout，落回 SDK 預設值（600s）。
        self.client = anthropic.Anthropic(api_key=self.api_key, timeout=CLOUD_REQUEST_TIMEOUT_SECONDS)

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.1,
            system=effective_prompt,
            messages=[{"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"}],
        )
        result = message.content[0].text.strip()
        print(f"[llm] Claude refined: {result}")
        return result
