"""
Always-on voice activity trigger (全時自動觸發模式).

Opens a persistent low-cost input stream and segments speech with
hysteresis — no hotkey needed. A short pre-roll ring buffer is prepended to
each segment so the first syllable is not clipped. Complete segments are
emitted as WAV bytes through on_segment_stop, compatible with the existing
STT pipeline (VoiceTypeApp._process_audio).

Runs independently of AudioRecorder: PTT/toggle hotkeys keep their own
stream, so enabling auto mode never touches the existing recording paths.

語音強度判斷（本來是內嵌的 RMS 能量計算）已抽象成 `audio/vad/` 的
`BaseVAD` 介面（`vad_engine` 參數：`"rms"`｜`"silero"`），這裡的狀態機
（hysteresis、`min_speech_sec`、`max_segment_sec`）完全不變——見
`audio/vad/base.py` 與 docs/DECISIONS.md 全時模式 VAD 引擎決策。
"""
import io
import logging
import threading
import wave
from collections import deque
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from audio.vad import get_vad_engine

log = logging.getLogger("voicetype.autotrigger")

BLOCK_SEC = 0.05  # 50ms blocks, same cadence as AudioRecorder


class AutoTriggerController:
    def __init__(
        self,
        on_segment_start: Callable[[], None],
        on_segment_stop: Callable[[bytes], None],
        level_callback: Optional[Callable[[float], None]] = None,
        samplerate: int = 16000,
        sensitivity: float = 0.15,
        silence_sec: float = 1.5,
        min_speech_sec: float = 0.4,
        max_segment_sec: float = 60.0,
        vad_engine: str = "rms",
    ):
        self.on_segment_start = on_segment_start
        self.on_segment_stop = on_segment_stop
        self.level_callback = level_callback
        self.samplerate = samplerate
        # 語音強度判斷引擎（預設 "rms"，現行行為位元級不變；"silero" 缺依賴
        # /模型時 get_vad_engine() 已自行優雅降級回 rms，這裡不需要再判斷）。
        self._vad = get_vad_engine(vad_engine)
        # 觸發門檻（0~1，與 Indicator 音量條同一尺度）；低於門檻的 60% 才算靜音（遲滯）
        self.sensitivity = max(0.02, min(float(sensitivity), 1.0))
        self.silence_sec = max(0.4, float(silence_sec))
        self.min_speech_sec = float(min_speech_sec)
        self.max_segment_sec = float(max_segment_sec)

        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._capturing = False
        self._ring: deque = deque(maxlen=6)  # 300ms 前導緩衝
        self._frames: list = []
        self._speech_blocks = 0
        self._silence_blocks = 0

    # ── lifecycle ──
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._reset_segment_state()
        self._vad.reset()
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            dtype="int16",
            callback=self._callback,
            blocksize=int(self.samplerate * BLOCK_SEC),
        )
        self._stream.start()
        log.info(
            f"[auto] Trigger armed (sensitivity={self.sensitivity}, "
            f"silence={self.silence_sec}s)")

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                log.debug(f"[auto] Error closing stream on stop(): {e}")
            self._stream = None
        self._reset_segment_state()
        log.info("[auto] Trigger disarmed.")

    # ── PTT/VAD 互斥（見 audio/mutex.py, REVIEW.md 風險表 #10）──
    def is_capturing(self) -> bool:
        """目前是否正在擷取一段語音（尚未偵測到結尾靜音）。"""
        return self._capturing

    def abandon_current_segment(self) -> None:
        """外部（PTT 熱鍵）搶佔麥克風時呼叫：捨棄目前正在擷取的語音段落，
        不觸發 on_segment_stop callback，避免這段音訊之後又被送去處理、
        與 PTT 錄音的結果重疊。串流本身繼續開著（VAD 全時模式不中斷），
        只是清空目前段落的狀態，之後重新從靜音狀態偵測下一次起音。"""
        self._reset_segment_state()

    def _reset_segment_state(self) -> None:
        self._capturing = False
        self._ring.clear()
        self._frames = []
        self._speech_blocks = 0
        self._silence_blocks = 0
        self._speech_total = 0  # 段落內實際講話的塊數（判斷 min_speech 用）

    # ── audio-thread state machine ──
    def _callback(self, indata, frames, time_info, status):
        if not self._running:
            return
        try:
            level = self._vad.compute_level(indata)
            speaking = level >= self.sensitivity
            barely_silent = level < self.sensitivity * 0.6

            if not self._capturing:
                self._ring.append(indata.copy())
                if speaking:
                    self._speech_blocks += 1
                    if self._speech_blocks >= 2:  # 需持續 ~100ms，濾掉短促雜音
                        self._begin_segment()
                else:
                    self._speech_blocks = 0
            else:
                self._frames.append(indata.copy())
                if speaking:
                    self._speech_total += 1
                if self.level_callback:
                    self.level_callback(level)
                if barely_silent:
                    self._silence_blocks += 1
                    if self._silence_blocks * BLOCK_SEC >= self.silence_sec:
                        self._end_segment()
                        return
                else:
                    self._silence_blocks = 0
                if len(self._frames) * BLOCK_SEC >= self.max_segment_sec:
                    self._end_segment()
        except Exception as e:
            log.error(f"[auto] Callback error: {e}")

    def _begin_segment(self) -> None:
        self._capturing = True
        self._frames = list(self._ring)
        self._ring.clear()
        self._silence_blocks = 0
        self._speech_total = self._speech_blocks  # 觸發前的起音塊也算講話
        self._speech_blocks = 0
        # 不在音訊執行緒裡做 UI/IO — 丟給 worker thread
        threading.Thread(target=self._safe_call,
                         args=(self.on_segment_start,), daemon=True).start()

    def _end_segment(self) -> None:
        frames, self._frames = self._frames, []
        self._capturing = False
        self._silence_blocks = 0
        # 以「實際講話時間」判斷，避免把短促雜音（門聲、鍵盤）送去辨識
        speech_duration = self._speech_total * BLOCK_SEC
        self._speech_total = 0
        wav = self._to_wav_bytes(frames) if speech_duration >= self.min_speech_sec else b""
        threading.Thread(target=self._safe_call,
                         args=(self.on_segment_stop, wav), daemon=True).start()

    def _safe_call(self, fn, *args) -> None:
        try:
            fn(*args)
        except Exception as e:
            log.error(f"[auto] Segment callback error: {e}")

    def _to_wav_bytes(self, frames) -> bytes:
        if not frames:
            return b""
        audio = np.concatenate(frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
