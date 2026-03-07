# 🚀 VoiceType4TW 環境遷移手冊 (給 cc58tw)

如果您剛拿到這台電腦並準備開始開發 `VoiceType4TW`，請按照以下步驟快速建立環境：

### 1. 基礎環境要求
- **macOS**: 建議 Ventura 13.0+ (需支援 Metal)。
- **Python**: 必須使用 **Python 3.12** (專案針對此版本加固)。
- **Xcode**: 安裝 Command Line Tools (`xcode-select --install`)。
- **Homebrew**: 安裝 `ffmpeg` (STT 必需)。

### 3. Clone 專案 (Git 流程)
由於您與父親共用 GitHub 帳號，您可以直接使用 **Private Repository**。
1. 在新電腦執行：
   ```bash
   git clone https://github.com/jfamily4tw/pirates-team
   ```
2. 將此目錄作為開發根目錄。

### 4. 複製 AI 記憶 (最重要 ⭐️)
如果您希望 AI 助手能記起之前所有的開發邏輯，請將舊電腦的以下目錄完整覆蓋到新電腦（這部分不會上傳 Git，需手動遷移）：
`~/.gemini/antigravity/brain/e5c8abbf-7d63-4e11-9d65-b8e8933129b1`

### 5. 安裝依賴
在專案根目錄執行：
```bash
pip3 install -r requirements.txt
# 或者根據 setup.py 安裝
python3 -m pip install -e .
```

### 6. 設定同步
專案支援將設定檔同步至特定雲端目錄（如 iCloud/NAS）。請檢查：
`~/Library/Application Support/VoiceType4TW/sync_path.txt`
確保路徑指向您的同步盤。

### 7. 首次執行測試
```bash
python3 main.py
```
啟動後，AI 會自動進行 1 秒的 **MLX Warmup**，這是正常的。

---
祝開發順利，cc58tw！如果有任何問題，直接在對話中呼叫我即可。
