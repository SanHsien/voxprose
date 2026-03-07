# 🧠 VoiceType4TW macOS 開發記憶 (2026-03-06 穩定測試版更新)

## 📍 專案當前狀態
- **版本**: v2.8.27-dev (BUILD-0306-P)
- **狀態**: **[APP 穩定測試版]** - 核心熱鍵引擎、錄製器、非同步邏輯已全面加固。
- **核心功能**: 
  - 支援全鍵盤熱鍵 (PgUp/PgDn/方向鍵等)。
  - 錄製器支援直接存儲硬體 Keycode (`code:XX`)，解決名稱對應失敗問題。
  - MLX Whisper 冷啟動優化（1s Dummy Warmup）。
  - 修復了 LLM 潤飾模式在 STT 處理期間提早恢復狀態的 Race Condition。
  - 內建 STT 幻覺過濾器 (VAD) 與防誤觸機制。
  - 圖示重製：無白邊 icon-2 版本。
  - 字型準備：支援 `assets/fonts/` 自動封裝。

## 🗄 重要路徑
| 路徑類型 | 路徑                                                    |
|------|-------------------------------------------------------|
| App 資料 | `~/Library/Application Support/VoiceType4TW/`         |
| debug log | `~/Library/Application Support/VoiceType4TW/debug.log` |
| sync_path.txt | `~/Library/Application Support/VoiceType4TW/sync_path.txt` |
| 打包輸出 | `/Volumes/JDATA/playground/voicetype-mac/dist/`      |

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

## 🛠 關鍵技術突破紀錄 (v2.8.23 - v2.8.27)

### 1. 硬體優先熱鍵錄製 (v2.8.24)
- **問題**：使用者鍵盤輸出名稱與系統預設命名不符（如右 Ctrl 輸出 code 54），導致儲存後 `listener.py` 抓不到事件。
- **解法**：重構 `SettingsWindow` 錄製器。錄製時直接捕捉 `NativeCode` 並儲存為 `(code:XX)` 格式。監聽器 `HotkeyListener` 優先匹配代碼，徹底解決「錄得到、存得進、但按不出」的顽疾。

### 2. PyQt6 錄製器崩潰件修復 (v2.8.25)
- **問題**：錄製熱鍵時噴出 `AttributeError: type object 'Key' has no attribute 'Key_Fn'`。
- **根因**：PyQt6 在新版中移除了 `Qt.Key.Key_Fn`。只要按下鍵盤，判斷式就會爆炸導致後續儲存流程中斷。
- **解法**：從錄製器檢查字典中拔除 `Key_Fn` 屬性。

### 3. MLX Whisper 光速啟動 (v2.8.24)
- **問題**：第一次錄音會卡住 5 秒進行 Metal 推理初始化。
- **解法**：在 `stt/mlx_whisper.py` 實作 dummy 轉錄。啟動時送入 1 秒的靜音陣列 (`np.zeros(16000)`)，預熱顯示卡推理圖。

### 4. 潤飾模式非同步時序修復 (v2.8.26)
- **問題**：按下潤飾熱鍵（強制開啟 LLM）講話，結果只有 STT 輸出。
- **根因**：`_on_stop` (放開按鍵時) 立即將 `llm_enabled` 恢復為原本的 False，但此時 STT 還在背景處理音訊。兩秒後讀取到的開關已變回 False。
- **解法**：將狀態恢復邏輯從 `_on_stop` 移至 `_process_audio` 開頭，並在處理開始前立刻鎖定當下的開關變數。

### 5. Whisper 幻覺過濾 (v2.8.27)
- **問題**：誤觸按鈕（短暫音訊）會讓 Whisper 噴出「點讚、訂閱、下期再見」。
- **解法**：
  - **長度門檻**：小於 0.5 秒 (8000 samples) 的音訊直接丟棄。
  - **關鍵字過濾**：建立幻覺關鍵字清單，長度在 45 字內包含「點讚、分享、小鈴鐺」等字眼時直接攔截不輸出。

---

## 👥 開發交接與環境遷移 (cc58tw)
- **接手開發者代號**: `cc58tw`
- **遷移目標**: 在新電腦上完整復原開發環境（Python 3.12 + PyQt6 + Metal/MLX）。
- **關鍵注意事項**:
  - 務必將 `~/.gemini/antigravity/brain/e5c8abbf-7d63-4e11-9d65-b8e8933129b1` 目錄完整備份並移動到新電腦對應位置，AI 才能繼承目前的開發邏輯與進度。
  - 新機器需安裝 `ffmpeg` 與 Xcode Command Line Tools 以支援 `mlx`。

---

---

## 🏁 Windows 版本移植與打包計畫 (2026-03-08 新增)
- **目標**: 實作 Windows 獨立執行檔 (.exe) 發布。
- **關鍵技術修正**:
  1. **CUDA 與 PyQt6 初始化衝突**: Windows 上必須**先載入 STT (CUDA)** 才能匯入 PyQt6，否則進程會無預警結束。
  2. **系統托盤**: Windows 使用 `pystray` 替代 `rumps`。在 `main.py` 中已實作分流載入。
  3. **自動化打包**: 已建立 `build_win.py`。
- **後續 Agent 執行守則 (Windows 環境)**:
  1. **取得代碼**：
     - 如果 PC 上還沒有代碼：執行 `git clone https://github.com/jfamily4tw/pirates-team`。
     - 如果 PC上已有舊版：進入該目錄執行 `git pull origin main`。
     - *註：資料夾名稱不重要（可以是 VoiceType4TW 或 pirates-team），重點是 Git 遠端必須指向上述網址。*
  2. **環境初始化**：
     - 安裝 Python 3.12 (建議使用 official python.org 版本)。
     - 在目錄內打開終端機 (PowerShell/CMD) 執行：`pip install -r requirements-win.txt`。
  3. **構建與打包**：
     - 執行 `python build_win.py`。
  4. **修復 STT 運行庫**：
     - 打包後若執行 `.exe` 提示缺少 DLL，需從 `venv/Lib/site-packages/ctranslate2` 或相關目錄複製 `cudnn_*.dll` 至 `dist/VoiceType4TW/`。

---
*此記憶文件由 AI 於 2026-03-08 更新，為明日 Windows 打包任務留存上下文。*
