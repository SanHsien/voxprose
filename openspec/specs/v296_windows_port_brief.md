# v2.9.6 Mac 優化移植說明 — Windows Agent 專用

> **日期**：2026-03-20
> **Mac 版本**：v2.9.6 stable，BUILD-2960-STABLE
> **Windows 分支**：win-stable，目前在 v2.8.27（BUILD-2026-03-14-V90）
> **用途**：請 Windows agent 閱讀此文件，將以下所有優化從 Mac v2.9.6 移植至 Windows win-stable。
> **語氣**：直接照辦，不需要再詢問方向，細節已全部寫在這裡。
> **UI 框架**：兩版皆為 PyQt6，程式碼可直接移植，注意下列 Windows 特有差異。

---

## Windows 版特有差異（移植前必看）

| 項目 | Mac 版 | Windows 版 |
|------|--------|-----------|
| 主流程檔案 | `main.py` | `ui/app.py`（`_process_audio()` 方法） |
| Bundle 資源路徑 | `os.environ.get("RESOURCEPATH")` (py2app) | `sys._MEIPASS` (PyInstaller) |
| UI 字型 | `PingFang TC` | `Microsoft JhengHei` |
| 版本常數位置 | `paths.py` | `paths.py`（相同） |
| AppData 路徑 | `~/Library/Application Support/VoiceType4TW` | `%APPDATA%/VoiceType4TW` |
| 皮膚系統 | `ui/skin_manager.py` + `ui/skins/` | 相同結構，已存在 |

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

### 在主流程呼叫（Windows：`ui/app.py` 的 `_process_audio()` 方法）

找到 STT 結果取得後的位置（`text = self.stt.transcribe(...)` 之後），加入 **step 0.5**（在 LLM 之前）：

```python
# --- 0.5. 私人詞庫修正（有無 LLM 皆執行）---
try:
    from vocab.manager import apply_vocab_correction
    text = apply_vocab_correction(text)
except Exception as e:
    print(f"[process] Vocab correction error: {e}")
```

### 在 LLM prompt 注入詞彙（`_build_llm_prompt` 方法）

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

#### 2-1. 將記憶注入 LLM prompt（Windows：`ui/app.py` 的 `_build_llm_prompt` 方法）

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

## 三、UI 調整（設定視窗 — PyQt6，可直接移植）

Windows 版確認為 PyQt6，以下程式碼可直接使用。

---

### 3-0. Material Symbols 圖示系統（若 Windows 版尚未引入）

Mac 版使用 Material Symbols Outlined 字型渲染所有 icon，取代 emoji。
字型檔：`assets/fonts/MaterialSymbolsOutlined.ttf`（從 Mac repo 複製過去）。

在 `ui/settings_window.py` 頂部加入以下全域函式：

```python
_MS_FONT_LOADED = False
_MS_FONT_FAMILY = "Material Symbols Outlined"

_MS_CODEPOINTS = {
    "auto_awesome": "\ue65f", "balance": "\ueaf6", "bar_chart": "\ue26b",
    "bolt": "\uea0b", "build": "\uf8cd", "cloud_sync": "\ueb5a",
    "health_and_safety": "\ue1d5", "history": "\ue8b3", "home": "\ue9b2",
    "keyboard": "\ue312", "lock_open": "\ue898", "manage_accounts": "\uf02e",
    "menu_book": "\uea19", "mic": "\ue31d", "mic_external_on": "\uef5a",
    "psychology": "\uea4a", "settings": "\ue8b8", "shield": "\ue9e0",
    "smart_toy": "\uf06c", "terminal": "\ueb8e", "tune": "\ue429",
    "visibility": "\ue8f4",
}

def _load_ms_font():
    global _MS_FONT_LOADED, _MS_FONT_FAMILY
    if _MS_FONT_LOADED:
        return
    from PyQt6.QtGui import QFontDatabase
    import os, sys
    # PyInstaller bundle: sys._MEIPASS; dev: __file__-relative
    # Windows PyInstaller bundle: sys._MEIPASS; dev: __file__-relative
    if hasattr(sys, "_MEIPASS"):
        font_path = os.path.join(sys._MEIPASS, "assets", "fonts", "MaterialSymbolsOutlined.ttf")
    else:
        font_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "fonts", "MaterialSymbolsOutlined.ttf"
        )
    if os.path.exists(font_path):
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id >= 0:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                _MS_FONT_FAMILY = families[0]
    _MS_FONT_LOADED = True

def _ms_char(name: str) -> str:
    return _MS_CODEPOINTS.get(name, name)

def ms_icon(name: str, size: int = 18, color: str = "") -> "QLabel":
    """QLabel 顯示 Material Symbol icon（純文字模式，適合嵌入 layout）"""
    from PyQt6.QtWidgets import QLabel
    from PyQt6.QtCore import Qt
    _load_ms_font()
    lbl = QLabel(_ms_char(name))
    color_rule = f"color: {color};" if color else ""
    # 必須在 inline stylesheet 指定 font-family，否則被全域 QSS 覆蓋
    lbl.setStyleSheet(
        f"background: transparent; border: none; "
        f"font-family: '{_MS_FONT_FAMILY}'; font-size: {size}pt; {color_rule}"
    )
    lbl.setFixedSize(size + 8, size + 8)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl

def ms_icon_pixmap(name: str, size: int = 22, color: str = "#e4e1e6"):
    """渲染 Material Symbol 為 HiDPI QPixmap（用於 QIcon / 視窗 icon）"""
    from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor
    from PyQt6.QtCore import Qt, QRect
    _load_ms_font()
    dpr = 3  # Retina / HiDPI：3× 實體像素
    px_size = size * dpr
    px = QPixmap(px_size, px_size)
    px.setDevicePixelRatio(dpr)  # 設定後 QPainter 使用 logical 座標（0..size）
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QColor(color))
    font = QFont(_MS_FONT_FAMILY)
    font.setPixelSize(size - 2)  # logical pixel size
    p.setFont(font)
    p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, _ms_char(name))
    p.end()
    return px
```

> **關鍵陷阱（Windows 也會中）：**
> - `setDevicePixelRatio(3)` 後，QPainter 的座標系變為 logical（0 到 `size`），不是物理（0 到 `px_size`）。drawText 的 QRect 必須用 `(0, 0, size, size)`，用 `px_size` 會畫到界外 → 空白。
> - 全域 QSS `QLabel { font-family: 'XXX' }` 會覆蓋 `setFont()`。必須在 `setStyleSheet()` 裡加 `font-family`。

---

### 3-1. 危險按鈕（danger）邊框改灰色

找到 `skin_manager.py` 或 QSS 裡 `QPushButton#danger` 的規則，改成：

```python
# skin_manager.py build_qss() 內
QPushButton#danger {{
    background-color: transparent;
    border: 1px solid {s['bg_input_border']};  # 灰色，不要用 s['danger'] 粉紅
    color: {s['danger']};
}}
QPushButton#danger:hover {{
    background-color: {s['bg_input_border']};
    color: {s['danger']};
}}
```

---

### 3-2. AI 學習清單 — 新增刪除按鈕

在「AI 學習清單」的 `QListWidget` 旁加一個刪除按鈕（`objectName = "danger"`）：

```python
self.btn_delete_learned = QPushButton("刪除")
self.btn_delete_learned.setObjectName("danger")
self.btn_delete_learned.setFixedHeight(32)
self.btn_delete_learned.clicked.connect(self._delete_learned_word)

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
        QMessageBox.critical(self, "錯誤", str(e))
```

---

### 3-3. 長期記憶快照區塊 — 壓縮按鈕 + 記憶注入開關

在記憶相關 GlassCard 內加入以下元素（順序：注入開關 → 壓縮按鈕）：

```python
# 記憶注入 toggle（ToggleSwitch 或 QCheckBox 皆可）
mem_inject_lbl = QLabel("記憶注入")
self.memory_inject_toggle = ToggleSwitch(checked=self.config.get("memory_enabled", True))

# 壓縮按鈕
self.btn_purge_memory = QPushButton("壓縮本週記憶")
self.btn_purge_memory.setObjectName("danger")
self.btn_purge_memory.clicked.connect(self._purge_memory)

# 排列方式（同列）
purge_row = QHBoxLayout()
purge_row.addWidget(mem_inject_lbl)
purge_row.addWidget(self.memory_inject_toggle)
purge_row.addStretch()
purge_row.addWidget(self.btn_purge_memory)
```

壓縮邏輯：

```python
def _purge_memory(self):
    from memory.manager import load_memory
    count = len(load_memory().get("entries", []))
    if count == 0:
        QMessageBox.information(self, "記憶壓縮", "目前沒有可壓縮的記憶條目。")
        return
    reply = QMessageBox.question(
        self, "確認壓縮記憶",
        f"將 {count} 筆原始記錄壓縮為摘要，原始資料會歸檔保留。確定？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
    )
    if reply != QMessageBox.StandardButton.Yes:
        return
    from memory.manager import purge_and_summarize
    purged = purge_and_summarize()
    self._refresh_memory()
    QMessageBox.information(self, "壓縮完成", f"已壓縮 {purged} 筆記錄，摘要已更新。")
```

config 讀寫（`_load_data` / `_save_action`）：

```python
# _load_data:
self.memory_inject_toggle.setChecked(self.config.get("memory_enabled", True))

# _save_action:
self.config["memory_enabled"] = self.memory_inject_toggle.isChecked()
```

---

### 3-4. 同步狀態燈號改綠色

找到顯示同步狀態（ACTIVE / LOCAL）的地方，改用 RichText 雙色文字：

```python
from PyQt6.QtCore import Qt

is_synced = bool(sync_path)  # 根據 Windows 版的判斷邏輯調整
dot_color = "#00e676" if is_synced else "#888888"
txt_color = "#ffffff" if is_synced else "#888888"

status_badge = QLabel()
status_badge.setTextFormat(Qt.TextFormat.RichText)
status_badge.setText(
    f"<span style='color:{dot_color}'>●</span>"
    f"<span style='color:{txt_color}'> {'ACTIVE' if is_synced else 'LOCAL'}</span>"
)
```

---

## 四、版本號更新

在 `paths.py` 更新（Windows 版目前是 `BUILD-2026-03-14-V90` / v2.8.27）：

```python
BUILD_ID = "BUILD-2960-STABLE"
VERSION_NAME = f"2.9.6 {'Coffee' if EDITION == 'coffee' else 'Free'} Edition"
```

同時確認 `SkinManager.build_qss()` 的 `font_family` 預設值為 `"Microsoft JhengHei"`（Windows 版），不要改成 PingFang TC。

---

## 五、注意事項

1. **主流程在 `ui/app.py`**：Windows 版沒有獨立的 `main.py` 處理邏輯，STT→LLM pipeline 在 `ui/app.py` 的 `_process_audio()` 和 `_build_llm_prompt()`。
2. **詞彙修正的執行順序很重要**：必須在 STT 結果取得後、LLM 呼叫前執行，且不論是否開啟 LLM 都要執行。
3. **記憶注入只在 LLM 開啟時有效**：`memory_enabled` 為 True 且 LLM 功能開啟時才注入，避免在純 STT 模式浪費處理。
4. **`purge_and_summarize` 不會刪除歸檔**：原始資料永遠保留在 `archive/` 目錄，只是 `memory.json` 內的 `entries` 被清空換成摘要。
5. **edit-distance-1 只比對等長字串**：這是設計決定，避免誤觸短詞。
6. **字型不要動**：Windows 版 `SkinManager.build_qss()` 用 `Microsoft JhengHei`，不要改成 Mac 的 `PingFang TC`。
7. **Bundle 路徑**：Windows 用 PyInstaller，字型路徑用 `sys._MEIPASS`；已在第三節 3-0 的程式碼中處理好了。

---

*此文件由 Mac 端 Claude agent 於 2026-03-20 撰寫，供 Windows agent 同步移植使用。*
