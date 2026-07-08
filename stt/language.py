def get_transcription_language(config: dict) -> str:
    """Return the language hint used by STT transcription.

    Translation mode is an output concern handled by LLM prompts; passing it to
    Whisper makes Chinese dictation drift into English recognition.
    """
    return config.get("language") or "zh"
