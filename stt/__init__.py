from .base import BaseSTT

# Windows 專用版：mlx_whisper (Apple Silicon) 引擎已移除。
# Lazy imports: 各引擎只在 get_stt() 選中時才 import。

def get_stt(config: dict) -> BaseSTT:
    import platform
    engine = config.get("stt_engine", "local_whisper")
    if engine == "groq":
        from .groq_whisper import GroqWhisperSTT
        return GroqWhisperSTT(config)
    elif engine == "openrouter":
        from .openrouter_stt import OpenRouterSTT
        return OpenRouterSTT(config)
    else:
        # v2.8.27_V68: The Harsh Reality of Windows C++
        # It has been definitively proven that loading CTranslate2 in the SAME
        # process as a PyQt6 event loop will ALWAYS cause an Access Violation
        # (0xC0000005) upon model generation.
        # Therefore, we MUST keep SubprocessWhisperSTT exclusively for Windows.
        if platform.system() == "Windows":
            from .subprocess_whisper import SubprocessWhisperSTT
            return SubprocessWhisperSTT(config)
        else:
            from .local_whisper import LocalWhisperSTT
            return LocalWhisperSTT(config)
