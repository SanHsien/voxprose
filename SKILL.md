---
name: voxprose
description: 維護 SanHsien/voxprose（聲成文 VoxProse），Windows 10/11 本機優先 AI 語音輸入工具。使用本機 Faster-Whisper 或選用雲端 STT，可選 LLM 潤飾、翻譯、情境與格式輸出。Fork 自 jfamily4tw/voicetype4tw-mac；完整規則以 AGENTS.md 為準。
---

# 聲成文 VoxProse

## 先讀

1. [`AGENTS.md`](AGENTS.md)：唯一完整 AI 維護規則。
2. [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)：Windows 已知地雷、測試、打包與實機驗證。
3. 任務涉及上游時再讀 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)；涉及 provenance 再讀 [`NOTICE.md`](NOTICE.md)。

## 快速定位

- `main.py` → `ui/app.py`：啟動與主協調流程
- `hotkey/`：Windows 全域快捷鍵
- `audio/`：錄音與 VAD
- `stt/`：本機／雲端語音辨識；Windows 本機 Whisper 走子行程隔離
- `llm/`：文字潤飾供應商
- `soul/`：Base / Scenario / Format
- `output/`：結果貼回前景視窗
- `config.py` / `paths.py`：設定與資料路徑
- `vocab/` / `memory/` / `stats/`：詞彙、長期記憶、統計
- `tests/`：pytest；`tests/manual/`：Windows 實機檢查

## 常用驗證

```powershell
python -m pytest tests/ -v
```

涉及真實錄音／STT／UI／快捷鍵／焦點貼字時，依 `AGENTS.md` 補 Windows 實機驗證。沒有實測就明確標記未驗證，不要推測通過。

## 不要做

- 不重新加入 macOS 專屬程式碼。
- 不提交 API key、使用者設定、錄音、輸出、模型等私密或大型資料。
- 不在沒有明確需求時修改 Windows 安裝／打包／Release 鏈。
- 不把 `REVIEW.md` 當一般 bug 流水帳；更新條件以 `AGENTS.md` 為準。

## 完成回報

列出修改檔案、測試結果、Windows 實機驗證範圍，以及是否碰到 STT 子行程隔離或打包鏈。
