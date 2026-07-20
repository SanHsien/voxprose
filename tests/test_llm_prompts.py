"""測試 Mac 主線 13-1（`docs/mac-mainline-absorption-analysis.md`）移植：
`llm/prompts.py` 集中化 system prompt + 各引擎 `refine()` 的
`prompt or get_default_system_prompt(language)` fallback。

不做真實網路呼叫：httpx.post / requests.post 全部 monkeypatch。
"""
import unittest
from unittest.mock import patch

from llm.prompts import SYSTEM_PROMPTS, get_default_system_prompt
from llm.openrouter import OpenRouterLLM
from llm.gemini import GeminiLLM
from llm.qwen import QwenLLM
from llm.deepseek import DeepSeekLLM
from llm.ollama import OllamaLLM


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class GetDefaultSystemPromptTest(unittest.TestCase):
    def test_known_languages_return_distinct_prompts(self):
        self.assertEqual(get_default_system_prompt("zh"), SYSTEM_PROMPTS["zh"])
        self.assertEqual(get_default_system_prompt("en"), SYSTEM_PROMPTS["en"])
        self.assertEqual(get_default_system_prompt("ja"), SYSTEM_PROMPTS["ja"])
        # 三種語言的文案彼此不同（不是複製貼上忘了改）
        self.assertEqual(len({SYSTEM_PROMPTS["zh"], SYSTEM_PROMPTS["en"], SYSTEM_PROMPTS["ja"]}), 3)

    def test_unknown_language_falls_back_to_chinese(self):
        self.assertEqual(get_default_system_prompt("fr"), SYSTEM_PROMPTS["zh"])

    def test_default_argument_is_chinese(self):
        self.assertEqual(get_default_system_prompt(), SYSTEM_PROMPTS["zh"])


class EngineFallbackTest(unittest.TestCase):
    """每個引擎收到空/None prompt 時，應該用 get_default_system_prompt(language)
    fallback，而不是把空字串當 system prompt 送進 API。"""

    def test_openrouter_empty_prompt_falls_back(self):
        llm = OpenRouterLLM({"openrouter_api_key": "k", "language": "en"})
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured["system"] = json["messages"][0]["content"]
            return FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})

        with patch("llm.openrouter.httpx.post", side_effect=fake_post):
            llm.refine("測試", "")

        self.assertEqual(captured["system"], SYSTEM_PROMPTS["en"])

    def test_openrouter_nonempty_prompt_is_used_as_is(self):
        llm = OpenRouterLLM({"openrouter_api_key": "k"})
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured["system"] = json["messages"][0]["content"]
            return FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})

        with patch("llm.openrouter.httpx.post", side_effect=fake_post):
            llm.refine("測試", "自訂 prompt")

        self.assertEqual(captured["system"], "自訂 prompt")

    def test_gemini_empty_prompt_falls_back(self):
        llm = GeminiLLM({"gemini_api_key": "k", "language": "ja"})
        captured = {}

        def fake_post(url, json, timeout):
            captured["text"] = json["contents"][0]["parts"][0]["text"]
            return FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

        with patch("llm.gemini.httpx.post", side_effect=fake_post):
            llm.refine("測試", None)

        self.assertIn(SYSTEM_PROMPTS["ja"], captured["text"])

    def test_qwen_empty_prompt_falls_back(self):
        llm = QwenLLM({"qwen_api_key": "k"})
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured["system"] = json["input"]["messages"][0]["content"]
            return FakeResponse(200, {"output": {"choices": [{"message": {"content": "ok"}}]}})

        with patch("llm.qwen.httpx.post", side_effect=fake_post):
            llm.refine("測試", "")

        self.assertEqual(captured["system"], SYSTEM_PROMPTS["zh"])

    def test_deepseek_empty_prompt_falls_back(self):
        llm = DeepSeekLLM({"deepseek_api_key": "k"})
        captured = {}

        def fake_post(url, headers, json, timeout):
            captured["system"] = json["messages"][0]["content"]
            return FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})

        with patch("llm.deepseek.httpx.post", side_effect=fake_post):
            llm.refine("測試", "")

        self.assertEqual(captured["system"], SYSTEM_PROMPTS["zh"])

    def test_ollama_empty_prompt_falls_back(self):
        llm = OllamaLLM({"language": "en"})
        captured = {}

        def fake_post(url, json, timeout):
            captured["system"] = json["messages"][0]["content"]

            class R:
                def raise_for_status(self):
                    pass

                def json(self):
                    return {"message": {"content": "ok"}}

            return R()

        with patch("llm.ollama.requests.post", side_effect=fake_post):
            llm.refine("測試", "")

        self.assertEqual(captured["system"], SYSTEM_PROMPTS["en"])


if __name__ == "__main__":
    unittest.main()
