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


