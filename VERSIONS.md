# VoiceType4TW 開發版本全紀錄 (面向物件分析)

本檔案用於精確紀錄「使用者需求」與「實際變更」的對照，並連結至 Git 提交與備份紀錄。最新版本置頂。

---

## [v2.8.2] - 2026-03-04 19:00 (Stable Release)
### 全功能同步與對齊 (Full Parity)
- **旗艦功能對齊**：同步 Mac 版的高精度「處理耗時顯示」與「執行日誌系統」。
- **API Key 預檢機制**：增加強健性檢查，若 API Key 未填將在 MicIndicator 顯示紅色警告，防止測試閃退。
- **雙層設定架構 (Double-Layer Config)**：
  - `config_local.json`：存放熱鍵、硬體特定設定（不參與同步）。
  - `config_global.json`：存放 API Keys、Prompt（參與同步）。
- **NAS 指標同步**：實作 `sync_path.txt` 目錄重定向，支援 NAS 私密靈魂同步。
- **穩定性修補**：移除 PC 版過時的 `CONFIG_PATH` 依賴。

---

## [v2.8.1-dev] - 2026-03-04 11:15 (Cloud Sync Handover)
### 🚀 跨平台同步開發
- **核心實作**：
  - `paths.py`：實作 `get_sync_base_dir()` 透過指標重定向資料目錄。
  - `config.py`：實作 `LOCAL_KEYS` 白名單，正式拆分 Local 與 Global 設定。
- **UI 強化**：新增 [☁️ 雲端同步] 專屬分頁，支援遷移與連結 NAS 目錄。

---

## [v2.8.0] - 2026-03-03 18:30 (Official PC Release B19)
### 核心穩定性與瀏覽器解禁
- **瀏覽器輸入修復 (B19)**：徹底移除針對瀏覽器的注入攔截，實現全網頁通用輸入。
- **極簡托盤選單 (B16)**：將模式與情境選擇移至浮動按鈕，托盤僅保留基礎設定。
- **浮動按鈕切換 (B18)**：支援使用者自定義開啟/關閉浮動按鈕 UI。
- **啟動防護與穩定性**：解決了 Windows 下的 OpenMP 衝突與 Pystray 死鎖，Build 躍升至 B19。

---

## [v2.7.32 B15] - 2026-03-03 15:00 (Tray Sync Fix)
- **托盤選單修復**：解決 Windows 下儲存設定後圖示選單更新失敗的问题。

---

## [v2.7.32 B14] - 2026-03-03 14:20 (Log Cleanup)
- **日誌淨化**：改進層級控制，關閉 Debug 時不再輸出大量熱鍵日誌。

---

## [v2.7.32 B8-B13] - 2026-03-03 (Security & UX Polish)
- **B13 (Hotfix)**：修正 SettingsWindow 崩潰。
- **B12 (Separate Log)**：實作 `keystrike.log` 職責分離。
- **B11 (Dynamic Prefix)**：前綴改為動態的情境名稱。
- **B10 (Build ID System)**：引入 `paths.py` 硬編碼 Build ID 追蹤。
- **B8-B9 (Memory Sync)**：引入 `<Draft>` XML 標籤保護與 `AI_MEMORY.md` 雙層架構。

---

## [v2.7.32 B7] - 2026-03-03 10:00 (Prompt Alignment)
- **Prompt 結構優化**：規則前置、資料後置。強制半形括號 `[]` 與標點符號風格鎖定。

---

## [v2.7.32 B2-B6] - 2026-03-03 09:00 (Flagship Features)
- **B6 (NameError Fix)**：修復 Demo 模式變數遺漏。
- **B5 (Format Fix)**：校準 `[底層靈魂]` 標籤格式。
- **B4 (UI Alignment)**：整合 Demo 控制項至系統設定頁。
- **B2-B3 (Scenario Loop)**：實作遍歷所有性格的測試模式並優化選單勾選。

---

## [v2.7.32 beta] - 2026-03-02 22:00 (Windows Porting Start)
- **啟動加強**：強制 `KMP_DUPLICATE_LIB_OK=TRUE`。
- **導入優化**：採用延遲導入 (Lazy Import) 避免重複依賴。
- **路徑重組**：將資料路徑導向 `%APPDATA%/VoiceType4TW`。

---

## [v2.7.24-pc-stable] - 2026-03-01 18:00 (Stable Base)
- **Windows 初心版**：建立能在 PC 穩定執行的環境基準，包含 Inno Setup 安裝配置。
