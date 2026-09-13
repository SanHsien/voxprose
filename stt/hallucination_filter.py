"""Whisper 幻覺過濾（口頭禪/YouTube 結尾片語偵測）。

移植自舊版 Mac 主線（`git show 51094bf:stt/mlx_whisper.py`）的
`_is_hallucination` / `_has_dominant_repetition`。原本這套邏輯內嵌在
MLX-only 的 `stt/mlx_whisper.py`（Apple Silicon 專屬引擎）裡，只對走 MLX
引擎的轉錄結果生效；win-stable（本 Windows-only 樹）完全沒有 MLX，也從未有
任何等效的幻覈過濾，是相對 main 分支的明確功能倒退（見 REVIEW.md 2026-07-19
第 6 節、風險排序表 #3）。

這裡把純文字邏輯抽成一個不依賴任何 STT 引擎實作的獨立模組，接在
`ui/app.py:_process_audio` 收到 STT 結果之後、詞庫修正之前的統一路徑呼叫
（見該檔案），對所有引擎一視同仁生效——不管文字是本地 Whisper 子行程
（`stt/subprocess_whisper.py`）算出來的，還是 Groq/OpenRouter/Gemini 等雲端
API 回傳的。刻意不放進 `stt/subprocess_whisper.py` 的子行程內，避免子行程與
主行程之間的 IPC 訊息格式因此變複雜（子行程只需要專心做轉錄）。
"""
import re

# Whisper 在靜音 / 雜訊 / 過短音檔時會憑空編出 YouTube 結尾片語（訓練資料偏差）。
# 中英都會出現，且常出現「片語. 片語. 片語.」串連，所以採「分句後 set 全在黑名單」的策略。
# 不做子字串匹配（避免誤殺「我覺得謝謝收看的設計很好」這種正常句子）。
_WHISPER_HALLUCINATION_PHRASES = frozenset(p.lower() for p in {
    # 中文 YouTube 結尾片語
    "謝謝收看", "謝謝觀看", "謝謝大家", "謝謝大家的收看", "謝謝大家的觀看",
    "多謝收看", "多謝觀看", "多謝你的觀看", "多謝您的觀看",
    "多謝你的收看", "多謝您的收看",
    "感謝收看", "感謝觀看", "感謝你的觀看", "感謝您的觀看", "感謝大家的收看", "感謝大家的觀看",
    "感謝你的收看", "感謝您的收看",
    "我們下次再見", "我們下集再見", "下次見", "下集再見", "下次再見", "我們下次見",
    "請訂閱", "請按讚", "請按讚訂閱", "別忘了訂閱", "記得訂閱", "請按讚並訂閱",
    "別忘了按讚訂閱", "別忘了按讚訂閱開啟小鈴鐺", "記得按讚訂閱開啟小鈴鐺",
    "按讚訂閱開啟小鈴鐺",
    # 英文 YouTube 結尾片語
    "thank you for watching", "thanks for watching", "thank you",
    "thank you so much for watching", "thanks so much for watching",
    "thank you for listening", "thanks for listening",
    "please subscribe", "subscribe", "subscribe to my channel",
    "like and subscribe", "like comment and subscribe", "like, comment and subscribe",
    "like comment subscribe", "please like and subscribe", "don't forget to subscribe",
    "remember to subscribe", "hit the subscribe button", "hit that subscribe button",
    "bye", "bye bye", "goodbye", "see you next time", "see you", "see ya",
    # 字幕組 / 上傳者水印
    "字幕由amara.org社群提供", "字幕由 amara.org 社群提供",
    "由 amara.org 社群提供", "由amara.org社群提供",
    "subtitles by the amara.org community", "subtitles by the amara org community",
    "amara.org",
    "mbc뉴스", "mbc 뉴스",
    # 過短口頭禪（單字節 hallucination）
    "嗯", "啊", "喔", "哦", "嗯哼", "呃", "嗯嗯",
    "。", "...", "…",
})

# 拆句符號（中英文標點均可）
_SENTENCE_SPLIT = re.compile(r"[。.!?！？]+")
_TOKEN_RE = re.compile(r"[a-zA-Z]+|[一-鿿]+")


def _has_dominant_repetition(text: str) -> bool:
    """Return True when one token/ngram dominates the whole transcript.

    Whisper silent-tail failures often look like "通過 通過 ..." or
    "anterior access anterior access ..." rather than a known ending phrase.
    This detects only heavy repetition so normal mixed-language dictation stays.
    """
    tokens = _TOKEN_RE.findall(text.lower())
    if len(tokens) < 12:
        return False

    for n in range(1, 5):
        if len(tokens) < n * 8:
            continue
        counts = {}
        for i in range(0, len(tokens) - n + 1):
            gram = tuple(tokens[i:i + n])
            counts[gram] = counts.get(gram, 0) + 1
        repeats = max(counts.values(), default=0)
        if repeats >= 8 and (repeats * n) / len(tokens) >= 0.65:
            return True
    return False


def is_hallucination(text: str) -> bool:
    """判斷 text 是否「整段都是已知 Whisper 幻覺片語」。

    處理三種情形：
    1. 完整單一片語：「Thank you for watching」
    2. 重複拼接：「Thank you for watching.Thank you for watching.」
    3. 中英混雜重複：「Thanks. 謝謝大家.」

    用 lower-case + 去尾標點 + 拆句後對 frozenset 比對；不做子字串匹配。
    """
    if not text:
        return False
    stripped = text.strip().rstrip("。.!?！？,，、 \t\n").lower()
    if not stripped:
        return False
    # 1) 整段就是一條片語
    if stripped in _WHISPER_HALLUCINATION_PHRASES:
        return True
    # 2/3) 拆句後每一句都是片語
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(stripped) if p.strip()]
    if parts and all(p in _WHISPER_HALLUCINATION_PHRASES for p in parts):
        return True
    # 4) 容忍短雜訊：忽略 ≤2 字元的短片段（如「E」「Eh」），剩下若全是幻覺也丟。
    # 用於擋 "E...E...Thank you for watching.Thank you for watching." 這種模式。
    meaningful = [p for p in parts if len(p) > 2]
    if meaningful and all(p in _WHISPER_HALLUCINATION_PHRASES for p in meaningful):
        return True
    # 5) 長尾重複幻覺：例如「通過」連發或英文片語重複到支配整段。
    if _has_dominant_repetition(stripped):
        return True
    return False
