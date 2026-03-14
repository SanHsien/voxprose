# 🧠 VoiceType4TW macOS 開發記憶 (2026-03-06 穩定測試版更新)

## 📍 專案當前狀態
- **版本**: v2.8.27 (Stable)
- **狀態**: **[正式穩定版]** - 全域深色模式適配、Coffee/Free 雙版本發佈。
- **核心功能**: 
  - 全域強制深色模式 (Lock Dark Appearance & Fusion Style)。
  - 系統列圖示 (Tray Icon) 支援 macOS Template 模式（隨系統換色）。
  - 自動化打包流程：一鍵產出 Coffee 版與 Free 版 DMG。
  - 修復 MLX 與 OpenSSL 在封裝內部的二進位路徑相容性。
  - 支援全鍵盤熱鍵與硬體碼 (NativeCode) 錄製。

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

### 6. 全域強制深色模式與 UI 加固 (v2.8.27-Stable)
- **問題**：系統處於「淺色模式」時，設定視窗背景、下拉選單噴白，影響品牌一致性。
- **解法**：
  - **Qt 層級**：使用 `setStyle("Fusion")` 並鎖定 `QPalette` 的深色調。
  - **系統層級**：透過 `AppKit` 調用 `setAppearance_("DarkAqua")`，鎖定原生選單外觀。
  - **DMG 層級**：建立帶有背景圖與應用程式捷徑連結的正規 DMG 封裝。

### 7. Coffee / Free 雙版本發佈機制
- **區分核心**：透過 `ui/menu_bar.py` 與 `setup.py` 的版本標籤實作功能分流。
- **自動化**：`build_all.sh` 配合 `pack_dmg.sh` 支援環境清理、補丁修復與最終打包。

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

## 🧪 Windows 穩定性開發專項 (2026-03-12)

### 1. STT Lab 實驗室成果
- **目標**: 徹底解決 `dist` 打包後在 Windows 上的 Access Violation (0xC0000005) 崩潰。
- **架構決策**: 採用 **「子進程隔離 (Subprocess Isolation)」** 方案。
  - 主進程: PyQt6 GUI + 錄音。
  - 子進程: `stt_worker.py` (執行 `faster-whisper`)。
- **關鍵補丁**:
  - `AllocConsole()`: 徹底解決 `--windowed` 模式下 C++ 引擎（ctranslate2）寫入控制台導致的 Access Violation。
  - `tqdm` 猴子補丁: 徹底禁用 `tqdm` 監控執行緒。
- **實驗紀錄 (Lab-10)**: 
  - 放棄 `openai-whisper` (Lab-09) 的純 PyTorch 模式，因其在 Frozen 環境下會出現 Numpy 找不到的問題。
  - 恢復使用 `faster-whisper` 並鎖定 DLL 路徑。

### 2. Windows Python Stable Version (V72-PYTHON-STABLE)
- **維護日期**: 2026-03-13 01:15
- **狀態**: **[核心功能完成 / 部署環境待穩固]**
- **今日進度深度分析**:
    - **Inno Setup (ISS) 部署優化**:
        - **旗標修復**: 修正了 `voicetype_installer.iss` 中的語法地雷。原本 `Source` 行使用了錯誤的 `ig` 旗標（正確應為 `ignoreversion`），導致編譯器拒絕運作。
        - **語系適配**: 成功啟用 `chinesetraditional`。注意：ISS 本身必須安裝繁體中文語言包，且腳本內需取消 `compiler:Languages\ChineseTraditional.isl` 的註釋。
        - **打包清理 (The Great Cleaning)**: 為了維持「旗艦感」，在 `Source: "*"` 實作了極其嚴格的 `Excludes` 清單。這包括所有 `test_*.py`、`main2.py`、`.git`、`venv`、以及含有開發敏感資訊的 `INTERNAL_TODO.md`。產出的安裝包體積從原本的雜亂，縮減為僅含核心運行的精簡版。
    - **啟動腳本 (BAT) 的自動化演進**:
        - **解決亂碼與絕對路徑**: 引入 `chcp 65001` (UTF-8) 與清空環境變數。最關鍵的改進是導入 `%~dp0`，確保無論使用者是從「開始功能表捷徑」、「安裝目錄」或是「桌面啟動」，腳本都能正確定位 `venv` 與專案根目錄。
        - **Python 智慧檢索**: 建立了一套檢索層級：`py -0` (Launcher) -> `python --version` -> `winget` 自動安裝。這解決了使用者電腦裝了 Python 但「沒加進 PATH」的常見災難。
- **針對下一位 Agent 的技術交接 (Transfer Notes)**:
    - **致命問題：發佈後 BAT 檔執行失敗**
        - **現象描述**: 儘管開發端測試正常，但打包成 ZIP 或經由 Inno Setup 安裝後，`run_voicetype.bat` 依然可能在使用者電腦上噴出「系統找不到指定的路徑」或完全無反應（疑似亂碼解析錯誤）。
        - **分析**: 可能是 Inno Setup 在複製檔案時改變了檔案編碼（BOM vs Non-BOM），或是 CMD 在解析帶有中文字元的路徑時，即使有 `chcp 65001` 依然出現對齊問題。
        - **解決方向**: 下一個階段應考慮使用 **C++ 或 Go 寫一個 200KB 內的 "Launcher.exe"** 來替代 BAT 檔。EXE 能穩定處理 UTF-8 路徑與靜默啟動（Hide Console），這是提升 Windows 使用者體驗的最後一哩路。
    - **清理流程同步**: 所有加入 `voicetype_installer.iss` 的 `Excludes` 規則，必須手動同步更新到 `release_win.ps1` 的「白名單」中，保持兩版本一致性。

---
### 3. Windows 穩定性與展示功能大爆發 (V75 - V80)
- **維護日期**: 2026-03-14 02:45
- **版本標籤**: V80-STABLE-ULTRA-SHOWCASE
- **關鍵技術突破**:
    1. **CUDA DLL 硬核尋徑 (V77)**: 解決安裝版環境下 `cublas64_12.dll` 找不到的問題。實作了 `ctypes.WinDLL` 預加載機制，自動偵測 Frozen 路徑與系統路徑，確保 4070 等 GPU 能 100% 被啟動。
    2. **IPC 通訊協議加固 (V78)**: 修復「錄音成功但指示器噴紅燈」的邏輯矛盾。在 `SubprocessWhisperSTT.transcribe` 實作訊息計量與過濾循環，自動忽略中間的 `progress` / `status` 訊號，直到獲得結果，杜絕了訊號誤吞導致的超時。
    3. **LLM 引擎穩定性與參數同步**: 徹底修正 `openai_llm.py` 與 `ollama.py` 的建構式參數不一致，並加入執行緒安全的 `try-except` 守衛，確保 API 失敗時系統能平滑回退至原始 STT 文本，不影響 UI 運作。
    4. **VBUS 旗艦級展示模式 (V79/V80)**:
        - **情境模擬 Demo (is_demo)**: 實作 `ThreadPoolExecutor` 並行請求所有 `soul/scenario/` 下的靈魂，一次性輸出全靈魂對比。
        - **展示板與前綴**: 整合 `[STT]` 原文標籤與自定義靈魂標籤，並精確統計顯示處理時間（精確到 0.1s）。
    5. **ZIP 版「智慧啟動器」 (V80 Stable)**:
        - 實作了 `run_voicetype.bat` 自動偵測與 `create_shortcut.ps1` 聯動機制。
        - 啟動時自動於桌面建立帶有 `assets/icon.ico` 的旗艦級捷徑，讓 ZIP 綠色版使用者也能享有安裝版的開啟便利。
    5.- **桌面捷徑與編碼硬化 (V84)**：
    - 問題：Windows PowerShell (5.1) 處理含有中文字元的 UTF-8 (無 BOM) 腳本會解析失敗；CMD 處理含有中文字元的 BAT 亦有風險。
    - 對策：`create_shortcut.ps1` 改用 **Unicode 逃逸法** (`[char]0xXXXX`) 定義中文字串；`setup_win.bat` 脫敏為 **純 ASCII 註解與訊息**。
    - 結果：排除所有編碼干擾，達成「一鍵安裝即刻建立捷徑」的旗艦穩定性。
- **後續交接關鍵**:
    - **測試環境 vs 安裝環境**: V77 證明了安裝環境的 DLL 搜尋優先序與開發環境完全不同，未來任何 C++ 運行庫更新都必須先進行 `ctypes.WinDLL` 單體校驗。
    - **展示模式穩定度**: 全靈魂展示時若 LLM 數量極多，需注意 API Rate Limit 與網絡震盪。

---
*此記憶文件更新於 2026-03-14 02:45，符合新版 Global Rules 之雙層記憶規範。內容核核。*
