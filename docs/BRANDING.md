# Branding

品牌規格與資料目錄遷移規劃。與 [`DECISIONS.md`](DECISIONS.md)（為什麼）、[`DEVELOPMENT.md`](DEVELOPMENT.md)（怎麼做）互補：這裡放品牌本身的定案內容與尚未實作的遷移計畫。

## 品牌規格（2026-07-21 定案）

- 中文品牌：**聲成文**｜英文品牌：**VoxProse**｜建議組合：**聲成文 VoxProse**
- 完整名稱：**聲成文｜本地優先 AI 語音輸入工具**
- 英文副標：**Local-first AI Voice Typing for Traditional Chinese**
- 英文標語：**Speak naturally. Write clearly.**｜中文標語：**自然開口，清楚成文。**
- 品牌呈現範例（About／README 頭部等）：

```
聲成文
本地優先 AI 語音輸入工具

Based on VoiceType4TW
Windows fork maintained by SanHsien
```

## 署名鏈（NOTICE／README／About／AGENTS.md 等處都需完整呈現）

1. **原創作者**：吉米丘（Jimmy）、CC58TW
2. **上游 Windows 專用版維護**：**go-mask**（`win-go-mask-202607` 分支）
3. **本 fork（Windows）維護**：SanHsien

## 第一階段已完成（本次任務，2026-07-21）

視窗標題／系統匣／桌面捷徑／About 視窗／Windows AppUserModelID／Release ZIP 與安裝檔命名／版本推進至 3.2.0／全 repo 文件品牌改寫。詳見 `CHANGELOG.md` [3.2.0]、`VERSIONS.md` [V3.2.0]、`docs/DECISIONS.md` 對應條目。

**第一階段刻意不動**：`%APPDATA%\VoiceType4TW`（`paths.py:APP_DATA_DIR`）與 `Documents\VoiceType4TW_Sync`（預設同步目錄）兩個實際路徑值。理由：這些路徑被設定、同步指標、模型、日誌、詞彙、統計多處直接使用，貿然改名會造成設定與日誌分裂。

## 第二階段遷移計畫（僅規劃，尚未實作——等品牌穩定後再實作）

目標：`%APPDATA%\VoiceType4TW` → `%APPDATA%\VoxProse`（`Documents\VoiceType4TW_Sync` 同理遷往 `Documents\VoxProse_Sync`）。

遷移邏輯六條原則（維護者拍板，原文照收）：

1. 新路徑不存在、舊路徑存在時才遷移。
2. 遷移前建立時間戳備份。
3. 先複製，不直接刪除舊資料。
4. 驗證 JSON、模型與詞彙資料後切換。
5. 至少保留一個版本的舊路徑 fallback。
6. 遷移失敗時繼續使用舊路徑。

實作時需要涵蓋的既有接觸點（現況盤點，供實作時參考，非本次已完成項目）：

- `paths.py`：`APP_DATA_DIR`、`SYNC_BASE_DIR`（`get_sync_base_dir()` 的預設值）、`initialize_paths()`、`_install_bundled_models()`。
- `main.py`：目前已改為引用 `paths.APP_DATA_DIR`（本次重構，見 `docs/DECISIONS.md`），第二階段遷移邏輯應同樣集中在 `paths.py`，不要再度散落到 `main.py`。
- `setup_win.bat`：`MODEL_DEST` 變數硬編 `%APPDATA%\VoiceType4TW\whisper_models`。
- `release_win.ps1`：`$ModelSrc`/`$ModelDest` 同樣硬編 `%APPDATA%\VoiceType4TW\...`（打包時讀取本機已下載模型快取）。
- `安裝下載教學.md`／`quality_control_checklist.md`：文件內列出的實際路徑字串（遷移完成後需要同步改寫，本次品牌改名任務刻意保留原樣）。

**等品牌穩定後再實作**——本次任務範圍僅止於本文件的規劃記錄。
