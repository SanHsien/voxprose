"""STT 引擎狀態訊息的共用常數與判斷。

`stt/subprocess_whisper.py` 在 worker 還沒就緒時，會把這句提示當成「辨識結果」
回傳；`ui/app.py` 必須認出它、不要把它當聽寫內容貼出去。判斷只認這句提示本身
（「系統初始化中」），不能用「初始化」三個字——使用者口述含「初始化」的正常句子
（例如「把變數初始化」）會被誤判成引擎錯誤而整句丟掉。
"""

STT_NOT_READY_MESSAGE = "（系統初始化中，請稍後再試...）"
_NOT_READY_MARKER = "系統初始化中"


def is_stt_not_ready_text(text) -> bool:
    return bool(text) and _NOT_READY_MARKER in text
