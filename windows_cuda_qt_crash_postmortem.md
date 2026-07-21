# Postmortem: Windows CUDA (faster-whisper) 與 PyQt6 初始化崩潰衝突

## 錯誤現象與症狀
在將本專案（聲成文 VoxProse，前身 VoiceType4TW）從 macOS 移植到 Windows 的過程中，當應用程式執行到載入 `faster-whisper` (底層依賴 `CTranslate2` 和 CUDA) 時，Python 進程會**無任何例外或錯誤日誌**直接結束 (Exit Code 1)。

## 根本原因 (Root Cause)
經過大量的隔離測試與追蹤後證實，在 Windows 作業系統上，如果 Python 記憶體中**優先被載入了 PyQt6 相關的動態連結庫 (DLL)** (即使完全尚未宣告或實例化 `QApplication`)，再進行 CUDA 模組或 GPU 相關框架的初始化，就會引發毀滅性的底層視訊驅動 / OpenGL 記憶體衝突。

## 解決方案 (Resolution)
強制作業系統的載入順序：
1. **阻擋式防禦**：在 `main.py` 的絕對第一行 (環境變數設定之後)，**阻擋任何 PyQt6 UI 模組的 `import`**。
2. **預先載入 STT**：判斷若為 Windows 系統，立即在主執行緒中阻塞式地呼叫 `get_stt()` 完成 CUDA 模型的掛載與預熱。
3. **延後 UI 生成**：當模型已成功掛載進記憶體後，再匯入諸如 `ui.mic_indicator` 或 `ui.menu_bar` 等包含 PyQt6 依賴的模組。
4. 在 macOS 系統上則維持原樣設計，依然可以使用非阻塞的 `QThread` 背景載入，因為 CoreML 與 Qt 在 macOS 上並無此類衝突。

## 其他 Windows 特有地雷
- **字體渲染不一**：Windows 上 PyQt6 未必會預設套用美觀的黑體，需強制全域設定 `QApplication.instance().setFont(QFont("Microsoft JhengHei", 10))` 解決文字難看與大小不一。
- **無聲無息的 pynput 按鍵**：Windows 上的右 Alt 鍵 (Right Alt) 經常因為不同鍵盤語系而在 `pynput` 的 `key.char` 中註冊為 `alt_gr` 而非預設的 `alt_r`，需在事件傾聽器中手動強制映射。
- **ToolTip 無法置頂**：`Qt.WindowType.ToolTip` 在 Windows 未必像 macOS 般好用且置頂，作為浮動小視窗應改為合併使用 `Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint` 才能保證常駐頂層且不錯亂。

**—— 已將此知識條目化，未來 AI 開發者開發與移植 Windows 跨平台 PyQt 程式時應嚴格遵守此載入順序與防雷事項。**
