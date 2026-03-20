# 🧠 VoiceType4TW macOS 開發記憶 (2026-03-19 v2.9.0 Mac純化版)

- [2026-03-19] **Mac v2.9.0 發布**：Mac 專屬純化版，移除所有 Windows 殘碼，加入 EDITION 版本開關，修復記憶體洩漏，新增模型下載進度條，MLX dylib 正確打包。
- [2026-03-14] **Mac v2.8.27 旗艦標竿版發布**：成功建立 `v2.8.27-mac-stable` 標籤，同步 GitHub Release，並更新團隊成員 **CC58TW**。

## 🗄 重要路徑
| 路徑類型 | 路徑 |
|------|-------------------------------------------------------|
| App 資料 | `~/Library/Application Support/VoiceType4TW/` |
| debug log | `~/Library/Application Support/VoiceType4TW/debug.log` |
| sync_path.txt | `~/Library/Application Support/VoiceType4TW/sync_path.txt` |
| 打包輸出 | `/Volumes/JDATA/playground/voicetype-mac/dist/` |

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
*此記憶文件由 AI 於 2026-03-19 更新，標記 v2.9.0 Mac 純化版里程碑。*
