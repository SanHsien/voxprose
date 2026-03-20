# v2.9.6 Mac 優化移植說明 — Windows Agent 專用

> **日期**：2026-03-20
> **Mac 版本**：v2.9.6 stable，BUILD-2960-STABLE
> **用途**：請 Windows agent 閱讀此文件，將以下所有優化移植至 Windows 版。
> **語氣**：直接照辦，不需要再詢問方向，細節已全部寫在這裡。

---

## 一、詞彙模糊修正（vocab 系統）

### 問題背景
Whisper STT 對同音異字（例如「嘴炮」vs「嘴砲」）無法穩定輸出，`initial_prompt` 只是提示，不保證結果。

### Mac 修正方案（已實作）
在 `vocab/manager.py` 加入 **edit-distance-1 滑動視窗** 模糊比對，在 STT 輸出後、LLM 輸入前執行替換。

**新增兩個函式：**

```python
def _edit_distance_1(a: str, b: str) -> bool:
    """判斷兩個等長字串的編輯距離是否為 1（只差一個字元）"""
    if len(a) != len(b):
        return False
    diff = sum(1 for x, y in zip(a, b) if x != y)
    return diff == 1

def apply_vocab_correction(text: str) -> str:
    """
    對 STT 輸出文字做詞彙修正：
    - 精確比對：直接替換
    - edit-distance-1 模糊比對：替換並 log
    只處理長度 >= 3 的詞彙，由長到短排序（避免短詞覆蓋長詞）
    """
    custom = load_custom_vocab()
    targets = sorted([w for w in custom if len(w) >= 3], key=len, reverse=True)
    for vocab_word in targets:
        wlen = len(vocab_word)
        i = 0
        result = []
        while i <= len(text) - wlen:
            substr = text[i:i + wlen]
            if substr == vocab_word:
                result.append(vocab_word)
                i += wlen
            elif _edit_distance_1(substr, vocab_word):
                result.append(vocab_word)
                i += wlen
                print(f"[vocab] 修正: 「{substr}」→「{vocab_word}」")
            else:
                result.append(text[i])
                i += 1
        result.append(text[i:])
        text = "".join(result)
    return text
```

**同時新增刪除詞彙函式（供 UI 呼叫）：**

```python
def remove_learned_word(word: str):
    """從 AI 自動學習清單中刪除指定詞彙"""
    memory = load_auto_memory()
    if word in memory:
        del memory[word]
        _save_auto_memory(memory)
```

### 在主流程呼叫（main.py / 主要處理函式）

找到 STT 結果取得後的位置，加入 **step 0.5**（在 LLM 之前）：

```python
# --- 0.5. 私人詞庫修正（有無 LLM 皆執行）---
try:
    from vocab.manager import apply_vocab_correction
    text = apply_vocab_correction(text)
except Exception as e:
    print(f"[process] Vocab correction error: {e}")
```

### 在 LLM prompt 注入詞彙（main.py `_build_llm_prompt`）

在建構 prompt 的函式中加入 **step 5**（LLM 指引）：

```python
# 5. 私人詞彙強制修正指引
try:
    from vocab.manager import load_custom_vocab
    custom = load_custom_vocab()
    if custom:
        vocab_str = "、".join(list(custom)[:40])
        parts.append(
            f"〔私人詞庫強制修正〕\n"
            f"以下詞彙為使用者定義的正確用字，請優先使用這些詞彙輸出，不得改用同音異字：\n"
            f"{vocab_str}"
        )
except Exception:
    pass
```

---

## 二、長期記憶系統強化（memory 系統）

### 問題背景
`memory/manager.py` 中的 `get_context_for_llm()` 函式原本已定義，但**從未被呼叫**，長期記憶是死功能。

### Mac 修正方案（已實作）

#### 2-1. 將記憶注入 LLM prompt（main.py `_build_llm_prompt`）

在建構 prompt 的函式中加入 **step 6**：

```python
# 6. 長期記憶上下文
if self.config.get("memory_enabled", False) and not is_assistant:
    try:
        from memory.manager import get_context_for_llm
        mem_ctx = get_context_for_llm()
        if mem_ctx:
            parts.append(
                f"〔使用者記憶背景〕\n{mem_ctx}\n"
                f"（以上為歷史脈絡，僅供語氣與用詞參考，勿直接複製輸出。）"
            )
    except Exception:
        pass
```

> `is_assistant` = 目前輸出模式是否為助理角色模式（若 Windows 版有此概念）。若沒有，直接用 `self.config.get("memory_enabled", False)` 即可。

#### 2-2. 新增 `purge_and_summarize()` 函式（memory/manager.py）

此函式讓使用者手動壓縮當週記憶，避免每次都把 50 筆原始紀錄塞進 prompt：

```python
def purge_and_summarize() -> int:
    """
    手動觸發：將所有記憶條目壓縮為緊湊摘要，原始資料歸檔保留。
    回傳被壓縮的筆數（0 表示無資料）。
    """
    _ensure_dirs()
    memory = load_memory()
    entries = memory.get("entries", [])
    if not entries:
        return 0

    # 歸檔原始資料
    week_str = datetime.now().strftime("%Y-W%W")
    archive_path = ARCHIVE_DIR / f"memory_{week_str}_purge.json"
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump({
            "archived_at": datetime.now().isoformat(timespec="seconds"),
            "entries": entries,
            "previous_summary": memory.get("summary", ""),
        }, f, ensure_ascii=False, indent=2)

    new_summary = _generate_digest(entries, memory.get("summary", ""))
    count = len(entries)
    memory["entries"] = []
    memory["summary"] = new_summary
    memory["last_archive"] = datetime.now().isoformat(timespec="seconds")
    save_memory(memory)
    print(f"[memory] Purged {count} entries → digest saved. Archive: {archive_path}")
    return count
```

確認 `_generate_digest()` 函式存在（Mac 版已有）。若 Windows 版沒有，加入以下：

```python
def _generate_digest(entries: list, old_summary: str = "") -> str:
    import re
    from collections import Counter

    all_texts = [e.get("llm") or e.get("stt", "") for e in entries]
    full_text = " ".join(all_texts)

    # 最常用 2-6 字中文詞彙 top 15
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', full_text)
    top_words = [w for w, _ in Counter(words).most_common(15)]

    # 代表性短句：5~35 字，最多 5 句
    sentences = []
    for text in all_texts:
        for part in re.split(r'[。！？；\n]', text):
            part = part.strip()
            if 5 <= len(part) <= 35:
                sentences.append(part)
    representative = list(dict.fromkeys(sentences))
    representative = sorted(representative, key=len)[:5]

    date_start = entries[0].get("ts", "")[:10] if entries else ""
    date_end = entries[-1].get("ts", "")[:10] if entries else ""
    total_chars = sum(len(t) for t in all_texts)

    parts = [
        f"[{date_start}～{date_end} · {len(entries)} 筆 · {total_chars} 字]",
        f"主要用詞：{'、'.join(top_words) if top_words else '(無)'}",
    ]
    if representative:
        parts.append("代表語句：" + "；".join(representative))

    new_digest = "\n".join(parts)
    if old_summary:
        return old_summary + "\n\n" + new_digest
    return new_digest
```

---

## 三、UI 調整（設定視窗）

> Windows 版 UI 框架可能不同（PyQt6 / tkinter / 其他）。以下描述**功能邏輯**，請對應至 Windows 版的 UI 元件。

### 3-1. AI 學習清單 — 新增刪除按鈕

在「AI 學習清單」（自動學到的詞彙列表）旁邊加一個刪除按鈕：

- 按鈕文字：「刪除」
- 行為：取得清單中目前選取的詞彙（格式可能是 `詞彙 (次數)`，取 ` (` 前的部分），呼叫 `vocab.manager.remove_learned_word(word)`，然後刷新清單。

```python
def _delete_learned_word(self):
    item = self.learned_list.currentItem()
    if not item:
        return
    word = item.text().split(" (")[0]
    try:
        from vocab.manager import remove_learned_word
        remove_learned_word(word)
        self._refresh_learned_vocab()
    except Exception as e:
        # 顯示錯誤提示
        print(f"刪除失敗: {e}")
```

### 3-2. 長期記憶快照區塊 — 增加資訊與壓縮按鈕

在設定視窗的記憶區塊（若有）加入：

1. **摘要顯示**：讀取 `memory.get("summary", "")` 顯示現有摘要內容（截斷顯示，例如前 200 字）
2. **筆數顯示**：`len(memory.get("entries", []))` 筆原始記錄
3. **「壓縮本週記憶」按鈕**：呼叫 `purge_and_summarize()`，完成後刷新顯示

```python
def _purge_memory(self):
    from memory.manager import load_memory
    count = len(load_memory().get("entries", []))
    if count == 0:
        # 提示：沒有可壓縮的記憶
        return
    # 確認對話框：「將 {count} 筆原始記錄壓縮為摘要，確定？」
    from memory.manager import purge_and_summarize
    purged = purge_and_summarize()
    self._refresh_memory()
    # 提示：已壓縮 {purged} 筆
```

### 3-3. 「記憶注入」開關

在記憶相關區塊加一個 toggle 開關（或 checkbox）：

- 標籤：「記憶注入」
- 對應 config key：`memory_enabled`（bool，預設 `True`）
- 儲存時寫入 config，讀取時從 config 載入

---

## 四、版本號更新

在 Windows 版對應的版本常數位置（類似 `paths.py` 的 `BUILD_ID` / `VERSION_NAME`）更新：

```
BUILD_ID = "BUILD-2960-STABLE"
VERSION_NAME = "2.9.6 {Edition} Edition"  # Coffee / Free
```

---

## 五、注意事項

1. **詞彙修正的執行順序很重要**：必須在 STT 結果取得後、LLM 呼叫前執行，且不論是否開啟 LLM 都要執行。
2. **記憶注入只在 LLM 開啟時有效**：`memory_enabled` 為 True 且 LLM 功能開啟時才注入，避免在純 STT 模式浪費處理。
3. **`purge_and_summarize` 不會刪除歸檔**：原始資料永遠保留在 `archive/` 目錄，只是 `memory.json` 內的 `entries` 被清空換成摘要。
4. **edit-distance-1 只比對等長字串**：這是設計決定，避免誤觸短詞。若 Windows 版詞彙結構不同（例如有拼音），調整 `_edit_distance_1` 的判斷邏輯。
5. **Windows 版路徑系統**：確認 `memory/manager.py` 的 `DATA_DIR` 指向正確的 Windows AppData 路徑（Windows 版應有對應的 `paths.py` 或等效設定）。

---

*此文件由 Mac 端 Claude agent 於 2026-03-20 撰寫，供 Windows agent 同步移植使用。*
