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

## 第一階段已完成（2026-07-21）

視窗標題／系統匣／桌面捷徑／About 視窗／Windows AppUserModelID／Release ZIP 與安裝檔命名／版本推進至 3.2.0／全 repo 文件品牌改寫。詳見 `CHANGELOG.md` [3.2.0]、`VERSIONS.md` [V3.2.0]、`docs/DECISIONS.md` 對應條目。

第一階段刻意不動：`%APPDATA%\VoiceType4TW`（`paths.py:APP_DATA_DIR`）與 `Documents\VoiceType4TW_Sync`（預設同步目錄）兩個實際路徑值——當時保留原樣是因為預設「已有真實使用者資料需要顧慮遷移」。

## 第二階段已完成（2026-07-21，同日稍後）——資料路徑正名，無遷移邏輯

維護者事後確認：本程式從未實際使用過，本機不存在任何 `%APPDATA%\VoiceType4TW` 或 `Documents\VoiceType4TW_Sync` 的真實資料。**第一階段規劃的「遷移邏輯六條原則」因此整批作廢，未實作、也不會實作**——沒有舊資料可遷移，寫這類邏輯只會是永遠不會執行到的死碼。改為直接把所有路徑常數與字面量改名，不留 old→new 的搬移/備份/fallback 程式碼。

- `paths.py`：`APP_DATA_DIR` → `%APPDATA%\VoxProse`；`get_sync_base_dir()` 預設值 → `Documents\VoxProse_Sync`。`whisper_models` 等子目錄透過 `get_data_dir()`/`APP_DATA_DIR` 常數跟著走，無需個別修改。
- `setup_win.bat`：`MODEL_DEST` 改為 `%APPDATA%\VoxProse\whisper_models`；console 標題/banner 改 VoxProse；編譯輸出改 `VoxProse.exe`。
- `release_win.ps1`：`$ModelSrc`/`$ModelDest` 改為 `%APPDATA%\VoxProse\...`；隨附啟動器改 `VoxProse.exe`；可攜版說明文字內路徑同步更新。
- `create_shortcut.ps1`：偵測的原生啟動器檔名改 `VoxProse.exe`。
- `tools/launcher.cs`：MessageBox 標題與頂部註解改 VoxProse（編譯出的 exe 檔名由 `setup_win.bat`/`release_win.ps1` 的 `/out:` 決定，見上）。
- `安裝下載教學.md`／`quality_control_checklist.md`：文件內列出的實際路徑字串已同步改為 `VoxProse`。
- 其餘散落的品牌字樣（`main.py`/`ui/app.py` 啟動 log、`self_check.py`/`tools/doctor.py`/`utils/diagnostics.py` 的診斷輸出等）一併掃到並改名，詳見 `docs/DECISIONS.md` 對應條目。

**刻意保留原名**：上游專案名／fork 來源／歷史沿革敘述（`NOTICE.md`、`README.md`／`README.en.md` 開頭 fork 出處、`pyproject.toml` 的 `description`、`main.py`/`tests/test_config.py` 內描述「這行程式碼過去長什麼樣子」的重構註解／docstring）——這些描述的是「當時實際存在過的字面值」，改寫會扭曲歷史事實，故不動。
