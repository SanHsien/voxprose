"""Mac 主線 v2.9.7（7-5，`51094bf:main.py:_apply_basic_soul_rules`，第 709-745 行）
移植：LLM 未啟用時仍可套用的輕量版靈魂規則——不呼叫任何 LLM API，只解析 soul md
的「贅詞清除規則」區段，把使用者自訂的口頭禪/贅詞直接從輸出文字中刪除。

拆成純函式放在這裡（不放在 `ui/app.py` 內），原因與 `audio/gain.py`／
`stt/hallucination_filter.py` 一致：`ui/app.py` 頂層 import PyQt6，在沒裝 PyQt6
的環境（包含本次開發機）連 import 都會失敗，純文字處理邏輯抽出來才能在任何環境
被單元測試覆蓋。`ui/app.py:VoiceTypeApp._apply_basic_soul_rules` 只負責讀檔案 +
呼叫這裡的函式。
"""
from __future__ import annotations

import re

_FILLER_WORD_PATTERN = re.compile(r"「([^」]+)」")
_SECTION_MARKER = "贅詞清除規則"


def extract_filler_words(markdown_text: str) -> list[str]:
    """解析 soul md 內容，抽出「贅詞清除規則」區段裡引號包住的詞語。

    區段起點：內容中含「贅詞清除規則」字樣的那一行（之後開始蒐集）。
    區段終點：下一個以 `#` 開頭的標題行，或檔案結尾。
    """
    if not markdown_text:
        return []
    in_section = False
    words: list[str] = []
    for line in markdown_text.split("\n"):
        if _SECTION_MARKER in line:
            in_section = True
            continue
        if in_section:
            if line.startswith("#"):
                break
            words.extend(_FILLER_WORD_PATTERN.findall(line))
    return words


def strip_filler_words(text: str, filler_words: list[str]) -> str:
    """把 filler_words 逐一從 text 裡刪除後回傳（trim 前後空白）。

    較長的詞先處理，避免短詞先命中破壞較長詞的比對（例如「那」比「那對」短，
    若「那」先刪會讓「那對」永遠比對不到剩下的「對」）。空字串詞語會被忽略。
    """
    if not text or not filler_words:
        return (text or "").strip()
    for word in sorted({w for w in filler_words if w}, key=len, reverse=True):
        text = text.replace(word, "")
    return text.strip()


def apply_basic_soul_rules(text: str, soul_markdown_contents: list[str]) -> str:
    """便利函式：合併多份 soul md 內容抽出的贅詞清單，套用到 text 上。"""
    filler_words: list[str] = []
    for content in soul_markdown_contents:
        filler_words.extend(extract_filler_words(content))
    return strip_filler_words(text, filler_words)
