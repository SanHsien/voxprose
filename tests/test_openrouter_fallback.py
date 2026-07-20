"""Ported from the Mac mainline (`git show 51094bf:test_openrouter_fallback.py`,
v2.9.16, item 16-4 in docs/mac-mainline-absorption-analysis.md).

llm/openrouter.py's default model `google/gemini-2.0-flash-001` carries
deprecation risk on OpenRouter -- if it gets pulled, LLM refinement silently
fails and just returns the raw STT text. This ports the Mac mainline's
fallback chain: on a "missing model" style 400/404 response, retry with the
next candidate model from OPENROUTER_FALLBACK_MODELS instead of giving up.

No real network calls are made: httpx.post is monkeypatched.
"""
import unittest
from unittest.mock import patch

import httpx

from llm.openrouter import OpenRouterLLM, OPENROUTER_FALLBACK_MODELS, _is_missing_model_error


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

    def test_non_missing_model_error_does_not_fall_back(self):
        """401/403 之類（金鑰錯誤等）不應觸發 fallback，第一次失敗就直接回原文。"""
        llm = OpenRouterLLM(
            {
                "openrouter_api_key": "test-key",
                "openrouter_model": "google/gemini-2.5-flash",
            }
        )
        calls = []

        def fake_post(url, headers, json, timeout):
            calls.append(json["model"])
            return FakeResponse(401, '{"error":{"message":"Invalid API key","code":401}}')

        with patch("llm.openrouter.httpx.post", side_effect=fake_post):
            self.assertEqual(llm.refine("原文", "translate"), "原文")

        self.assertEqual(calls, ["google/gemini-2.5-flash"])

    def test_default_model_is_not_deprecated_gemini_2_0_flash_001(self):
        """回歸守衛：確保沒人不小心把 default model 改回已淘汰風險的 2.0-flash-001。"""
        llm = OpenRouterLLM({"openrouter_api_key": "test-key"})
        self.assertEqual(llm.model, "google/gemini-2.5-flash")
        self.assertNotEqual(llm.model, "google/gemini-2.0-flash-001")

    def test_candidate_models_dedupes_when_configured_model_in_fallback_list(self):
        llm = OpenRouterLLM(
            {
                "openrouter_api_key": "test-key",
                "openrouter_model": "google/gemini-2.5-flash",
            }
        )
        candidates = llm._candidate_models()
        self.assertEqual(candidates, OPENROUTER_FALLBACK_MODELS)
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_is_missing_model_error_matches_no_endpoints_found(self):
        resp = FakeResponse(404, '{"error":{"message":"No endpoints found for x.","code":404}}')
        self.assertTrue(_is_missing_model_error(resp))

    def test_is_missing_model_error_false_for_unrelated_500(self):
        resp = FakeResponse(500, '{"error":{"message":"Internal error","code":500}}')
        self.assertFalse(_is_missing_model_error(resp))


if __name__ == "__main__":
    unittest.main()
