import threading
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional

from audio.gain import apply_gain, rms_of, update_agc_factor, AGC_WINDOW
from audio.gain import is_silent as _compute_is_silent


class AudioRecorder:
    """
    Records audio from the microphone.
    Provides real-time RMS level via callback for UI visualization.

    Mac 主線 v2.9.7（7-1/7-2/7-3）移植：麥克風裝置選擇 + 手動增益 + AGC。
    device (int|None): sounddevice 輸入裝置索引，None = 系統預設。
    gain (int, 50~300): 使用者手動設定的基底放大倍率，100 = ×1.0（不變）。
    gain_auto (bool): 啟用 AGC，用獨立的 _agc_factor 動態微調，不覆蓋手動 gain。
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        level_callback: Optional[Callable[[float], None]] = None,
        device: Optional[int] = None,
        gain: int = 100,
        gain_auto: bool = True,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.level_callback = level_callback
        self.device = device
        self.gain = gain            # 使用者手動設定 (50~300)
        self.gain_auto = gain_auto  # AGC 開關

        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._agc_factor: float = 1.0        # AGC 動態倍率（不覆蓋 gain，7-3）
        self._recent_peaks: list[float] = []

        self.is_silent: bool = False  # 7-4：stop() 後設定，供呼叫端跳過 STT

        # Event handlers for main.py integration
        self.on_start: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[bytes], None]] = None

    def _update_agc(self, rms: float) -> None:
        """AGC：根據近期峰值動態調整 _agc_factor，不動 self.gain（7-3）。
        純數學部分委派給 audio/gain.py 的 update_agc_factor（可獨立單元測試）。"""
        if not self.gain_auto:
            return
        self._recent_peaks.append(rms)
        if len(self._recent_peaks) > AGC_WINDOW * 2:
            self._recent_peaks.pop(0)
        self._agc_factor = update_agc_factor(self._recent_peaks, self._agc_factor)

    def _callback(self, indata, frames, time_info, status):
        """Standard PortAudio callback - avoids thread deadlocks on stop()."""
        if not self._recording:
            return

        amplified = apply_gain(indata, self.gain, self._agc_factor)

        with self._lock:
            self._frames.append(amplified.copy())

        # 放大後的 RMS（0.0~1.0），同時餵給 UI 音量條與 AGC 判斷
        rms = rms_of(amplified)
        self._update_agc(rms)

        if self.level_callback:
            # Normalize to 0~1.0 range for UI
            self.level_callback(min(rms * 10, 1.0))

    def start(self) -> None:
        """Start recording audio via non-blocking callback."""
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True
            self._agc_factor = 1.0
            self._recent_peaks = []
            self.is_silent = False

        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
                callback=self._callback,
                blocksize=int(self.samplerate * 0.05), # 50ms chunks
            )
            self._stream.start()
        except Exception as e:
            if self.device is not None:
                # 裝置消失（拔線/切換）：fallback 回系統預設裝置（7-1）
                print(f"[recorder] Device {self.device} unavailable ({e}), falling back to system default.")
                self._stream = sd.InputStream(
                    samplerate=self.samplerate,
                    channels=self.channels,
                    dtype="int16",
                    device=None,
                    callback=self._callback,
                    blocksize=int(self.samplerate * 0.05),
                )
                self._stream.start()
            else:
                raise

        if self.on_start:
            self.on_start()

    def _poll_audio(self) -> None:
        while self._recording and self._stream:
            try:
                # 每次讀取 0.05 秒的區塊 (16kHz * 0.05 = 800 frames)
                frames_to_read = int(self.samplerate * 0.05)
                # Ensure we only try to read if stream is active and we are still recording
                if not self._stream or not self._stream.active:
                    break
                    
                indata, overflowed = self._stream.read(frames_to_read)
                
                with self._lock:
                    if not self._recording:
                        break
                    self._frames.append(indata.copy())
                
                # 計算音量 RMS (0.0 ~ 1.0) 回傳給 UI
                if self.level_callback:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.level_callback(min(rms * 10, 1.0))

            except Exception as e:
                # 當串流被外界中止或關閉，將引發例外中斷讀取
                break

    def stop(self) -> bytes:
        """Stop recording safely. Sets is_silent (7-4)."""
        with self._lock:
            if not self._recording:
                return b""
            self._recording = False

        if self._stream:
            try:
                # Stop the callback gracefully first
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        # 7-4：整段錄音的峰值 RMS 低於門檻就標記為靜音，讓呼叫端可以跳過 STT
        # （省一次呼叫，且與幻覺過濾互補：避免把「根本沒聲音」的音訊送進 Whisper）。
        with self._lock:
            frames_snapshot = list(self._frames)
        self.is_silent = _compute_is_silent(frames_snapshot)

        wav_bytes = self._to_wav_bytes()
        if self.on_stop:
            self.on_stop(wav_bytes)
        return wav_bytes

    def _to_wav_bytes(self) -> bytes:
        if not self._frames:
            return b""
        audio = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
