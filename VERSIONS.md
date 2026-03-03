# VoiceType4TW 開發開發版本全紀錄 (面向物件分析)

本檔案用於精確紀錄「使用者需求」與「實際變更」的對照，並連結至 Git 提交與備份紀錄。

---

## [v2.7.32 beta] - 正在進行中的旗艦版升級
**狀態**: 規劃中 (In Progress)

## [v2.7.32 beta] - 2024-03-01 (Windows Stability Update)

### 核心變動與穩定性 (Core Stability)
- **啟動防護**：於 `main.py` 最頂端強制設定 `KMP_DUPLICATE_LIB_OK=TRUE` 以及 PIL 預先初始化，徹底解決 Windows 下的 OpenMP 衝突與 Pystray/Pillow 死鎖。
- **導入優化**：將 `SettingsWindow` 等大型 UI 元件改為延遲導入 (Lazy Import)，避免模組相互依賴造成的開機 Exit Code 1。
- **重啟提醒**：儲存設定後不再自動連鎖觸發，改為彈窗提醒使用者手動重啟，確保環境變數完整生效。

### 性格與 AI 邏輯 (Soul & AI Logic)
- **靈魂層次化**：將 `base.md` 合併至 `default.md` 作為所有輸出的底層。`Personality` 選項現在是疊加於底座之上的「性格修飾器」。
- **語言微調系統**：保持原稱「翻譯功能」，實作「性格 + 語言」雙層疊加（例如：性格為社群貼文 + 翻譯為日文）。
- **強化日誌系統 (Enhanced Logging)**：
  - 日誌改為「累加模式 (Append)」，並在每次啟動時加入時間分隔線。
  - 背景音訊處理執行緒加入完整 `Traceback` 捕獲，確保錯誤不遺漏。
  - 在「系統設定」加入 **「📄 檢視詳細日誌」** 按鈕，方便一鍵排錯。
- **修復 ImportError**：補齊 `hotkey/listener.py` 中遺漏的 `get_active_window_title` 函式。

---

## v2.7.32 Build-0303-B2 (旗艦加強版)
### 改進清單 (Requested by User)
- **多情境 Demo 模式 (Scenario Demo Loop)**：
  - 當開啟 Demo 模式時，系統會自動遍歷 `soul/scenario/` 下的所有 `.md` 檔案。
  - 輸出格式統一為：`[STT] 結果`、`[LLM模式1] (性格A) 結果`、`[LLM模式2] (性格B) 結果`...
- **Showcase 模式修正**：確保格式始終為 `[STT] 結果\n\n[LLM模式] 結果`。
- **絕對防護：瀏覽器開窗阻斷**：
  - 在 Demo 模式下全面跳過 `ActionDispatcher` 指令偵測，防止語音誤觸搜尋或網頁指令。
  - 徹底排除 `webbrowser.open` 調用。
- **版號精細管控 (Build Numbering)**：
  - 引入內部 `BUILD_ID` (B2)，顯示於側邊欄下方，確保每次修改後之版本可追蹤。
  - 此版本記錄由 Gemini 協助自動同步維護。

---

## v2.7.32 Build-0303-B3 (旗艦完善版)
### 改進清單 (Requested by User)
- **靈魂選單優化**：在「靈魂情境」選單中還原「預設 (基底靈魂)」選項，滿足使用者對純淨輸出的選取需求。
- **翻譯狀態同步**：
  - 修復「快速翻譯」選單在切換語言後未更新勾選狀態 (Checked) 的問題。
  - 確保切換至特定語言時，選單會自動同步當前狀態。
- **浮動視窗 UI 強化**：
  - 為浮動視窗的 `QMenu` 導入自定義勾選圖示 (`assets/check.png`)，解決勾選狀態不可見的問題。
  - 統一選單視覺風格，提升操作回饋感。
- **版本遞增**：Build 更新至 **B3**，版本日誌同步記錄。

---

## v2.7.32 Build-0303-B4 (旗艦最終校準版)
### 改進清單 (Requested by User)
- **UI 深度對齊**：
  - 修正「系統設定 (General)」頁面中的 **「⚙️ 偏好設定」** 標題重複問題。
  - 將「情境模擬 Demo」、「顯示模式名稱前綴」、「LLM 展示版」等控制項統一整合至「系統設定」頁面，並與使用者截圖完美一致。
- **全情境遍歷 Demo**：
  - 加強 Demo 模式，現在會額外輸出 **「預設/基底」** 靈魂的結果，確保全方位的性格測試。
- **文字輸出標籤 (Output Prefix)**：
  - 新增「顯示模式名稱前綴」支援。開啟後，一般 LLM 輸出會自動加上 `[LLM模式]` 標籤。
- **Showcase 模式優化**：
  - 確保 Showcase 彈窗與格式輸出在 B4 版中穩定可用，並修正顯示權限 logic。
- **穩定性更新**：Build 編號正式躍升至 **B4**。

---

## v2.7.32 Build-0303-B5 (旗艦格式精準版)
### 改進清單 (Requested by User)
- **Demo 模式格式精確對齊**：
  - 更新標籤格式，將原始的 `[LLM模式n] (預設/基底)` 修正為更簡潔的 **`[底層靈魂]`**。
  - 其他情境標籤統一為 **`[情境名稱]`** (如 `[商務回應]`)，並確保內容與標籤在同一行起始。
- **Showcase 模式名稱校準**：
  - 將 LLM 輸出的對照標籤從 `[LLM模式]` 修正為 **`[LLM]`**，完全符合使用者提供的對比範例。
- **標點符號風格鎖定**：
  - 確保所有輸出結果維持全形標點符號的統一性。
- **版本遞增**：Build 更新至 **B5**。

---

## v2.7.32 Build-0303-B6 (旗艦緊急修復版)
### 改進清單 (Requested by User)
- **緊急修復 (Hotfix)**：
  - 修正 `main.py` 在 Demo 模式結束時因 `original_scenario` 變數未定義導致的 `NameError` 崩潰問題。
  - 確保 Demo 遍歷後能正確恢復原本選定的情境。
- **UI 文字同步**：
  - 配合使用者對 `settings_window.py` 的手動微調，確保「需 API KEY 連結雲端 LLM」等警語在 B6 版中獲得完整支持。
- **穩定性更新**：Build 編號正式升級至 **B6**。

---

## v2.7.32 Build-0303-B7 (旗艦智慧對齊版)
### 改進清單 (Requested by User)
- **Prompt 結構深度優化**：
  - 重構 `_build_llm_prompt` 邏輯：將「指令規範」與「靈魂設定」置於最前，**「輸入草稿」置於最後**。
  - 此調整能顯著防止 LLM 在面對簡短輸入時，錯誤地輸出其性格設定或指令內容（Prompt Leakage/Mimicry）。
  - 在 Prompt 中顯式加入「嚴禁自我介紹或解釋」的強制指令。
3. **系統標籤一致性**：配合使用者最新偏好，所有 Demo 與 Showcase 的標籤括號維持使用半形 **`[]`** (例如 `[STT]`、`[LLM]`、`[底層靈魂]`)。
4. **顯示模式名稱前綴 (B11)**：當開啟 `output_prefix` 時，前綴應為動態的 **`[當前情境名稱]`** (如 `[商務回應]` 或 `[底層靈魂]`)，而非固定的 `[LLM模式]`。
5. **獨立熱鍵日誌 (B12)**：為了日誌純淨，熱鍵事件應透過專屬 Logger `voicetype.hotkey` 導向 `keystrike.log`。
6. **標點符號風格**：在最終替換邏輯中，使用者偏好保留半形的 **`., (), [], {}`**，而非全形版本。

再次警告：你的唯一任務是「根據角色設定，輸出標籤內潤飾後的內容」。嚴禁加上前言或結語。
- **穩定性更新**：Build 編號正式升級至 **B7**。

---

## v2.7.32 Build-0303-B8 (旗艦防護強化版)
### 改進清單 (Requested by User)
- **Prompt 防護 (Prompt Injection Protection) 強化**：
  - 引進 **`<Draft>` XML 標籤封裝**。現在所有的語音輸入都會被包在該標籤中，讓 LLM 絕對區分「指令」與「草稿」。
  - 在輸出邏輯中加入了二次防護警告，嚴禁 LLM 輸出關於自身設定的內容，徹底解決簡短輸入（如「好的」）導致的提示詞洩漏。
- **永久記憶系統 (Non-Git Memory)**：
  - 在 `paths.py` 中定義了 **`AI_PERMANENT_MEMORY_PATH`**，指向 `%APPDATA%/VoiceType4TW/ai_permanent_memory.md`。
  - 此檔案存儲於使用者電腦，**不受 Git 回滾影響**，用於保存 AI 在開發過程中學到的核心規則與教訓。
- **穩定性更新**：Build 編號升級至 **B8**。

---

## v2.7.32 Build-0303-B9 (旗艦記憶同步版)
### 改進清單 (Requested by User)
- **跨平台開發記憶同步 (Cross-Platform Sync)**：
  - 更新 Repo 根目錄下的 **`AI_MEMORY.md`**，將 B7-B8 的所有「旗艦版鐵律」（標籤封裝法、全形標籤、結構優先權）正式寫入專案大腦。
  - 建立 **「雙層記憶架構」**：開發經驗隨 Git 同步（Mac/Win 通用），同時在各機 AppData 保留不回滾的 `ai_permanent_memory.md`。
  - 此舉確保 AI 助手在任何平台啟動時，都能透過「知識發現 (Knowledge Discovery)」主動繼承所有已知的避坑經驗。
- **穩定性更新**：Build 編號正式升級至 **B9**。

---

## v2.7.32 Build-0303-B10 (旗艦啟動優化版)
### 改進清單 (Requested by User)
- **啟動日誌強化**：
  - 在 Python 啟動畫面與 `debug.log` 的 `[START]` 紀錄中，正式加入 **Build Number** 顯示 (例如 `v2.7.32 beta (BUILD-0303-B10)`)。
  - 將 `BUILD_ID` 常數移至 `paths.py` 以達成 `main` 與 `UI` 模組間的清潔調用。
- **格式偏好校準 (Style Calibration)**：
  - 根據使用者手動微調，將所有系統標籤括號回退為半形 **`[]`**。
  - 調整最終標點替換邏輯，保留半形的 `., (), [], {}` 以符合使用者習慣。
- **穩定性更新**：Build 編號正式升級至 **B10**。

---

## v2.7.32 Build-0303-B11 (旗艦前綴動態版)
### 改進清單 (Requested by User)
- **動態模式名稱前綴 (Dynamic Mode Prefix)**：
  - 更新「顯示模式名稱前綴」功能。現在輸出的前綴會根據當前選定的情境動態變化，例如：**`[商務回應]`**、**`[情商大師]`** 或 **`[底層靈魂]`**。
  - 此改進取代了原先固定的 `[LLM模式]` 標籤，提供更高的辨識度與個人化體驗。
- **穩定性更新**：Build 編號正式升級至 **B11**。

---

## v2.7.32 Build-0303-B12 (旗艦偵錯強化版)
### 改進清單 (Requested by User)
- **獨立熱鍵日誌系統 (Separate KeyStrike Logging)**：
  - 為了防止 `debug.log` 體積爆炸並提升可讀性，現已支援將所有 KeyStrike- [x] v2.7.32 b12: 實作獨立熱鍵日誌系統 (Separate KeyStrike Log)
    - [x] 在 `settings_window.py` 增加「獨立記錄熱鍵」選項
    - [x] 修改 `hotkey/listener.py` 改用 `logging`
    - [x] 在 `main.py` 實作日誌自動分流 (Route to `keystrike.log`)
- [x] v2.7.32 b11: 動態模式名稱前綴 (取代固定 `[LLM模式]`)
頁面新增「檢視熱鍵紀錄」按鈕，方便一鍵開啟 `keystrike.log`。
- **穩定性更新**：Build 編號正式升級至 **B12**。

---

## v2.7.32 Build-0303-B13 (啟動穩定熱修復版)
### 改進清單 (Requested by User)
- **啟動修復 (Hotfix)**：
  - 修正了 B12 版本中 `SettingsWindow` 的 `AttributeError`。該錯誤是因為按鈕綁定了已更名的日誌方法 `_view_logs` (已更正為 `_view_debug_log`)，導致啟動時可能產生崩潰。
  - **同步 KeyStrike 配置**：統一了 UI 改動後的 `showcase_mode` 鍵值，確保設定能正確儲存並生效於主程式。
- **穩定性更新**：Build 編號正式升級至 **B13**。

---

## v2.7.32 Build-0303-B14 (日誌淨化版)
### 改進清單 (Requested by User)
- **日誌層級動態控制**：
  - 修正了終端機在關閉「詳細日誌 (Debug Logging)」後仍持續輸出熱鍵事件的問題。
  - 現在全域日誌預設為 `INFO` 層級，僅在手動勾選「詳細日誌」時才會切換至 `DEBUG`。
- **穩定性更新**：Build 編號正式升級至 **B14**。

---

## v2.7.32 Build-0303-B15 (托盤同步穩定版)
### 改進清單 (Requested by User)
- **托盤選單修復 (Tray Synchronization)**：
  - 修正了在 Windows 下儲存設定後，托盤選單更新失敗並顯示 `Failed to update Windows tray menu` 的問題。
  - **技術優化**：重構 `tray_manager.py`，確保所有 `pystray` 選單項目的 Callback 與 勾選狀態 (Checked) 均採用標準函數封裝，避免因異步狀態變更導致的內部異常。
- **穩定性更新**：Build 編號正式升級至 **B15**。

---

## v2.7.32 Build-0303-B16 (極簡托盤版)
### 改進清單 (Requested by User)
- **選單功能分流 (Menu Separation)**：
  - **簡化托盤選單**：為提升操作效率，系統托盤 (Tray) 選單現在僅保留「關於」、「偏好設定」與「結束」。
  - **完整浮動選單**：所有核心功能（AI 開關、靈魂情境選擇、快速翻譯）完整保留於「浮動按鈕」中，實現 UI 職責分離，減少托盤負擔。
- **穩定性更新**：Build 編號正式升級至 **B16**。

### UI/UX 改進
- **純淨介面**：隱藏「輸出格式」標籤與選單，移除靈魂名稱的 Emoji 前綴，維持視覺簡潔。
- **自動詞彙學習**：修正 Windows 下 `vocab.manager` 的加載與學習邏輯，語音內容出現 3 次以上將自動記入 AI 學習清單。
- **長期記憶存儲**：修正 `memory.manager` 確保長期對話記錄能在 Windows 下正確追加。

### 備份與維護 (Backup)
- **獨立分支**：本版本完全開發於 Windows 修復分支，不影響 Mac 穩定版 (v2.6.0)。
- **備份準備**：已執行 `soul/scenario` 目錄清理與精簡。
    - **本地實體記憶**: 紀錄對話內容 (Memory) 並自動學習常用詞彙 (Vocab >3次)。
5. **Debug 工具**: 
    - **Showcase 模式**: [STT] + [LLM] 分行展示（雙換行）。
    - **Demo 模式**: 無視 AI 開關，遍歷並顯示所有模型結果。

- [ ] 升級版本號至 v2.7.32 beta。
- [ ] 實施啟動穩定性修復腳本 (OpenMP, ImageInit, LazyImport)。
- [ ] 更名 UI 術語並移除 Emoji。
- [ ] 實作性格疊加提示詞邏輯。
- [ ] 實作瀏覽器視窗偵測與注入跳過。

### 📦 版本備份
- **Git Tag**: (等候完成後標記)
- **Archive**: (等候完成後建立 zip)

---

## [v2.7.24] - PC 可運作版本 (穩定基準)
**狀態**: 已封存 (Stable Base)

### 🗣️ 使用者需求紀錄
- 建立一個能在 Windows 穩定執行的版本。
- 支援 Inno Setup 安裝程式。

### 🛠️ 實際變更清單
- 回滾大規模跨平台重構至 v2.7.24。
- 完成 Inno Setup 安裝腳本配置。

### 📦 版本備份
- **Git Tag**: `v2.7.24-pc-stable` (2026-03-03)
- **Archive**: `VoiceType4TW_v2.7.24_PC_Stable.zip`
