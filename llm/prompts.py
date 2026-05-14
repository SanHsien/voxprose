"""
Centralized system prompts for LLM refinement across all language variants.

This module provides the single source of truth (SSOT) for system prompts used
in the refine() method of all LLM classes. Each language variant is stored here
to ensure consistency and enable easy updates without modifying individual LLM classes.

Language variants are selected based on the language setting in config (default: "zh").
If the language is not found, fallback to Chinese ("zh").
"""

SYSTEM_PROMPTS = {
    "zh": "請將以下語音辨識結果整理成通順的文字，保持原意，只回傳結果：",
    "en": "Refine the following speech recognition output into clear, coherent text. Preserve the original meaning and return only the result:",
    "ja": "次の音声認識結果を整理し、明確で一貫性のあるテキストに変換してください。元の意味を保ち、結果のみを返してください：",
}


def get_default_system_prompt(language: str = "zh") -> str:
    """
    Retrieve the default system prompt for a given language.

    Args:
        language: The language code (e.g., "zh", "en", "ja"). Defaults to "zh".

    Returns:
        The system prompt string for the specified language, or the Chinese prompt
        if the language is not found (fallback behavior).

    Example:
        >>> prompt = get_default_system_prompt("en")
        >>> print(prompt)
        Refine the following speech recognition output into clear, coherent text...
    """
    return SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["zh"])
