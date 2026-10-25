"""LLM 輸出的半形標點轉全形（繁體中文排版）。

只轉會出現在句子裡的 , ? ! : ;（「.」維持半形，避免小數點與網域被破壞）。
數字之間的 , 與 :（1,000、3:30）以及網址的 `://` 是資料不是句讀，保持半形。
"""
from __future__ import annotations

import re

_FULLWIDTH = {",": "，", "?": "？", "!": "！", ":": "：", ";": "；"}
_PATTERN = re.compile(r"[,?!:;]")
_DIGITS = "0123456789"


def _is_digit(ch: str) -> bool:
    return len(ch) == 1 and ch in _DIGITS


def to_fullwidth_punctuation(text: str) -> str:
    if not text:
        return text

    def _repl(m: re.Match) -> str:
        ch = m.group(0)
        i = m.start()
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch in ",:" and _is_digit(prev) and _is_digit(nxt):
            return ch
        if ch == ":" and text.startswith("//", i + 1):
            return ch
        return _FULLWIDTH[ch]

    return _PATTERN.sub(_repl, text)
