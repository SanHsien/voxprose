# VoiceType4TW 內部開發私密清單 (Internal Private Roadmap)

> [!IMPORTANT]
> 此檔案已加入 `.gitignore`，**不會**被 Push 到 GitHub。這是我們（AI 與吉米大）之間的私密筆記空間。

## 🎯 已完成進度 (Recently Completed on PC)

### 1. UI 職責分流 (Tray vs Floating Menu)
- **現狀**：托盤選單僅保留「設定/關於/結束」，核心 AI 控制項（性格、翻譯、連鎖模式）已完整遷移至「浮動圖示選單」中，大幅提升 Windows 下的操作流暢度。

### 2. Prompt 防護與結構優化
- **XML 標籤封裝**：導入 `<Draft>` 標籤，徹底解決簡短輸入（如「好的」）導致的提示詞洩漏問題。
- **結構調整**：將人格設定置於最頂部，輸入內容置於最末，極大化 LLM 的追隨指令能力。

### 3. 瀏覽器注入解禁 (v2.8.0)
- **突破**：移除了先前版本中對瀏覽器視窗的注入限制，現在可在 Chrome/Edge 等環境直接用語音打字。

## 🚀 待實作功能 (Roadmap)

### 1. Trigger Mode (全時自動觸發模式)
- **進度**：[ ] 開發中
- **目標**：實現「嘿 VoiceType」喚醒後的自動錄音切換，或是按一下切換開關，而非長時間按住。

### 2. 多螢幕位置記憶 (Positional Memory)
- **目標**：讓 Indicator 不只是「跟隨滑鼠」，還能記錄使用者在不同螢幕上的「偏好停靠位置」。

### 3. 記憶體占用優化 (Memory Usage Optimization)
- **現狀**：[2026-03-15] 發現占用達 6.59 GB。
- **原因**：使用者啟用了 `whisper-large-v3-mlx` 模型。
- **計划**：先觀察幾天。若持續困擾，考慮強制優化 `main.py` 的模型釋放邏輯，或建議切換回 `medium`。

---
*上次更新日期：2026-03-03 (Synchronized from PC session)*
