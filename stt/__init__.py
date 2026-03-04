from .base import BaseSTT

# Lazy imports: 各引擎只在 build_stt() 選中時才 import，
# 避免在 Windows 上缺少 groq / mlx 等 macOS 專屬模組而崩潰。

def get_stt(config: dict) -> BaseSTT:
    import platform
    default_engine = "mlx_whisper" if platform.system() == "Darwin" else "local_whisper"
    engine = config.get("stt_engine", default_engine)
    if engine == "mlx_whisper":
        from .mlx_whisper import MLXWhisperSTT
        return MLXWhisperSTT(config)
    elif engine == "groq":
        from .groq_whisper import GroqWhisperSTT
        return GroqWhisperSTT(config)
    elif engine == "openrouter":
        from .openrouter_stt import OpenRouterSTT
        return OpenRouterSTT(config)
    elif engine == "gemini":
        from .gemini_stt import GeminiSTT
        return GeminiSTT(config)
    else:
        from .local_whisper import LocalWhisperSTT
        return LocalWhisperSTT(config)

