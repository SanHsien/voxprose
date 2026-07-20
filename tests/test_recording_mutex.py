"""Unit tests for audio/mutex.py's PttVadMutex — the minimal mutex between
PTT (按住說話) and the VAD 全時自動觸發 mode (REVIEW.md 風險排序表 #10).

Policy under test (see docs/DECISIONS.md for the rationale): PTT wins.
- Starting PTT while a VAD segment is being captured must signal the caller
  to abandon that in-flight VAD segment.
- A VAD segment-start that occurs while PTT is active must be ignored (no
  second recording path stacked on top), and the matching segment-stop for
  that same ignored segment must be dropped rather than processed.

This module has no sounddevice/PyQt6 dependency by design, so these tests
run unconditionally (no importorskip needed) and exercise the state machine
in isolation from the real audio I/O in audio/recorder.py and
audio/auto_trigger.py.
"""
from audio.mutex import PttVadMutex


def test_ptt_start_stop_round_trip_when_vad_never_active():
    m = PttVadMutex()

    assert m.on_ptt_start() is False  # nothing to preempt
    assert m.ptt_active is True

    m.on_ptt_stop()
    assert m.ptt_active is False


def test_vad_segment_start_stop_round_trip_when_ptt_never_active():
    m = PttVadMutex()

    assert m.on_vad_segment_start() is False  # not ignored
    assert m.vad_active is True

    assert m.on_vad_segment_stop() is False  # not discarded
    assert m.vad_active is False


def test_ptt_start_preempts_in_flight_vad_segment():
    """全時模式錄音中按 PTT：VAD 段落必須被要求捨棄，PTT 照常開始。"""
    m = PttVadMutex()
    m.on_vad_segment_start()
    assert m.vad_active is True

    preempted = m.on_ptt_start()

    assert preempted is True, "caller must abandon the in-flight VAD segment"
    assert m.vad_active is False
    assert m.ptt_active is True


def test_vad_segment_start_is_ignored_while_ptt_active():
    """PTT 錄音中 VAD 觸發：這次觸發必須被忽略，不得疊加第二路錄音。"""
    m = PttVadMutex()
    m.on_ptt_start()

    ignored = m.on_vad_segment_start()

    assert ignored is True
    assert m.vad_active is False, "VAD must not become the active source while PTT holds it"


def test_vad_segment_stop_is_discarded_after_being_ignored_at_start():
    """VAD 觸發被 PTT 忽略後，稍後到達的音訊（segment_stop）也必須被丟棄，
    不能送去 STT/LLM 處理——否則使用者會看到一份「來路不明」的輸出。"""
    m = PttVadMutex()
    m.on_ptt_start()
    m.on_vad_segment_start()  # ignored

    discard = m.on_vad_segment_stop()

    assert discard is True


def test_vad_segment_stop_after_ptt_ends_is_not_discarded():
    """PTT 結束後才真正輪到 VAD 開始一個新段落：這次不該被誤判為要丟棄的
    殘留狀態（確保 _vad_suppressed 不會跨段落誤留）。"""
    m = PttVadMutex()
    m.on_ptt_start()
    m.on_vad_segment_start()  # ignored, segment 1
    m.on_vad_segment_stop()   # discarded, segment 1
    m.on_ptt_stop()

    ignored = m.on_vad_segment_start()  # segment 2, PTT no longer active
    discard = m.on_vad_segment_stop()

    assert ignored is False
    assert discard is False


def test_normal_vad_segment_not_discarded_when_ptt_starts_only_after_it_ended():
    """VAD 已經正常結束一個段落（vad_active 已清空）之後才按 PTT，不該誤
    以為有東西可以搶佔。"""
    m = PttVadMutex()
    m.on_vad_segment_start()
    m.on_vad_segment_stop()  # segment already finished normally

    preempted = m.on_ptt_start()

    assert preempted is False
