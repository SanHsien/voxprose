## Why

新用戶在 Mac Mini 上使用 v2.9.11 時遇到兩個致命問題：
1. **LLM 幻覺**：空白的系統提示詞導致 OpenRouter 返回無關內容（如「謝謝觀賞，下次再見」）
2. **OpenSSL 打包破裂**：libssl.3.dylib 內部仍指向使用者機上不存在的 Homebrew 路徑，要求用戶手動安裝

用戶要求：安裝後無需手動干預，所有依賴問題在打包階段解決。

## What Changes

- 在 `llm/prompts.py` 建立統一的語言特定系統提示詞集合，移除散落在各 LLM 類別中的硬編碼提示詞
- 修改所有 LLM 類別（openrouter、minimax、claude、gemini、qwen、deepseek、ollama、openai_llm）的 `refine()` 方法簽名，當提示詞為空時自動使用 `get_default_system_prompt(language)`
- 增強 `post_build_fix.py` 中的後編譯步驟，在 py2app 完成後執行 `fix_libssl_rpath()`，使用 `install_name_tool` 將 libcrypto.3.dylib 與 libssl.3.dylib 的絕對路徑改寫為相對路徑（`@loader_path`）
- 在 `build_all.sh` 中呼叫修復函數，確保每次編譯都自動執行

## Non-Goals

- 不修改 LLM 模型選擇或提示工程方案的邏輯
- 不影響已有的設定檔格式；保持向後相容性
- 不涉及 STT 或其他語音模組的改動

## Capabilities

### New Capabilities

（無新功能，此為純內部重構）

### Modified Capabilities

（無需修改規格；此為實作細節改進）

## Impact

- **受影響的代碼**：
  - `llm/prompts.py`（新建）
  - `llm/__init__.py`、`llm/openrouter.py`、`llm/minimax.py`、`llm/claude.py`、`llm/gemini.py`、`llm/qwen.py`、`llm/deepseek.py`、`llm/ollama.py`、`llm/openai_llm.py`（修改）
  - `post_build_fix.py`（增強）
  - `build_all.sh`（修改呼叫順序）

- **受影響的用戶**：新裝戶（macOS）不再需要手動安裝 OpenSSL；LLM 功能獲得一致的預設提示詞
