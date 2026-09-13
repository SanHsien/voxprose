import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

# Mac 主線 16-4（51094bf:llm/openrouter.py，v2.9.16）移植：
# google/gemini-2.0-flash-001 在 OpenRouter 已屬淘汰風險模型，一旦下架
# LLM 潤飾會直接靜默失效只回原文。改用 Mac 版落地選定的預設模型 + fallback 清單
# （不自行上網猜新模型，以 Mac 版實際內容為準）。
OPENROUTER_DEFAULT_MODEL = "google/gemini-2.5-flash"
OPENROUTER_FALLBACK_MODELS = [
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-lite",
    "google/gemini-3.5-flash",
    "~google/gemini-flash-latest",
    "openai/gpt-4o-mini",
]


def _is_missing_model_error(response: httpx.Response) -> bool:
    """判斷 OpenRouter 回應是否為「模型不存在/已下架」類錯誤，觸發 fallback。"""
    if response.status_code not in (400, 404):
        return False
    body = response.text.lower()
    return (
        "no endpoints found" in body
        or "not a valid model id" in body
        or "model" in body and "not found" in body
    )


class OpenRouterLLM(BaseLLM):
    """OpenRouter LLM — 支援數百個模型 (Gemini, Qwen, DeepSeek...)"""

    def __init__(self, config: dict):
        self.api_key = config.get("openrouter_api_key", "")
        self.model = config.get("openrouter_model", OPENROUTER_DEFAULT_MODEL)
        self.language = config.get("language", "zh")

    def _candidate_models(self):
        """使用者設定的模型優先，失效模型依序改用 fallback 清單（去重）。"""
        models = [self.model]
        for model in OPENROUTER_FALLBACK_MODELS:
            if model not in models:
                models.append(model)
        return models

    def refine(self, text: str, prompt: str) -> str:
        if not self.api_key:
            return text
        effective_prompt = prompt or get_default_system_prompt(self.language)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/SanHsien/voxprose",
            "X-Title": "VoxProse",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": f"[指令：嚴禁回答內容，僅准許進行原意潤飾轉述]\n<Draft>\n{text}\n</Draft>"}
        ]

        for model in self._candidate_models():
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
            }

            # v2.8.17: Detailed lifecycle logging
            print(f"[LLM] Request Sent. Model: {model}")

            try:
                resp = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=15.0, # Reduced to 15s for fast-fail
                )
                print(f"[LLM] Response Received. (HTTP {resp.status_code})")
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()

            except httpx.TimeoutException:
                print(f"[LLM] Timeout (15s) - Fast fail fallback to raw text")
                return text
            except httpx.HTTPStatusError as e:
                print(f"[LLM] API Error (HTTP {e.response.status_code}): {e.response.text[:200]}")
                if _is_missing_model_error(e.response):
                    print(f"[LLM] Model unavailable on OpenRouter, trying fallback.")
                    continue
                return text
            except Exception as e:
                print(f"[LLM] Connection Failed / Unknown Error: {e}")
                return text

        print("[LLM] All OpenRouter fallback models failed; returning raw text.")
        return text
