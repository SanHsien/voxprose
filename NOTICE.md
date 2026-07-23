# NOTICE

聲成文 VoxProse（voxprose，前身 嘴炮輸入法 VoiceType4TW，SanHsien fork）

本專案 fork 自 [`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac)。

原始作品：

- Project: `voicetype4tw-mac`（嘴炮輸入法 / VoiceType4TW）
- 原創作者：吉米丘（Jimmy）、CC58TW（見上游與本 repo `README.md`）
- 上游 Windows 專用版維護：**go-mask**（`win-go-mask-202607` 分支；該分支 README 明載「Windows 專用版維護：go-mask ｜ 協助開發：Claude Code」）
- 協助開發者（README 列名）：Codex、Claude、Gemini、Nebula

## 授權狀態

**上游已於 2026-07-20 正式採 MIT 授權**（`jfamily4tw/voicetype4tw-mac` main 分支 commit `46346d3`：「docs: add MIT license and contribution guide」）。本 fork 隨即同步：整體以 **MIT License** 授權，見根目錄 `LICENSE`——上游授權全文（含 Jimmy Chiou / CC58TW / VoiceType4TW contributors 版權行）之外，另加一段本 fork 新增部分 © 2026 SanHsien、同樣採 MIT 條款的聲明。

以下保留先前（上游補齊授權前）的雙軌授權查證過程作為背景記錄：

- 查證方式：`git -C <repo> ls-files | grep -i licen`（本 fork 工作目錄當時沒有 `LICENSE` 檔）、`gh api repos/jfamily4tw/voicetype4tw-mac/license` → `404 Not Found`、`gh repo view jfamily4tw/voicetype4tw-mac --json licenseInfo` → `licenseInfo: null`。
- 上游當時 `README.md` 僅有口語聲明（「GitHub開源的Python版，想自己抓下來研究、裝在電腦裡都OK」「原始碼全部開源，想玩的自己去下載安裝，完全免費，但無法提供技術支援」），不具備 MIT / Apache-2.0 / GPL 等具法律定義的授權文字。
- 因此 2026-07-19 曾採雙軌授權聲明：上游程式碼不宣稱開源授權（著作權屬吉米丘 / CC58TW，僅依口語善意做個人研究改良）、本 fork 新增部分單獨採 MIT。此雙軌安排已隨上游正式補齊授權（見上方）收斂為全 MIT，不再適用。
- 決策沿革詳見 `docs/DECISIONS.md`。

## Project Scope

`聲成文 VoxProse`（voxprose）是本機優先的語音輸入法：使用者按住或切換全域快捷鍵錄音，透過本地 Whisper（`faster-whisper` / Apple Silicon 上的 `mlx-whisper`）或選用的雲端引擎（Groq、Gemini、OpenRouter）辨識語音，可選經 LLM（Ollama / OpenAI / Anthropic / Gemini / OpenRouter / Qwen / DeepSeek / Minimax）依「三層式靈魂系統」潤飾語氣，再自動貼回目前有輸入焦點的應用程式。原生支援 macOS（Universal）與 Windows 10/11；本 fork 的維護環境為 Windows 11 原生。

## Credits and Acknowledgments

- **Fork 來源**：[`jfamily4tw/voicetype4tw-mac`](https://github.com/jfamily4tw/voicetype4tw-mac) — 原創作者吉米丘、CC58TW。本 fork 保留其作者署名與原產品命名（嘴炮輸入法 / VoiceType4TW）作為歷史沿革記錄；現行品牌為「聲成文 VoxProse」。
- **上游 Windows 專用版維護**：go-mask（`win-go-mask-202607` 分支）。
- **本 fork（Windows）維護**：SanHsien，修改、文件與 Windows 端調整由其維護，另有註明者除外。
- **上游列名的 AI 協助開發者**：Codex、Claude、Gemini、Nebula（沿用上游 README 記載，非本 fork 新增聲明）。
- **語音辨識**：[Faster Whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2 實作）、[MLX Whisper](https://github.com/ml-explore/mlx-examples)（Apple Silicon 加速）——僅作為執行期相依套件使用，程式碼未 vendored 進本 repo。
- **語音偵測（VAD）**：[Silero VAD](https://github.com/snakers4/silero-vad)（`snakers4`，MIT License）——`audio/vad/silero_vad.py` 選用引擎（`vad_engine="silero"`），模型檔（`silero_vad.onnx`，釘住 `v6.2.1` tag）於使用者首次啟用時下載到本機 `%APPDATA%\VoxProse\models\`，不隨 repo 版控，程式碼亦未 vendored 進本 repo。
- **UI 框架**：PyQt6（Riverbank Computing，GPL v3 / 商業雙授權）——作為執行期相依套件使用，非本 repo 程式碼的一部分；`requirements-win.txt` 直接依賴其官方 PyPI 套件。

## Third-Party Services And Trademarks

本專案與 OpenAI、Anthropic、Google（Gemini）、Groq、OpenRouter、Alibaba（Qwen）、DeepSeek、MiniMax、Ollama 等第三方 API/服務提供者沒有關聯、背書或贊助關係；程式碼中出現這些名稱僅為識別與互通目的（使用者需自備各自的 API key）。

使用者與維護者需自行遵守：

- 各 LLM / STT 供應商（OpenAI、Anthropic、Google、Groq、OpenRouter 等）各自的服務條款與用量政策。
- PyQt6 的授權條款（GPL v3 或商業授權，依實際使用情境選擇）。
- 當地著作權、商標、隱私與消費者保護法規。

## AI Output Responsibility

語音辨識與 LLM 潤飾後的文字仍可能有辨識錯誤、幻覺內容或風格偏差，使用前應自行檢查，不保證輸出內容的正確性或適合直接用於正式文件、法律或商業用途。

## Secrets Caution

不要把 Groq / OpenAI / Anthropic / Gemini / OpenRouter / Qwen / DeepSeek / MiniMax 等 API key、`config_local.json`、`config_global.json`、`sync_path.txt`、使用者 `soul.md`、`memory/*.json`、`vocab/*.json`、錄音檔（`audio/*.wav`）或辨識輸出（`output/*.txt`）提交進版控。這些項目已列在 `.gitignore` 中。
