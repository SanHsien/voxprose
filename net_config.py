"""共用的雲端請求逾時常數。

背景（REVIEW.md 第 3 節「網路請求逾時」，風險排序表未獨立列出但屬於同一類
問題）：各 STT/LLM provider 對外部雲端 API 的 httpx/requests 呼叫逾時設定不
一致，多數已各自帶了合理的 timeout（15~30s，維持原樣不動，見下方清單），
但兩個透過官方 SDK（而非直接 httpx/requests）呼叫的 provider——
`llm/claude.py`（anthropic SDK）、`stt/groq_whisper.py`（groq SDK）——完全
沒有明確設定，會落回 SDK 自己的預設值（anthropic/groq SDK 預設都高達
600 秒），一旦網路異常會讓背景執行緒卡住非常久。

這裡提供一個統一常數，只套用在這兩個原本完全沒有明確逾時的呼叫點；已經有
自己 timeout 的呼叫點（llm/ollama.py、llm/openai_llm.py、llm/openrouter.py、
llm/gemini.py、llm/deepseek.py、llm/qwen.py、stt/gemini_stt.py、
stt/openrouter_stt.py、actions/builtins.py）依指示保持原樣不動。
"""

# 語音上傳（STT）與 LLM 文字回應都可能耗時較久，取 30~120s 建議範圍內的折衷值。
CLOUD_REQUEST_TIMEOUT_SECONDS = 60
