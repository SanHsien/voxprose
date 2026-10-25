"""STT「引擎尚未就緒」守衛不能誤殺正常聽寫內容。

Regression: ui/app.py 原本用 `"系統初始化中" in text or "初始化" in text`，
使用者口述「記得把變數初始化」這類含「初始化」的正常句子會被當成引擎錯誤丟掉，
畫面顯示「引擎尚未就緒」且文字完全不輸出。
"""
from stt.status import STT_NOT_READY_MESSAGE, is_stt_not_ready_text


def test_real_not_ready_message_is_detected():
    assert is_stt_not_ready_text(STT_NOT_READY_MESSAGE)


def test_dictated_text_containing_chushihua_is_not_swallowed():
    assert not is_stt_not_ready_text("記得把這個變數初始化")
    assert not is_stt_not_ready_text("初始化完成之後再開始錄音")


def test_empty_text_is_not_not_ready():
    assert not is_stt_not_ready_text("")
    assert not is_stt_not_ready_text(None)


def test_subprocess_worker_uses_the_shared_message():
    import inspect

    from stt import subprocess_whisper

    assert "STT_NOT_READY_MESSAGE" in inspect.getsource(subprocess_whisper)
