import unittest
from unittest.mock import patch

import httpx

from llm.openrouter import OpenRouterLLM


class FakeResponse:
    def __init__(self, status_code, text="", content="OK"):
        self.status_code = status_code
        self.text = text
        self._content = content

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
            raise httpx.HTTPStatusError(
                "bad model",
                request=request,
                response=self,
            )

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


class OpenRouterFallbackTest(unittest.TestCase):
    def test_falls_back_when_configured_model_has_no_endpoint(self):
        llm = OpenRouterLLM(
            {
                "openrouter_api_key": "test-key",
                "openrouter_model": "google/gemini-2.0-flash-001",
            }
        )
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json["model"])
            if len(calls) == 1:
                return FakeResponse(
                    404,
                    '{"error":{"message":"No endpoints found for google/gemini-2.0-flash-001.","code":404}}',
                )
            return FakeResponse(200, content="Translated")

        with patch("llm.openrouter.httpx.post", side_effect=fake_post):
            self.assertEqual(llm.refine("測試", "translate"), "Translated")

        self.assertEqual(
            calls,
            ["google/gemini-2.0-flash-001", "google/gemini-2.5-flash"],
        )

    def test_returns_original_text_when_all_models_fail(self):
        llm = OpenRouterLLM(
            {
                "openrouter_api_key": "test-key",
                "openrouter_model": "missing-model",
            }
        )

        def fake_post(url, headers, json, timeout):
            return FakeResponse(404, '{"error":{"message":"No endpoints found.","code":404}}')

        with patch("llm.openrouter.httpx.post", side_effect=fake_post):
            self.assertEqual(llm.refine("原文", "translate"), "原文")


if __name__ == "__main__":
    unittest.main()
