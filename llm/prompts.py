"""Mac 主線 v2.9.13（13-1，`51094bf:llm/prompts.py`）移植：集中化 LLM system prompt 預設值。

背景：移植前，`llm/openrouter.py`／`gemini.py`／`qwen.py`／`deepseek.py` 四個引擎各自在
`__init__` 裡重複硬編同一句中文預設 prompt（`config.get("llm_prompt", "請將以下語音辨識結果...")`），
且這個 `self.prompt` 屬性從未被對應的 `refine()` 實際使用——現樹呼叫路徑
（`ui/app.py:_build_llm_prompt`）一律組好完整、非空的 prompt 字串才呼叫
`refine(text, prompt)`，所以舊的「引擎內建預設值」形同死碼，也只有中文一種語言。

集中放這裡的目的：
1. 消除四個引擎檔重複的硬編中文字串（單一真相源）。
2. 讓 `refine()` 統一用 `prompt or get_default_system_prompt(self.language)` 做防禦性
   fallback——避免空/None prompt 直接送進雲端 API（Mac 版 v2.9.13 commit `960f5e6`
   的修復動機：空 prompt 容易讓 LLM 幻覺出無關內容）。現樹目前的呼叫路徑一律先組好
   非空 prompt，這層防護目前是「防禦性合約」而非「治療現有 bug」，但讓 `refine()`
   的介面更完整，未來新增呼叫路徑（測試、CLI 工具、直接呼叫 llm/*.py）不需要重複造字串。

不改動：`BaseLLM.refine()` 簽章維持 `(text, prompt)` 不變（呼叫端傳入 prompt 的既有設計，
見 docs/DECISIONS.md 2026-07-20「Mac 主線功能吸收第 2-5 項」條目關於 13-1 的討論）。
"""

SYSTEM_PROMPTS = {
    "zh": "請將以下語音辨識結果整理成通順的文字，保持原意，只回傳結果：",
    "en": "Refine the following speech recognition output into clear, coherent text. Preserve the original meaning and return only the result:",
    "ja": "次の音声認識結果を整理し、明確で一貫性のあるテキストに変換してください。元の意味を保ち、結果のみを返してください：",
}

DEFAULT_LANGUAGE = "zh"


def get_default_system_prompt(language: str = DEFAULT_LANGUAGE) -> str:
    """依語言取得預設 system prompt；未知語言 fallback 回中文。

    Args:
        language: 語言代碼（如 "zh"、"en"、"ja"）。預設 "zh"。

    Returns:
        對應語言的預設 system prompt；查無該語言時 fallback 回中文版本。
    """
    return SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS[DEFAULT_LANGUAGE])


# 「快速翻譯」（選單／語音指令寫入 config["translation_lang"]）要附加在 LLM prompt 末端的
# 指令。放在最後是因為 docs/DEVELOPMENT.md 檢核表要求「開啟翻譯時，即使有其他情境設定，
# 也優先翻譯為目標語文」。
TRANSLATION_INSTRUCTIONS = {
    "en": "【翻譯指令】無論原文是什麼語言，請將潤飾後的最終內容翻譯成英文（English）後輸出；只輸出譯文，不附原文、不加說明。",
    "ja": "【翻譯指令】無論原文是什麼語言，請將潤飾後的最終內容翻譯成日文（日本語）後輸出；只輸出譯文，不附原文、不加說明。",
}


def get_translation_instruction(target) -> str:
    """翻譯目標（"en"／"ja"）對應的 prompt 指令；None、空字串或未知語言回傳空字串。"""
    return TRANSLATION_INSTRUCTIONS.get(target or "", "")
