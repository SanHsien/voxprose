## Context

**現狀**：
- LLM 系統提示詞散落在各類別建構子中，每個模型（OpenRouter、MiniMax、Claude、Gemini 等）重複定義
- 在 config.py 中 `DEFAULT_CONFIG` 故意留空 `llm_prompt` 欄位（註解「留空使用內建 prompt」），但 `refine()` 方法無視回退邏輯
- `openrouter.py:refine()` 方法接收 `prompt` 參數卻直接使用，而非使用 `self.prompt`，導致空字串被傳入 API
- 新用戶在 Mac Mini 上發現：libssl.3.dylib 內部仍硬編碼指向 `/opt/homebrew/Cellar/openssl@3/3.6.2/lib/libcrypto.3.dylib`，而該路徑在用戶機上不存在
- 用戶被迫手動安裝 OpenSSL，違反「零手動干預」原則

**約束**：
- 保持向後相容的設定檔格式
- 不修改 LLM 模型選擇或推理流程
- 自動化打包階段，無需用戶干預

## Goals / Non-Goals

**Goals:**
- 建立單一真實來源（llm/prompts.py）管理所有語言的系統提示詞
- 確保所有 LLM 類別在提示詞為空時自動使用預設值
- 修復 macOS 打包流程，自動改寫 dylib 依賴的絕對路徑為相對路徑
- 新用戶無需執行任何手動安裝步驟即可使用應用

**Non-Goals:**
- 不修改現有設定檔格式或遷移邏輯
- 不改變 LLM 推理、模型選擇或提示詞內容本身
- 不涉及 Windows 打包流程

## Decisions

### 決策 1：在 llm/prompts.py 中集中管理語言特定的系統提示詞

**選擇**：建立 `llm/prompts.py` 包含：
```python
SYSTEM_PROMPTS = {
    "zh": "請將以下語音辨識結果整理成通順的文字，保持原意，只回傳結果：",
    "en": "Refine the following speech recognition output into clear, coherent text...",
    "ja": "次の音声認識結果を整理し、明確で一貫性のあるテキストに..."
}

def get_default_system_prompt(language: str = "zh") -> str:
    return SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["zh"])
```

**理由**：
- 單一真實來源（SSOT）：所有模型共用一個地方定義提示詞，避免不同步
- 易於審計：語言一致性、提示詞質量審查、A/B 測試時更新

**棄卻方案**：
- 分別保存在各模型類別 → 導致重複、維護負擔重、不一致
- 存儲在設定檔中 → 增加設定複雜度，新用戶難以理解

### 決策 2：使用「或邏輯」後退機制修復 LLM 類別

**選擇**：修改所有 `refine(text, prompt=None)` 方法為：
```python
def refine(self, text: str, prompt: str = None) -> str:
    effective_prompt = prompt or get_default_system_prompt(self.language)
    return self._call_api(text, effective_prompt)
```

**理由**：
- 兼容性：既有呼叫 `refine(text, "custom")` 仍可用，新呼叫 `refine(text)` 得到預設
- 簡單明確：不需修改呼叫端；後退邏輯單一清晰

**棄卻方案**：
- 在呼叫端檢查 → 增加複雜度，容易遺漏
- 設定檔回填時驗證 → 不適用於 API 呼叫路徑

### 決策 3：使用 install_name_tool 進行後編譯 rpath 修復

**選擇**：在 `post_build_fix.py` 中新增 `fix_libssl_rpath()` 函數：
```bash
install_name_tool -change /opt/homebrew/Cellar/openssl@3/3.6.2/lib/libcrypto.3.dylib \
                          @loader_path/libcrypto.3.dylib \
                          /path/to/app/libssl.3.dylib
```

**理由**：
- 標準 macOS 工具：內建於 Xcode，無額外依賴
- 隔離修復：僅修改已打包的二進位檔，不影響編譯過程
- 自動化：在 build_all.sh 中自動執行，用戶無感知

**棄卻方案**：
- 編譯時設定 RPATH → 需修改 py2app 組態、編譯過程複雜
- 要求用戶手動執行 → 違反零干預原則

### 決議 4：在 build_all.sh 中集成 rpath 修復

**選擇**：py2app 完成後立即呼叫 `fix_libssl_rpath()`，在 DMG 簽署前執行

**理由**：
- 順序保證：確保所有步驟在正確時間點執行
- 可見性：Build log 記錄修復過程，便於除錯
- 可追蹤：git history 記錄何時啟用此步驟

## Risks / Trade-offs

| 風險 | 減緩方法 |
|------|---------|
| 新增 LLM 語言忘記更新 llm/prompts.py | Code review 檢查表；CI 檢查（語言列舉一致性） |
| install_name_tool 在某些 macOS 版本失敗 | 測試所有支持的 macOS 版本（Ventura、Sonoma、Sequoia） |
| 誤改其他 dylib | 明確指定文件路徑和目標路徑，加日誌輸出 |
| 向後相容性破裂 | 現有呼叫 `refine(text, "")` 仍得到預設（因為 `"" or default` = default） |

**Trade-off**：
- 打包時間略增（rpath 修復 < 1 秒）vs. 用戶無手動干預 ✓

## Migration Plan

1. **部署前**：
   - 在開發機測試 rpath 修復流程
   - 驗證多個 macOS 版本（Ventura、Sonoma、Sequoia）
   - 檢查 DMG 簽署未被 rpath 修復破壞

2. **部署步驟**：
   - 合併代碼到主分支
   - 執行完整 build 流程 (`build_all.sh`)
   - 於全新 Mac Mini 上測試解包後的應用（無需手動安裝 OpenSSL）

3. **回滾策略**：
   - 若 rpath 修復失敗，禁用 `fix_libssl_rpath()` 呼叫，直接使用前版本
   - 若 LLM 提示詞導致不佳結果，直接編輯 `llm/prompts.py` 中的 SYSTEM_PROMPTS

## Open Questions

- 是否需要在 CI/CD 中驗證 install_name_tool 成功？建議加 checksums
- 新增語言時是否需要 code review approval？建議是
