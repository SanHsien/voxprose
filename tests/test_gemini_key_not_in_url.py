"""Gemini API key 不能放在 URL 查詢字串。

Regression: llm/gemini.py 與 stt/gemini_stt.py 把 `?key=<API key>` 組進網址。
httpx 在 INFO 等級會把完整請求網址寫進 logger（main.py 的 root logger 是 INFO、
寫入 debug.log），HTTPStatusError 的訊息也含網址；debug.log 又會被「匯出診斷包」
打包出去，等於把金鑰明文寫進可分享的檔案。官方支援改用 x-goog-api-key 標頭。
"""
import httpx

from llm.gemini import GeminiLLM
from stt.gemini_stt import GeminiSTT

SECRET = "AIza-SECRET-KEY-123"


class _Resp:
    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": " ok "}]}}]}


def _capture(monkeypatch):
    seen = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["kwargs"] = kwargs
        return _Resp()

    monkeypatch.setattr(httpx, "post", fake_post)
    return seen


def test_gemini_llm_sends_key_in_header_not_url(monkeypatch):
    seen = _capture(monkeypatch)
    out = GeminiLLM({"gemini_api_key": SECRET}).refine("你好", "prompt")
    assert out == "ok"
    assert SECRET not in seen["url"]
    assert "key=" not in seen["url"]
    assert seen["kwargs"]["headers"]["x-goog-api-key"] == SECRET


def test_gemini_stt_sends_key_in_header_not_url(monkeypatch):
    seen = _capture(monkeypatch)
    out = GeminiSTT({"gemini_api_key": SECRET}).transcribe(b"RIFFxxxx", language="zh")
    assert out == "ok"
    assert SECRET not in seen["url"]
    assert "key=" not in seen["url"]
    assert seen["kwargs"]["headers"]["x-goog-api-key"] == SECRET
