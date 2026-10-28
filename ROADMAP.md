# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `31aa9db3c894` 查的快照，開工前先重查 GitHub。

## 現況

聲成文 VoxProse：Windows 10/11 本機優先語音輸入工具（Whisper → 可選 LLM 潤飾／翻譯 → 貼回前景視窗），是 `jfamily4tw/voicetype4tw-mac` 的 Windows-only fork，私有（`AGENTS.md`）。健康：`main` 的 CI 與 CodeQL 最近一次 success（2026-10-28，`31aa9db3c894`）；open issue 0、open PR 0、Dependabot 與 Code scanning 告警 0；最新 release 是 v3.4.4（2026-07-25），其後 `CHANGELOG.md` 的 `[Unreleased]` 已累積第二輪深掃的 13 項缺陷修正與依賴調整，尚未發版（2026-10-29 `gh` 查詢）。上游審到哪裡看 `docs/UPSTREAM.md` 的 sync-points；上游更新檢查最近一次 success（2026-10-26），沒有待審項目。卡住的是需要真人、真 API key 的驗證，不是程式缺陷。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 決定並發佈下一個 patch 版（v3.4.5 或維護者另訂） | 最新 release 是 v3.4.4，`pyproject.toml` 版號仍是 3.4.4，`[Unreleased]` 內的修正（含 Gemini API key 改走標頭、避免外流到 log 與診斷包）使用者還拿不到 | `CHANGELOG.md` 把 `[Unreleased]` 切成版本段；`pyproject.toml` 與 tag 一致；Release workflow success；`python tools/verify_release_zip.py` 對下載的 Lite 與 NoModel 兩包通過；Lite 在 Windows `Expand-Archive` 解壓成功、啟動顯示新版本；SHA-256 與 sidecar、GitHub digest 一致 | 維護者 | `gh release list -R SanHsien/voxprose`（最新 v3.4.4）；`pyproject.toml:3`；`CHANGELOG.md:11-24`；`tools/verify_release_zip.py` |
| 補完三項需要真人或真 API key 的實機驗證：27-1（Silero VAD 真人音訊）、27-2（前景情境 LLM 端到端）、28-3（UIA 崩潰歸因） | 自動化測試覆蓋不到；`REVIEW.md` 把它們標為 🔍，不得在沒證據時轉為 ✅ | 逐項依 `docs/DEVELOPMENT.md` 的驗證流程執行，結果與證據回註在 `REVIEW.md` 對應列並改狀態；27-1 要用同一段 PCM 比較 RMS 與 Silero 兩引擎，並涵蓋說話、咳嗽、呼吸、雜音；27-2 要用真 API key 確認前景視窗實際套用該情境 prompt | 維護者 | `REVIEW.md` 27-1、27-2、28-3 列；接續開發報告（2026-10-2x）「REVIEW.md」段 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 評估並升級 `anthropic` 到 1.x／2.x | Anthropic 發出新版（`.github/dependency-deferrals.json` 的暫緩會自動失效並重新提醒），或維護者決定潤飾功能不再依賴 `temperature=0.1`、並提供真實 API key | 先決定溫度控制的替代做法並寫進 `docs/DECISIONS.md`；以真實 API key 驗證 `refine()` 在預設模型上可用；`requirements-win.txt` 上限調整、`dependency-deferrals.json` 該筆移除；`pytest tests -q` 綠；依賴新鮮度檢查不再報 `anthropic` | Claude Opus | `.github/dependency-deferrals.json`（`deferredLatest` 2.3.0）；`llm/claude.py:24-30`（`temperature=0.1`）；`docs/DECISIONS.md` 2026-08-29（補）條目 |
| 設定／記憶／統計檔損毀時先把損毀檔改名保留，再以空值啟動 | 維護者同意這個行為變更（目前載入失敗退回空值，下次存檔就覆蓋掉損毀檔） | 對設定、記憶、統計、詞彙各有測試：餵入損毀檔後，原檔被改名成帶時間戳的備份、新檔為有效空值、使用者資料可事後搶救；原子寫入的既有測試（`tests/test_atomic_json_writes.py`）仍綠 | Claude Sonnet | `docs/DECISIONS.md:425`（觀察清單第 3 點）；`tests/test_atomic_json_writes.py` |
| 為 `stats`／`memory`／`vocab` 的讀改寫加上跨執行緒鎖 | 找到穩定重現「VAD 全時模式 worker 與 PTT 執行緒同時結束時覆蓋一筆紀錄」的方法，或有使用者回報紀錄遺失 | 新增的壓力測試在加鎖前能重現遺失、加鎖後 N 次重跑零遺失；不造成熱鍵或錄音路徑阻塞 | Claude Opus | `docs/DECISIONS.md:424`（觀察清單第 2 點，目前無穩定重現方式） |
| ASCII 詞彙的模糊比對規則（預設詞庫 `Slack` 會把 `black` 改成 `Slack`） | 維護者決定要不要把 ASCII 詞彙排除在 edit-distance 比對之外，或有使用者回報誤改 | 決定寫進 `docs/DECISIONS.md`；測試涵蓋「`black` 不被改」與「中文同音字修正（如 生成文→聲成文）照常運作」兩個方向 | Claude Sonnet | `vocab/manager.py:204-215`（只過濾 3 字以下）；`docs/DECISIONS.md:423`（觀察清單第 1 點） |
| 選單情境名稱只去掉開頭的 emoji 與空白，保留 `_`、`-` 等檔名字元；比對檔名時用原始檔名，不用顯示名稱（修正 `_work.md` 這類以符號開頭的情境檔對不到檔） | 維護者決定要修（`docs/DECISIONS.md:426` 觀察清單第 4 點） | 先加一條在修前會失敗的測試（建立 `_work.md` 並從選單選取，確認載入的是該檔）；`pytest tests -q` 綠；有 emoji 前綴的情境顯示名稱不變 | Claude Sonnet | `ui/menu_bar.py:77,104`；`docs/DECISIONS.md:426` |
| Silero VAD 模型下載後做雜湊驗證 | 維護者決定要修（`docs/DECISIONS.md:427` 觀察清單第 5 點；現況來源已釘 tag、風險低） | 程式內寫死該 tag 模型的 SHA-256；雜湊不符時拒絕載入並刪除檔案、回報可辨識的錯誤；測試涵蓋雜湊相符、不符與下載中斷三種情況，不連網 | Claude Sonnet | `audio/vad/silero_vad.py:42-46`（`MODEL_URL` 釘 `v6.2.1`，檔內無 `sha256`／`hashlib`）；`docs/DECISIONS.md:427` |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 重新加入 macOS 專屬 API、依賴或打包分支；移植上游 Mac 線（`main`）程式碼 | 本 fork 是 Windows-only，Mac 線只分析吸收、不追蹤程式碼（`docs/UPSTREAM.md` sync-points 中 `main.last_merged` 為 `null`） | 維護者明確改變產品範圍 |
| 自動核准或自動合併 Dependabot PR | PyQt6、Whisper、ONNX Runtime、CUDA 與 Release actions 可能影響 Windows 真機或發行包，`AGENTS.md` 規定一律人工審查並先讀 diff | 有可在真 Windows 環境重跑的完整發版驗證自動化之後 |
| 「快速翻譯」在 LLM 關閉時加上畫面提示 | 既有產品行為，是否提示屬 UI 決定，不是缺陷（`docs/DECISIONS.md:428`） | 有使用者回報因此困惑，或維護者決定調整 UI 文案 |
| 為了單純文件修改新增 review／decision／postmortem 文件 | `AGENTS.md` 明確不要，只有資訊具有長期維護價值時才新增 | 資訊具有長期維護價值時 |

## 維護方式
fork 追蹤 `jfamily4tw/voicetype4tw-mac`：上游更新檢查每週一 02:00 UTC 比對 `docs/UPSTREAM.md` 的 sync-points，有新項目才開 issue；逐筆判斷後採用（手工移植並補測試，推進 `last_merged` 與 `last_reviewed`）或不採用（只推進 `last_reviewed`、補 Skipped 表與理由）。failure 代表上游有未審項目，不是工具壞。依賴新鮮度每月 1 日檢查；判斷過暫不升的套件記在 `.github/dependency-deferrals.json`，綁定當時版本。查現況：`gh issue list -R SanHsien/voxprose`、`gh api repos/SanHsien/voxprose/dependabot/alerts?state=open`、`gh run list -R SanHsien/voxprose -b main -L 5`。
