# 參考專案與服務調研

> 調研日期：2026-07-20
> 調研方法：以 `firecrawl_search`（web search + 內容摘要）針對四大類逐項查證，優先採官方網站／GitHub repo／官方定價頁作為來源；每個條目至少交叉比對 1-2 個獨立來源（Reddit/HN/第三方評測文章僅作旁證，不單獨作為存在性依據）。凡搜尋結果中提及但未能找到官方頁面或 repo 佐證的項目，一律標註「待確認」或不收錄（本次因證據不足捨棄 3 項，詳見文末）。
>
> 本文件目的：作為 VoxProse（聲成文，Windows 本地優先語音輸入法：全域熱鍵 → faster-whisper 本地辨識 / 可選雲端引擎 → 可選 LLM 潤飾 → 游標注入；repo 內部代號沿用 `voicetype`）功能擴充與 roadmap 決策的外部參考盤點，不代表任何採用承諾。

---

## 1. 同類產品（語音輸入 / dictation 工具）

| 名稱 | 授權/商業模式 | 平台 | 本地/雲端 | 與 VoxProse 相關的亮點 | 可借鏡點（具體到功能） |
|---|---|---|---|---|---|
| [TypeLess](https://www.typeless.com/) | 商業（訂閱） | Windows / macOS / iOS / Android | 雲端 | 自動偵測多語言混講並即時轉錄、免手動切換語言 | VoxProse 目前語言由使用者/設定指定；可評估「中英混講自動偵測」邏輯，改善中英夾雜口語的辨識切分（對照 `stt/language.py`） |
| [Wispr Flow](https://wisprflow.ai/) | 商業（訂閱） | Windows / macOS | 雲端 | 依「目前作用中應用程式」自動套用不同輸出格式（如 Slack 用短句、郵件用完整句子） | **已實作**（`utils/foreground.py`＋`config.py` 的 `auto_scenario_enabled`/`auto_scenario_rules`，2026-07-23，🔍 待實機驗證）：VoxProse 三層靈魂系統（`soul/`）新增依前景視窗自動選情境模板的選用功能，預設關閉，詳見 `docs/DECISIONS.md` |
| [Superwhisper](https://superwhisper.com/) | 商業（一次性+訂閱分層） | macOS / Windows / iOS | 本地 + 雲端混合 | 使用者可自訂/分享「AI 模式」（提示詞+輸出風格組合），社群可互相匯入模式 | 可對照 VoxProse 三層靈魂系統，評估「模式匯出/匯入 JSON」讓使用者分享情境模板與輸出格式組合，而非僅限本機設定 |
| [Aqua Voice](https://aquavoice.com/) | 商業（訂閱） | Windows / macOS | 雲端 | 支援語音直接下達編輯指令（如「刪掉上一句」），啟動延遲宣稱 <50ms | VoxProse 目前僅做「辨識→（可選潤飾）→貼上」單向輸出；可評估新增有限的語音編輯指令集（如「重講」「刪除剛才」）作為未來魔術語擴充方向 |
| [WhisperWriter](https://github.com/savbell/whisper-writer)（savbell） | MIT，開源 | Windows / macOS / Linux（Python） | 本地（Whisper API 或本地模型）+ 可選雲端 | 架構與 VoxProse 高度相似：全域熱鍵→VAD 偵測停頓自動結束→Whisper 轉錄→自動輸入；config 檔案驅動 | 架構最接近的開源同類，可作為設定檔結構、VAD 停頓判斷參數命名的對照參考 |
| [Vibe](https://github.com/thewh1teagle/vibe)（thewh1teagle） | 開源（Tauri/Rust） | Windows / macOS / Linux | 本地（whisper.cpp） | 用 whisper.cpp 取代 Python + PyTorch 堆疊，Tauri 打包後體積遠小於目前 VoxProse 的可攜式 Python + CUDA 方案 | 佐證「whisper.cpp 後端」路線可行性（見下表本地 STT 引擎），可作為評估是否推出免 CUDA/PyTorch 的輕量替代辨識後端的參考實作 |
| [Amical](https://github.com/amicalhq/amical) | 開源（AGPL 系列，需查證確切版本） | Windows / macOS / iOS / Android | 本地（Whisper）+ 可選開源 LLM 潤飾 | 架構幾乎與 VoxProse 一致：Whisper 辨識 + LLM 後處理潤飾筆記/文字，且同樣主打隱私與離線 | 架構上最直接的開源對標專案，值得追蹤其 roadmap 作為功能差異化參考（例如其筆記整理功能） |
| [Voicetypr](https://github.com/moinulmoin/voicetypr)（moinulmoin） | 開源 | Windows / macOS | 本地（離線優先） | 明確定位為「Superwhisper / Wispr Flow 的開源離線替代品」 | 可對照其 onboarding／模型下載體驗，評估 VoxProse `setup_win.bat` 首次安裝流程是否有可簡化之處 |

**其他有觀察到但本次未深入評估的專案**（曾在原題目列出或搜尋中出現，僅列可信來源供日後追蹤，未列入上表評分）：
- [FUTO Voice Input](https://voiceinput.futo.org/)／[GitLab](https://gitlab.futo.org/keyboard/voiceinput)：僅 Android，「source-first」授權（非 OSI 開源），與 VoxProse 的 Windows 桌面場景不直接相關。
- [Talon Voice](https://talonvoice.com/)：免費版+付費 Patreon，主打「完全語音控制電腦/寫程式」而非單純聽寫，使用情境與 VoxProse 的聽寫定位不同，故未深入比較。
- [Buzz](https://github.com/chidiwilliams/buzz)：MIT 開源，但定位是離線批次轉錄音檔/影片（非即時熱鍵聽寫工具），與 VoxProse 的即時輸入法場景不同。

---

## 2. 本地 STT 引擎選項（faster-whisper 之外）

| 名稱 | Windows 可用性 | 中文表現 | 授權 | 與 VoxProse 相關的亮點 | 可借鏡點 |
|---|---|---|---|---|---|
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp)（ggml-org） | 官方支援（MSVC/MinGW build，CPU-only 或 CUDA/ROCm/OpenVINO 加速） | 與原始 Whisper 模型同源，中文表現取決於載入的 Whisper 模型大小 | MIT | 純 C/C++ 實作，無需 Python/PyTorch 執行環境，二進位體積遠小於目前 faster-whisper + CUDA 堆疊 | 可評估推出「輕量無 CUDA 版本」時以 whisper.cpp 取代 faster-whisper，縮小 Lite 版安裝體積（對照 `release_win.ps1` 的 Lite/NoModel 分包邏輯） |
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（k2-fsa） | 官方支援（含 Tauri 桌面應用範例） | 強項：原生支援 Paraformer / SenseVoice / Zipformer 等中文（含多方言、粵語）模型，中文辨識社群評價佳 | Apache-2.0 | 支援真正的串流（streaming）辨識，可邊講邊出字，而非等一段語音結束才送整段轉錄 | VoxProse 目前「全時模式」（`audio/auto_trigger.py`）是先用 RMS 能量偵測切段、整段送給 STT；可評估導入串流辨識取得「邊講邊顯示」的體驗，減少感知延遲 |
| [Vosk](https://github.com/alphacep/vosk-api)（alphacep） | 官方支援 | 支援中文等 20+ 語言，但整體辨識準確度普遍低於 Whisper 系列 | Apache-2.0 | 模型極輕量（小模型約 50MB，記憶體需求約 300MB） | 可作為「低階硬體/無 GPU 精簡模式」的備用引擎選項，犧牲準確度換取極低資源需求 |
| [NVIDIA Parakeet / Canary](https://huggingface.co/nvidia/canary-1b-v2)（NeMo 系列） | 需透過 NeMo 框架，原生 Windows 整合複雜度高於 whisper.cpp/faster-whisper（待確認實際 Windows 部署難度） | 官方標示多語言支援，但中文（尤其繁體）表現未見獨立評測數據，**待確認** | CC-BY-4.0 | 在 NVIDIA GPU 上號稱業界領先的速度與 WER（英語為主的評測） | 若未來評估「進階 CUDA 加速模式」，可將 Parakeet/Canary 列為 faster-whisper 之外的效能升級選項，但需先驗證繁中辨識品質與 NeMo 相依套件是否與現有 CUDA/PyQt6 載入順序衝突（見 `windows_cuda_qt_crash_postmortem.md`） |
| [Moonshine](https://github.com/moonshine-ai/moonshine)（Useful Sensors） | 官方支援 Windows/macOS/Linux/行動裝置 | 主要針對英語優化，中文支援程度**待確認**（未查到明確的繁中評測） | 開源（需查證確切授權條款，官方稱 MIT 系列，**待確認**細節） | 專為低延遲即時應用設計的小模型（比 Whisper tiny 更快） | 若中文支援不足，可能僅適合作為英文聽寫場景的輕量備用引擎，暫不建議作為主力中文引擎 |

---

## 3. 雲端 STT API（Groq / Gemini / OpenRouter 之外值得評估）

| 名稱 | 商業模式 | 與 VoxProse 相關的亮點 | 可借鏡點 |
|---|---|---|---|
| [Deepgram](https://deepgram.com/product/speech-to-text)（Nova-3） | 依用量計費，約 $0.0065–0.0092/分鐘（依方案與串流/預錄不同） | 專為低延遲串流設計的 API，內建語者分離、格式化等附加功能 | 若 VoxProse 未來要做「即時串流顯示辨識中文字」的體驗，Deepgram 的串流 API 設計可作為介面/回呼模式參考，即使不採用其服務 |
| [AssemblyAI](https://www.assemblyai.com/universal-2)（Universal-2/3.5） | 依用量計費，約 $0.15–0.21/小時（非即時），支援 99 種語言 | 提供「keyterm prompting」（提示關鍵詞提升辨識準確度）附加功能 | 與 VoxProse 現有的 `vocab/manager.py` 自訂詞彙/自動記憶機制概念高度相符；若導入此雲端引擎，keyterm prompting 可直接對接現有詞彙庫，提升專有名詞辨識率 |
| [ElevenLabs Scribe](https://elevenlabs.io/speech-to-text) | 依用量計費，約 $0.22–0.40/小時 | 官方（自評）宣稱在 90+ 語言的辨識準確度上優於 Whisper / Deepgram / Gemini（**此為廠商自評數據，未見獨立第三方驗證，需謹慎看待**） | 若未來擴充雲端引擎選項，可用與現有 `stt/groq_whisper.py`／`stt/gemini_stt.py`／`stt/openrouter_stt.py` 一致的 `BaseSTT` 介面（`stt/base.py`）新增一個 `elevenlabs_stt.py`，作為第四個雲端選項提供使用者比較 |

---

## 4. 周邊技術（文字注入、VAD、熱鍵、標點恢復）

| 名稱/主題 | 授權/性質 | 與 VoxProse 相關的亮點 | 可借鏡點 |
|---|---|---|---|
| [Silero VAD](https://github.com/snakers4/silero-vad) | MIT，開源（PyTorch 模型，本專案改用 onnxruntime + ONNX 版模型） | 業界常用的輕量神經網路 VAD，精準度優於單純能量（RMS）門檻判斷 | **已實作**（`audio/vad/silero_vad.py`，`vad_engine="silero"`，2026-07-23）：VoxProse 現有「全時模式」（`audio/auto_trigger.py`）RMS + 遲滯（hysteresis）門檻切段的邏輯抽象成 `audio/vad/base.py` 介面，Silero 引擎作為選用替代（預設仍是 `rms`，行為不變）；onnxruntime 因 PyPI wheel 版本區間無法同時涵蓋本專案 CI 矩陣 3.10-3.14，改列選用依賴，詳見 `docs/DECISIONS.md` |
| [Windows Text Services Framework (TSF)](https://learn.microsoft.com/en-us/windows/win32/tsf/text-services-framework) | Microsoft 原生框架（非開源函式庫，Win32 API） | 是 Windows 原生的「輸入法/文字服務」整合層，IME、手寫辨識、語音輸入的官方標準介面 | VoxProse 目前文字注入（`output/injector.py`）採「剪貼簿 + 模擬 Ctrl+V」+ 針對 LLM 模式用 `SendInput` 模拟 Shift+Left 選字的作法，註解中明確提到是為了避開 IME 衝突而選擇此路線；TSF 是「正規」的 Windows 文字服務整合方式，可注入至任何支援 TSF 的應用而不經剪貼簿，但實作複雜度高（需 COM 介面），可列為長期重構方向而非近期優先項 |
| [boppreh/keyboard](https://github.com/boppreh/keyboard) | MIT，開源（Python） | 提供跨 Windows/Linux 的全域鍵盤 hook 與熱鍵組合解析 | VoxProse 現有 `hotkey/listener.py` 為 Windows 專屬底層實作；可作為熱鍵組合解析（如多鍵組合、修飾鍵狀態管理）的程式介面設計參考，非必然替換現有實作 |
| 標點恢復（Punctuation Restoration，[GitHub topic](https://github.com/topics/punctuation-restoration)） | 各實作授權不一（多為 MIT/Apache，需逐一查證） | 針對不主動輸出標點的 ASR 引擎（如部分 Vosk/Moonshine 輸出），額外做標點與大小寫還原 | 若未來導入 Vosk 或其他不含標點恢復的引擎作為備用選項，可在 STT 輸出後、LLM 潤飾前insert一個輕量標點恢復步驟，避免完全依賴 LLM 潤飾階段補標點（目前 VoxProse 的標點很大程度依賴可選的 LLM 潤飾層） |

---

## 對 VoxProse roadmap 的啟發

以下建議按優先順序排列，均標注來源條目，僅供決策參考，非已決議事項：

1. **已實作**：前景應用程式感知的情境模板自動切換（來源：Wispr Flow）。見上表「已實作」備註與 `docs/DECISIONS.md` 2026-07-23 條目（`utils/foreground.py` 純 ctypes 偵測、規則比對語義、UI）。
2. **已實作**：評估 Silero VAD 取代/輔助全時模式的 RMS 能量判斷（來源：Silero VAD）。見上表「已實作」備註與 `docs/DECISIONS.md` 2026-07-23 條目（真模型實測數字、onnxruntime 選用依賴決策）。
3. **AssemblyAI keyterm prompting 與現有詞彙庫的整合可能性**（來源：AssemblyAI）。若日後導入 AssemblyAI 作為第四個雲端引擎選項，其 keyterm prompting 機制可直接讀取 `vocab/manager.py` 的 `custom_vocab.json`／`auto_memory.json`，讓自訂詞彙同時嘉惠雲端與本地兩種辨識路徑。
4. **whisper.cpp 作為免 CUDA/PyTorch 輕量後端的可行性評估**（來源：Vibe、whisper.cpp 本身）。目前 Lite/NoModel 打包已針對體積分層，若進一步想縮小無 GPU 使用者的安裝體積與依賴複雜度，whisper.cpp（MIT，純 C/C++）是已有其他開源專案（Vibe、Handy）驗證過可行的路線，但需重新設計 Python↔C++ 的呼叫介面，工作量不小。
5. **有限度的語音編輯指令（如「刪掉上一句」「重講」）**（來源：Aqua Voice）。目前 VoxProse 是單向「辨識→（可選潤飾）→輸出」流程；可作為長期功能方向探索小範圍語音編輯指令集，須注意與現有「魔術語即時翻譯」機制的觸發詞衝突設計。

---

## 本次調研中因證據不足而捨棄的項目

以下項目在搜尋過程中出現但因缺乏可信官方來源、平台/授權資訊矛盾或無法確認仍在維護，本次未收錄：3 項（具體名稱因證據強度不足不列出以免誤導，日後如有需要可重新搜尋查證）。

---

## 維護慣例

本文件採 **latest-only** 維護：每次重大調研後直接更新／覆寫對應章節內容與日期戳，不保留歷史版本快照（歷史脈絡如需追溯，請查 git log）。若需新增分類或大幅改版，建議先在 `docs/DECISIONS.md` 記錄決策理由。
