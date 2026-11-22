import anthropic
from .base import BaseLLM
from .prompts import get_default_system_prompt
from net_config import CLOUD_REQUEST_TIMEOUT_SECONDS

# 取代舊的 temperature=0.1：寫進每次請求的 user turn（不放 system，因為 system 可能是使用者自訂的 soul）。
STABILITY_INSTRUCTION = (
    "[要求：保持原意與原本的用字，只做必要的潤飾；不增補內容、不換說法、不自由發揮。"
    "同一段草稿每次都應得到相同的結果。只回傳潤飾後的文字。]"
)


class ClaudeLLM(BaseLLM):
    def __init__(self, config: dict):
        # 欄位名以 config.py DEFAULT_CONFIG／設定 UI 實際儲存的
        # anthropic_api_key / anthropic_model 為準。舊版誤讀
        # claude_api_key / claude_model——這兩個欄位不存在於 DEFAULT_CONFIG，
        # 設定視窗也從未寫入，導致 Claude 引擎永遠拿到空 key，refine() 直接
        # 回傳原文（使用者以為有潤飾，實際上從未呼叫過 API）。
        self.api_key = config.get("anthropic_api_key", "")
        self.model = config.get("anthropic_model", "claude-haiku-5-5")
        self.language = config.get("language", "zh")
        # REVIEW.md 第 3 節：舊版未設定 timeout，落回 SDK 預設值（600s）。
        self.client = anthropic.Anthropic(api_key=self.api_key, timeout=CLOUD_REQUEST_TIMEOUT_SECONDS)

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        message = self.client.messages.create(
            model=self.model,
            # 現行 Claude 模型（claude-haiku-5-5 等）收到非預設 temperature 會回 400，所以不送；
            # 原本靠 temperature=0.1 換來的保守度，改由下面 STABILITY_INSTRUCTION 寫明。
            # 這些模型預設會先思考，思考也算進 max_tokens，所以上限給 4096。
            # 見 docs/DECISIONS.md 2026-11-22。
            max_tokens=4096,
            system=effective_prompt,
            messages=[{"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n{STABILITY_INSTRUCTION}\n<Draft>\n{text}\n</Draft>"}],
        )
        # 回應開頭可能是 thinking 塊，依型別取文字塊，不依位置。
        result = "".join(b.text for b in message.content if getattr(b, "type", "") == "text").strip()
        print(f"[llm] Claude refined: {result}")
        return result
