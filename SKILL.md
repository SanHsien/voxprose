---
name: voxprose
description: 維護 SanHsien/voxprose（聲成文 VoxProse，前身 嘴炮輸入法 VoiceType4TW）。本機優先的 Windows 語音輸入法：全域熱鍵錄音（純 ctypes 輪詢，無 pynput）、faster-whisper 本地辨識（Windows 上走獨立子行程避免 PyQt6/CUDA 衝突）或雲端引擎（Groq/Gemini/OpenRouter）、可選 LLM 潤飾（7 種供應商）、三層靈魂系統與詞彙記憶。Fork 自 jfamily4tw/voicetype4tw-mac 的 win-stable 分支（原作者吉米丘、CC58TW；上游 Windows 專用版維護 go-mask），上游採 MIT 授權，本 fork 只做 Windows 10/11 版本。
---

# 聲成文 VoxProse

## 何時使用

使用者要維護 `SanHsien/voxprose`，或開發聲成文 VoxProse（前身嘴炮輸入法 VoiceType4TW）功能：

- 修 bug、調整 STT（`stt/`）或 LLM（`llm/`）引擎、熱鍵（`hotkey/`）、UI（`ui/`）。
- 調整三層靈魂系統（`soul/`）、詞彙記憶（`vocab/`）、長期記憶（`memory/`）、統計（`stats/`）。
- Windows 環境的相容性除錯與手動驗證（本 fork 唯一開發/執行環境）。
- 讀 `config.py` / `paths.py` 了解設定與資料路徑，或擴充 `config.py` 的 `DEFAULT_CONFIG`。
- 跑或擴充 `tests/` 下的 pytest 自動化測試。

## 不適用

- 未查證前，在文件或回覆中宣稱上游程式碼有 MIT / Apache / GPL 等正式開源授權——見 [`NOTICE.md`](NOTICE.md) 與根目錄 `LICENSE` 的雙軌說明。
- 未經任務明確要求，修改打包鏈（`setup_win.bat`、`build_win.py`、`release_win.ps1`、`voicetype_installer.iss`、`tools/get_portable_python.ps1`、`tools/launcher.cs`）。
- 假設或新增 macOS 專屬程式碼（`AppKit`/`Quartz`/`py2app`/`pyobjc-*`/`mlx`）——目前工作樹已是 Windows-only，這些依賴與分支不存在。
- 提交 API key、`config_local.json`、`config_global.json`、`sync_path.txt`、`soul.md`、`memory/*.json`、`vocab/*.json`、`audio/*.wav`、`output/*.txt`、`bundled_models/` 等私密/本機/大型資料。

## 怎麼跑

```powershell
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements-win.txt
pip install -r requirements-cuda-win.txt   # 只有 NVIDIA GPU 才需要
python main.py
```

或一般使用者走 `setup_win.bat`（自動建置環境）＋ `run_voicetype.bat` / 桌面捷徑。

## 怎麼驗

```powershell
python -m pytest tests/ -v      # 自動化：tests/test_smoke.py（py_compile 全庫 + 純邏輯模組匯入）、tests/test_config.py（設定載入/儲存）
python self_check.py            # 手動：STT 子行程實際辨識煙煙測試（需已下載模型）
python tests\manual\manual_qkey_check.py   # 手動：需可顯示視窗環境，驗證 nativeVirtualKey
```

沒有 pytest 就 `pip install pytest`（或 `pip install -e ".[dev]"`，`pyproject.toml` 已定義 `dev` extra）。詳見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)「測試」一節。

## 快速定位

- `README.md` / `README.en.md`：使用者入口、功能介紹。
- `AGENTS.md` / `CLAUDE.md`：AI 接手規則（本檔規則以 `AGENTS.md` 為準）。
- `NOTICE.md`：fork 來源與授權查證結果。
- `CHANGELOG.md` / `VERSIONS.md`：精簡對外變更摘要 / 逐版詳細全紀錄。
- `main.py` → `ui/app.py`：進入點與 `VoiceTypeApp(QObject)` 協調者。
- `config.py` / `paths.py`：設定載入儲存、資料目錄與路徑解析（`%APPDATA%\VoiceType4TW\`）。
- `stt/`、`llm/`、`ui/`、`hotkey/`、`actions/`、`soul/`、`vocab/`、`memory/`、`audio/`、`output/`、`stats/`、`utils/`、`tools/`：功能模組，職責見 `AGENTS.md` 架構速覽表。
- `tests/`：pytest 自動化測試；`tests/manual/`：需視窗環境的手動腳本。
- `pyproject.toml`：套件 metadata 與 pytest 設定（不取代 `requirements-win.txt`）。
- `docs/DEVELOPMENT.md`：環境需求、Windows 啟動、測試、目錄結構。
- `docs/DECISIONS.md`：決策紀錄。
- `windows_cuda_qt_crash_postmortem.md`：Windows 上 PyQt6/CUDA 載入順序衝突的已知地雷與修法。
- `self_check.py` / `diagnose_mic.py`：手動診斷腳本（後者已重寫為 Windows 版：列輸入裝置、測預設裝置實際音量）。

## 完成回報

回報時列出：

- 修改了哪些檔案。
- 是否改到 STT/LLM 引擎介面、`config.py` 的 `DEFAULT_CONFIG`/`LOCAL_KEYS`、熱鍵對應表，或 `main.py`/`stt/__init__.py` 的 Windows 載入順序。
- 執行過哪些驗證：`python -m pytest tests/ -v` 的結果、有無在 Windows 實機啟動 `python main.py` 手動測試。
- 是否碰到 `windows_cuda_qt_crash_postmortem.md` 記錄的已知地雷，或動到打包鏈（`setup_win.bat`/`build_win.py`/`release_win.ps1`/`voicetype_installer.iss`）。
