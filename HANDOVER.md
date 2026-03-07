# VoiceType4TW v2.8.27-Stable Handover Record

## 📌 當前狀態 (Current Context)
- **版本號**: v2.8.27-dev (BUILD-0306-P) - **[APP 穩定測試版]**
- **專案路徑**: `/Volumes/JDATA/playground/voicetype-mac`
- **關鍵成就**: 
  - 核心熱鍵系統徹底加固，解決物理按鍵對應失敗問題（一律記錄 `code:XX`）。
  - 非同步 LLM 狀態鎖定修復，解決潤飾模式被提早關閉的 Race Condition。
  - 內建 MLX Whisper 預熱與音效/幻覺過濾機制。

## ✅ 交接重要事項 (Handover Checklist)

### 1. 給新開發人員 (For Humans)
- **技術必讀**: 請務必先閱讀 **`AI_MEMORY.md`**。那裡有關於「硬體碼優先錄製」、「MLX Warmup」與「非同步時序修復」的所有細節。
- **打包指令**: 
  ```bash
  python3 setup.py py2app && ./pack_dmg.sh
  ```
  *(注：`pack_dmg.sh` 已內建 libmlx.dylib 修正腳本)*

### 2. 給下一個 AI Agent (For Agents)
- **讀取核心**: 啟動後請優先使用 `view_file` 讀取專案內的 `AI_MEMORY.md` 以取得所有已知的技術地雷與解法。
- **存取私密記憶 (Private Memory/Artifacts)**:
  - 若需接續目前的 `task.md` 任務進度，請確保讀取此路徑：
    `/Users/<USER>/.gemini/antigravity/brain/e5c8abbf-7d63-4e11-9d65-b8e8933129b1`
  - 如果更換電腦，請將整個 uuid 目錄複製至新環境的對應隱藏資料夾下。

## 🚀 未來展望
- **穩定性觀察**: 持續測試 v2.8.27 在不同重載情況下的 CPU/GPU 分配。
- **UI 優化**: 若有特定字型需求，請將其放入 `assets/fonts/` 並重新打包。

---
*本文件由上任 Agent (B10-B25) 於 2026-03-06 22:58 生成，標記 v2.8.27 為穩定里程碑。*
