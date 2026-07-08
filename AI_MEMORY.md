# 🧠 VoiceType4TW macOS 開發記憶 (2026-03-19 v2.9.0 Mac純化版)

- [2026-03-19] **Mac v2.9.0 發布**：Mac 專屬純化版，移除所有 Windows 殘碼，加入 EDITION 版本開關，修復記憶體洩漏，新增模型下載進度條，MLX dylib 正確打包。
- [2026-03-14] **Mac v2.8.27 旗艦標竿版發布**：成功建立 `v2.8.27-mac-stable` 標籤，同步 GitHub Release，並更新團隊成員 **CC58TW**。

## 🗄 重要路徑
| 路徑類型 | 路徑 |
|------|-------------------------------------------------------|
| App 資料 | `~/Library/Application Support/VoiceType4TW/` |
| debug log | `~/Library/Application Support/VoiceType4TW/debug.log` |
| sync_path.txt | `~/Library/Application Support/VoiceType4TW/sync_path.txt` |
| 打包輸出 | `<repo>/dist/` |

## ⚙️ 打包指令
```bash
# 完整打包（清舊檔 + py2app + DMG）
rm -rf build dist && bash build_all.sh

# 只重打 DMG（.app 已存在時用）
hdiutil detach "/Volumes/嘴炮輸入法" -force 2>/dev/null || true
rm -f dist/pack_temp.dmg dist/*.dmg
bash pack_dmg.sh
```
- **務必用 `python3.12`** 執行，不能用系統預設 python3（ServBay 是 3.14，套件裝在 3.12）
- `build_all.sh` 與 `pack_dmg.sh` 已統一改為 `python3.12`

## 🔑 MacOS Keycode 對照表
| 按鍵名稱 | Keycode | 備註 |
|----------|---------|------|
| `alt_r` | 61 | 右 Option |
| `ctrl_r` | 62 | 右 Control |
| `shift_r` | 60 | 右 Shift |
| `cmd_r` | 54 | 右 Command |
| `cmd` | 55 | 左 Command |
| `fn` | 63 | Fn |

---

## 🛠 關鍵技術突破紀錄 (v2.8.23 - v2.9.0)

### 1. 硬體優先熱鍵錄製 (v2.8.24)
- **問題**：使用者鍵盤輸出名稱與系統預設命名不符，導致儲存後 `listener.py` 抓不到事件。
- **解法**：錄製時直接捕捉 `NativeCode` 並儲存為 `(code:XX)` 格式，監聽器優先匹配代碼。

### 2. PyQt6 錄製器崩潰修復 (v2.8.25)
- **問題**：`AttributeError: type object 'Key' has no attribute 'Key_Fn'`
- **解法**：從錄製器檢查字典中拔除 `Key_Fn` 屬性。

### 3. MLX Whisper 光速啟動 (v2.8.24)
- **解法**：啟動時送入 1 秒靜音陣列 (`np.zeros(16000)`) 做 dummy 轉錄，預熱 Metal 推理圖。

### 4. 潤飾模式非同步時序修復 (v2.8.26)
- **根因**：`_on_stop` 立即恢復 `llm_enabled`，但 STT 還在背景跑。
- **解法**：將狀態恢復邏輯移至 `_process_audio` 開頭。

### 5. Whisper 幻覺過濾 (v2.8.27)
- 小於 0.5 秒 (8000 samples) 直接丟棄。
- 關鍵字過濾：長度在 45 字內含「點讚、分享、小鈴鐺」等字眼直接攔截。

### 6. 全域強制深色模式 (v2.8.27)
- `QApplication.setStyle("Fusion")` + `AppKit NSAppearance DarkAqua` 組合技，缺一不可。

### 7. EDITION 版本開關 (v2.9.0)
- **位置**：`paths.py` 第一行 `EDITION = "coffee"`
- **切換方式**：改成 `"free"` 即為免費版，`VERSION_NAME` 自動跟著變
- **功能分流**：Coffee 版顯示「🎭 靈魂情境」完整子選單；Free 版只顯示「🎭 底層靈魂」

### 8. 記憶體洩漏修復 (v2.9.0)
- **根因**：MLX Metal 快取無限成長，Python GC 不會自動清理。
- **解法**（`stt/mlx_whisper.py`）：
  - 每 10 次轉錄自動執行 `mx.metal.clear_cache()` + `gc.collect()`
  - 退出時主動清理（`_on_quit` 呼叫 `_clear_metal_cache()`）
- **參數**：`_CACHE_CLEAR_INTERVAL = 10`（可視狀況調整）

### 9. 模型下載進度條 (v2.9.0)
- **舊做法**：`setRange(0,0)` 跑馬燈，無實際進度。
- **新做法**：
  - `stt/mlx_whisper.py` 加入 `download_model(progress_callback)` — 用 `list_repo_files` + `hf_hub_download` 逐檔追蹤
  - `main.py` 新增 `download_signal = pyqtSignal(str, int)` 串接進度到 UI
  - `ui/settings_window.py` 的 `update_download_progress(status, pct, done)` 支援 0-100 真實百分比，pct=-1 切回跑馬燈
- **流程**：下載(0-100%) → 初始化 Metal(跑馬燈) → 載入 LLM(跑馬燈) → 完成隱藏

### 10. MLX dylib 打包修復 (v2.9.0)
- **問題**：`post_build_fix.py` 用錯 Python（ServBay python3 而非 python3.12），`site.getsitepackages()` 找不到 mlx。
- **解法**：
  - `post_build_fix.py` 的 `get_site_packages_path()` 加入 python3.12 framework 路徑作為 fallback
  - `pack_dmg.sh` 所有 `python3` 呼叫改為 `python3.12`
- **MLX 路徑**：`/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/mlx`

---

## 📦 DMG 打包地雷紀錄 (Lessons Learned)

### 1. hdiutil convert failed — 資源暫時無法取用
- **原因**：Finder 或前一次打包殘留的掛載點還在佔用。
- **解法**：`hdiutil detach "/Volumes/嘴炮輸入法" -force` 再重試。

### 2. MLX dylib 沒打進 bundle
- **症狀**：`[Post-Build Fix] Could not find site-packages containing 'mlx'`
- **根因**：`post_build_fix.py` 是用系統 python3 跑的，但 mlx 裝在 python3.12。
- **解法**：見上方「技術突破 #10」。

### 3. PyQt6 深色模式對抗
- `QApplication.setStyle("Fusion")` + `AppKit NSAppearance DarkAqua` 組合技，缺一不可。

### 4. STT 預熱不可省略
- 首次按錄音會凍結 5 秒，必須在啟動時做 dummy 轉錄預熱 Metal。

### 5. AppleScript 視窗座標偏移
- 加入 `delay 2` 與 `update without registering applications` 確保 Finder 渲染完再下座標。

### 6. EDITION 版本混入
- **防範**：所有版本功能開關統一讀 `paths.py` 的 `EDITION`，打包前只改這一個字。

---

## 🖥️ 系統需求（v2.9.0 起）
- **Apple Silicon Mac**（M1 或以上）— Intel Mac 不支援 MLX
- **macOS 13 Ventura 或更新版本**
- 安裝說明需明確標示，Intel 用戶無法使用

## 👥 主要開發團隊
- **吉米丘**：創始人與架構師。
- **CC58TW**：主要開發者與產品設計。
- **開發環境**：Python 3.12（`/usr/local/bin/python3.12`）+ PyQt6 + Metal/MLX

---

### 📅 2026-03-19 收工整理
- **完成**：v2.9.0 Mac 純化版開發與打包
  - 移除 Windows 殘碼（build_win.py, requirements-win.txt, ui/floating_button.py 等）
  - EDITION 版本開關統一化
  - 記憶體洩漏修復（Metal cache clear）
  - 模型下載進度條（真實百分比）
  - MLX dylib 正確打包進 DMG
- **發布**：`dist/嘴炮輸入法_v2.9.0-Coffee-Edition_macOS.dmg`（542MB）
- **待觀察**：測試者回饋後決定是否調整 `_CACHE_CLEAR_INTERVAL`

---

### 📅 2026-03-20 收工整理 — v2.9.2 Titanium UI 全面改版

#### 🎨 改版目標
將 `ui/settings_window.py` 所有頁面改寫為 Titanium Minimalism 風格（極簡鈦金）。用 Material Symbols Outlined 單色 icon 替換所有 emoji。

---

#### 🖼 頁面改版清單

**1. 詞彙 & 記憶 (`_create_vocab_mem_page`)**
- 左欄：搜尋框 + 詞彙列表 + 新增對話框按鈕 + 刪除按鈕（`_add_vocab_dialog` 用 QInputDialog）
- 右欄：AI學習清單 card + 長期記憶快照 card

**2. 數據統計 (`_create_stats_page`)**
- 標頭 + 重新整理按鈕
- 兩個摘要大字卡（今日辨識次數、累計省下時間、共辨識字數、今日字數）
- QTreeWidget 5 欄位 session 紀錄表格
- **重要**：stats 頁面用 `lbl_stats_*` 命名（`lbl_stats_today_count` 等）與 Dashboard 的 `lbl_today_count` 區分，`_refresh_stats()` 用 `hasattr` 同時更新兩組

**3. 系統設定 (`_create_general_page`)**
- 熱鍵區：每列一行（label 130px + HotkeyRecorderButton stretch + 測試按鈕 54px/11px 字型），`_hotkey_row()` 回傳 `QHBoxLayout`，用 `addLayout()` 加入
- 診斷區：`_diag_card()` 用 `QPushButton` 為容器 + 內部透明 QWidget，`resizeEvent` lambda 同步尺寸
- 偏好設定：4 個 ToggleSwitch 排 2×2 QGridLayout，`border: none`（無邊框）
- 進階設定：`ui_skin_combo` 隱藏保留（`hide()`，config 仍正常存讀）；3 個選項：`debug_demo_mode`、`output_prefix`、`showcase_mode`
- `separate_keystrike_log` 合併進 `debug_mode`，不再是獨立 toggle

**4. 雲端同步 (`_create_sync_page`)**
- 上排兩欄：同步狀態卡（路徑顯示 + 連結/取消按鈕 + ACTIVE/LOCAL badge）+ 安全性提醒卡（shield icon box）
- 下排 3 個功能說明卡：靈魂情境、詞彙同步、AI記憶

---

#### 🔤 Material Symbols Icon 系統

**字體檔**：`assets/fonts/MaterialSymbolsOutlined.ttf`（10MB variable font）

**核心發現與修復**：

| 問題 | 根因 | 解法 |
|------|------|------|
| 圖示顯示為文字（如 "home"） | Qt 預設不套用 OpenType ligature | 改用直接 Unicode codepoint（如 `\ue9b2`） |
| 全頁 QLabel icon 全部空白 | 全域 QSS `QLabel { font-family: 'PingFang TC' }` 蓋掉 `setFont()` | 在 `setStyleSheet()` 內加 `font-family: 'Material Symbols Outlined'` |
| `ms_icon_pixmap()` 輸出全黑空白 | `setDevicePixelRatio(3)` 後 QPainter 用 logical 座標（0~size），畫 `QRect(0,0,px_size,px_size)` 超出邊界 | 改畫 `QRect(0,0,size,size)` + `font.setPixelSize(size-2)` |
| Sidebar icon 低解析度 | pixmap 以 1× 實體尺寸渲染 | 建立 3× 實體像素 QPixmap（`px_size = size * 3`），`setDevicePixelRatio(3)` |
| 字體載入後 family 名稱不確定 | variable font 可能以不同名稱註冊 | `_load_ms_font()` 讀回 `applicationFontFamilies(font_id)[0]` 更新全域 `_MS_FONT_FAMILY` |

**Codepoints 對照（共 22 個）**：
```
home→e9b2, mic→e31d, settings→e8b8, bar_chart→e26b, auto_awesome→e65f
menu_book→ea19, cloud_sync→eb5a, keyboard→e312, build→f8cd, tune→e429
shield→e9e0, lock_open→e898, visibility→e8f4, mic_external_on→ef5a
health_and_safety→e1d5, history→e8b3, terminal→eb8e, psychology→ea4a
balance→eaf6, bolt→ea0b, manage_accounts→f02e, smart_toy→f06c
```

**Sidebar 選單 icon 對照**：
```
Dashboard→home, 辨識AI→mic, 靈魂設定→auto_awesome
詞彙記憶→menu_book, 雲端同步→cloud_sync, 數據統計→bar_chart, 系統設定→settings
```

---

#### 🎨 UI 細節決策

| 項目 | 決策 |
|------|------|
| 介面外觀／skin 選單 | **隱藏**（`ui_skin_combo.hide()`），config 仍保存。等新 skin 加入再開放 |
| danger 按鈕邊框 | 改為 `s['bg_input_border']`（#2a2a2e 灰），文字保持粉紅 |
| 偏好 toggle 格子 | 無邊框（`border: none`），背景 `s['bg_input']` |
| StatusChip 置中 | 所有 `addWidget` 加 `alignment=Qt.AlignmentFlag.AlignHCenter` |
| ModelStatusLight 置中 | 移除 `addStretch()`，layout/top_row/desc 全部 `AlignHCenter` |

---

*此記憶文件由 AI 於 2026-03-20 更新，標記 v2.9.2 Titanium UI 全面改版里程碑。*

---

### 📅 2026-03-20 收工整理 — v2.9.6 stable 功能完成 & DMG 打包

#### 🔧 功能新增

**1. 詞彙模糊修正（vocab/manager.py）**
- 新增 `_edit_distance_1()` + `apply_vocab_correction()` — 滑動視窗 edit-distance-1 比對
- 解決同音異字問題（嘴炮 ↔ 嘴砲），Whisper 輸出後立即修正（step 0.5，LLM 前後皆執行）
- LLM prompt 也注入詞彙強制修正指引（step 5）

**2. 長期記憶注入（memory/manager.py + main.py）**
- `get_context_for_llm()` 原本有定義但**從未被呼叫**，現在整合至 `_build_llm_prompt()` step 6
- 由 `memory_enabled` config 控制開關
- 新增 `purge_and_summarize()`：手動壓縮所有 entries → digest（top-15 詞彙 + 5 代表語句），原始資料歸檔保留
- UI 增加「壓縮本週記憶」按鈕 + 記憶注入 toggle（位於 purge 列前）

**3. AI 學習清單 — 刪除功能**
- 新增「刪除」按鈕，呼叫 `vocab.manager.remove_learned_word()`
- 清單高度固定 148px（約 6 筆），騰出空間給長期記憶區塊

**4. 同步燈號改綠**
- 同步狀態 ACTIVE 燈改為 `#00e676`（綠色），與模型狀態燈一致
- 使用 RichText `<span>` 實現雙色文字

#### 🐛 Icon 系統 Bug 修正

| 問題 | 根因 | 修正 |
|------|------|------|
| `ms_icon_pixmap()` 輸出空白 | `setDevicePixelRatio(3)` 後 QPainter 使用 logical 座標，QRect 不能用 px_size | 改用 `QRect(0,0,size,size)` + `setPixelSize(size-2)` |
| 頁面 icon 顯示錯誤字元 | 全域 QSS `QLabel { font-family }` 覆蓋 `setFont()` | inline `setStyleSheet()` 加入 `font-family` |
| Bundle 內字型找不到 | `__file__` 解析至 `lib/python3.12/`，非 Resources | 改用 `os.environ.get("RESOURCEPATH")`（py2app 設定） |

#### 📦 版本標記 & 打包

| 項目 | 值 |
|------|-----|
| BUILD_ID | `BUILD-2960-STABLE` |
| Coffee Edition DMG | `嘴炮輸入法_v2.9.6-Coffee-Edition_macOS.dmg` |
| Free Edition DMG | `嘴炮輸入法_v2.9.6-Free-Edition_macOS.dmg` |
| Git commit | `b9f997b` |
| 目前 paths.py EDITION | `coffee`（預設） |

---

*此記憶文件由 AI 於 2026-03-20 更新，標記 v2.9.6 stable 里程碑。*

## 2026-05-14 重要 carry-over

- MLX 必須鎖在 `>=0.29,<0.30`：MLX 0.30+ wheel = `macosx_26_0_arm64` + MSL 4.0 metallib，只能跑 macOS 26+；對 macOS 13/14/15 使用者會 `RuntimeError: Unable to load kernel ...` 或 C-level abort。詳見 `requirements.txt` 註解、`CLAUDE.md` MLX Version Pin 段落、`openspec/specs/mlx-version-pin/spec.md`。要升級必須開新 Spectra change 並在 design.md 解釋是否要放棄 macOS 13/14/15 支援。
- v2.9.13 build pipeline 內建 `scripts/pre_build_check.py` 守衛，發現 MLX 太新會直接 abort 不繼續 build。

## 2026-05-24 v2.9.16 長靜音幻覺修復

- 修正 30 秒純靜音會被 MLX Whisper 辨識成「多謝您的觀看。」的案例；`stt/mlx_whisper.py` 增加中文 / 粵語式 YouTube 結尾片語與高比例重複 token / n-gram 偵測。
- 修正翻譯模式污染 STT：`main.py` 改用 `stt.language.get_transcription_language(config)`，STT 永遠讀 `language`，`translation_lang` 只給 LLM prompt 翻譯輸出使用。
- 本機 `mlx-community/whisper-medium-mlx` cache 可搬到外部模型快取目錄，原 Hugging Face cache 位置保留 symlink。
- 驗證重點：30 秒純靜音 STT 回空字串；source app / dist app 啟動後都能透過 symlink 找到模型並進入 `Models are READY`。
