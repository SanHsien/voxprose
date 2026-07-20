"""PTT (按住說話) 與 VAD 全時自動觸發模式的最小互斥邏輯。

背景（REVIEW.md 風險排序表 #10）：`audio/recorder.py`（PTT/切換熱鍵）與
`audio/auto_trigger.py`（v2.9.8 全時 VAD）各自開自己的 `sounddevice.InputStream`，
兩者完全獨立、互不知道對方存在。若使用者在全時模式錄音中又按下 PTT，或
PTT 錄音中 VAD 剛好偵測到語音起音，理論上會有兩路錄音同時啟動，導致同一
句話被處理兩次、甚至搶佔同一個麥克風裝置。

決策（見 docs/DECISIONS.md）：**PTT 優先**——PTT 是使用者主動按下按鍵的明確
動作，訊號強度與意圖清楚；VAD 是背景被動偵測，較不可靠（環境雜音、其他人
說話都可能誤觸發）。因此：

- PTT 開始錄音時，若 VAD 正在擷取一個語音段落，該段落會被要求捨棄
  （不送去處理），PTT 照常開始。
- VAD 偵測到語音起音時，若 PTT 正在錄音，這次 VAD 觸發直接被忽略——
  不疊加開第二路輸出；當這段語音真正結束時 (on_vad_segment_stop) 也一併
  丟棄，避免遲來的半段音訊被誤送進 STT。

這個類別刻意設計成不碰任何音訊 I/O（沒有 sounddevice/PyQt6 依賴），純粹
是一個小狀態機，方便在沒有安裝這些重量依賴的開發環境也能單元測試；實際
的麥克風擷取仍分別留在 audio/recorder.py 與 audio/auto_trigger.py，由
ui/app.py 呼叫這裡的方法來決定「這次要不要真的動作」。
"""


class PttVadMutex:
    """PTT／VAD 互斥狀態機（先來後到 + PTT 優先搶佔）。"""

    def __init__(self) -> None:
        self._ptt_active = False
        self._vad_active = False
        self._vad_suppressed = False

    def on_ptt_start(self) -> bool:
        """PTT（含切換模式）開始錄音時呼叫。

        回傳 True 代表目前有一段 VAD 語音正在擷取中，呼叫端必須捨棄它
        （呼叫 AutoTriggerController.abandon_current_segment()）。
        """
        preempted_vad = self._vad_active
        self._vad_active = False
        self._ptt_active = True
        return preempted_vad

    def on_ptt_stop(self) -> None:
        """PTT（含切換模式）停止錄音時呼叫。"""
        self._ptt_active = False

    def on_vad_segment_start(self) -> bool:
        """VAD 偵測到語音起音、即將開始擷取段落時呼叫。

        回傳 True 代表這次觸發應被忽略（PTT 正在錄音中，優先權較高）；
        呼叫端不應該顯示錄音中 UI 狀態，也不應該把稍後收到的音訊送去處理
        （見 on_vad_segment_stop）。
        """
        if self._ptt_active:
            self._vad_suppressed = True
            return True
        self._vad_suppressed = False
        self._vad_active = True
        return False

    def on_vad_segment_stop(self) -> bool:
        """VAD 語音段落結束、拿到音訊 bytes 時呼叫。

        回傳 True 代表這段音訊應該被丟棄，不送去 STT/LLM 處理——對應
        on_vad_segment_start 當時回傳 True（被 PTT 忽略）的那一次觸發。
        """
        self._vad_active = False
        suppressed, self._vad_suppressed = self._vad_suppressed, False
        return suppressed

    @property
    def ptt_active(self) -> bool:
        return self._ptt_active

    @property
    def vad_active(self) -> bool:
        return self._vad_active
