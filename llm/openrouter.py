import httpx
from .base import BaseLLM
from .prompts import get_default_system_prompt

OPENROUTER_DEFAULT_MODEL = "google/gemini-2.5-flash"
OPENROUTER_FALLBACK_MODELS = [
    "google/gemini-2.5-flash",
    "google/gemini-2.5-flash-lite",
    "google/gemini-3.5-flash",
    "~google/gemini-flash-latest",
    "openai/gpt-4o-mini",
]


def _is_missing_model_error(response: httpx.Response) -> bool:
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
        self.prompt = config.get("llm_prompt", "")

    def _candidate_models(self):
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
            "HTTP-Referer": "https://github.com/voicetype-mac",
            "X-Title": "VoiceType Mac",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": effective_prompt},
            {"role": "user", "content": f"<Draft>\n{text}\n</Draft>"}
        ]

        for model in self._candidate_models():
            payload = {
                "model": model,
                "messages": messages,
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
