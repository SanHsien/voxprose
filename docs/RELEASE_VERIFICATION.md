# Windows Release 實機驗證

本文件是 Windows 可攜版的發佈驗證清單。目的不是只確認 workflow 顯示綠燈，
而是證明使用者下載到的 ZIP 能完整解壓、啟動，並完成語音輸入的主要路徑。

## 判定原則

- `PASS`：本次實際執行且結果符合預期。
- `FAIL`：本次實際執行且結果不符合預期；不得發佈或宣稱完成。
- `BLOCKED`：缺真人音訊、API key、硬體或其他外部條件；不得用單元測試代替。
- pytest、CI、靜態讀碼與真機操作分開記錄，不互相替代。
- API key 不貼進 issue、log、截圖或診斷包；雲端引擎只記 provider、時間與成功／失敗。

## 一、版本與自動化基線

```powershell
git fetch origin main --prune
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
python -m pytest tests/ -v
```

記錄 commit、Python 版本、passed／skipped 數量與 skip 原因。只有
`HEAD == origin/main` 且工作樹狀態已被理解，才能把結果歸到遠端 `main`。

## 二、下載、雜湊與 ZIP 結構

以下以 `vX.Y.Z` 與 Lite 版為例：

```powershell
$VerifyRoot = Join-Path $env:TEMP "voxprose-release-verify-vX.Y.Z"
New-Item -ItemType Directory -Force -Path $VerifyRoot | Out-Null

gh release download vX.Y.Z -R SanHsien/voxprose `
  -p "ShengChengWen-Windows-Lite-vX.Y.Z.zip" `
  -p "ShengChengWen-Windows-Lite-vX.Y.Z.zip.sha256" `
  -D $VerifyRoot --clobber

$Zip = Join-Path $VerifyRoot "ShengChengWen-Windows-Lite-vX.Y.Z.zip"
$Expected = ((Get-Content "$Zip.sha256" -Raw) -split "\s+")[0].ToLowerInvariant()
$Actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $Zip).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw "SHA-256 mismatch" }

python tools\verify_release_zip.py $Zip
```

`tools/verify_release_zip.py` 會檢查：

- ZIP 可讀且全檔 CRC 正確。
- 沒有 literal `?`、Unicode replacement character 或重複 entry。
- 非 ASCII entry 有 ZIP UTF-8 flag。
- `可攜版說明.txt`、`啟動聲成文.bat`、`安裝下載教學.MD` 與四個中文情境模板各出現一次。

最後必須用 Windows 內建解壓工具做一次真實 round-trip：

```powershell
$Extract = Join-Path $VerifyRoot "expanded"
Expand-Archive -LiteralPath $Zip -DestinationPath $Extract
Get-ChildItem -LiteralPath $Extract -Recurse |
  Where-Object Name -in @(
    "可攜版說明.txt", "啟動聲成文.bat", "安裝下載教學.MD",
    "社群貼文.md", "商務回應.md", "情商大師.md", "逐字稿.md"
  ) |
  Select-Object FullName
```

少任何一個必要檔案，或 `Expand-Archive` 失敗，整個 release 即為 `FAIL`。

## 三、runtime 與麥克風預檢

在解壓後的版本目錄執行：

```powershell
.\.runtime\python.exe -c "import PyQt6, faster_whisper, sounddevice, numpy, requests, onnxruntime; print('RUNTIME_OK')"
.\.runtime\python.exe .\diagnose_mic.py
```

`diagnose_mic.py` 必須列出預設輸入裝置、成功開啟串流並完成 0.5 秒音量取樣。
只有「程式可 import」不能取代麥克風檢查。

## 四、基本語音輸入

先從 repo checkout 用解壓後版本的內嵌 Python 跑 UI 視窗 smoke check；腳本會
強制驗證實際匯入模組位於指定的 release root，並確認 Settings／About 可見、
未最小化：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$env:VOXPROSE_UI_CHECK_OUTPUT = Join-Path $VerifyRoot "ui-screenshots"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_ui_windows_check.py"
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Remove-Item Env:\VOXPROSE_UI_CHECK_OUTPUT
```

若 ZIP 內另有一層版本目錄，`$Extract` 必須改指向實際含 `ui\app.py` 與
`.runtime\python.exe` 的 package root。輸出的 `about-window.png` 不得裁字／重疊，
`settings-window.png` 應顯示完整設定頁。此腳本不代替下列真人語音操作。

1. 雙擊 `VoxProse.exe`。
2. 在記事本或其他純文字輸入框放置游標。
3. 依目前 PTT／Toggle 設定錄音，真人說「今天天氣真好」。
4. 確認文字辨識合理、貼到原本游標處，沒有貼到 VoxProse 自己的視窗。
5. 目視系統匣圖示與「聲成文」名稱。
6. 若模型需要首次下載，等完成後重新測一次；下載中的失敗不能算語音路徑失敗。

真人未發聲、沒有可用麥克風或無法目視系統匣時，對應項目記 `BLOCKED`。

## 五、Silero VAD 與 RMS 對照

先用同一份真人音訊取得可比較的 VAD 數值證據。腳本會依序要求正常說話、
咳嗽、呼吸、環境雜音各一次；每段只錄一次，再把同一份 PCM 以產品使用的
800-sample block 同時餵給 RMS 與真 Silero。預設只保留 JSON／Markdown
指標，不保存原始錄音：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$VadReport = Join-Path $VerifyRoot "real-audio-vad.json"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_audio_vad_check.py" `
  --output $VadReport
$VadExitCode = $LASTEXITCODE
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Get-Content -LiteralPath $VadReport -Raw
if ($VadExitCode -ne 0) {
  Write-Warning "真人 VAD 對照未通過；依報告判定 FAIL 或 BLOCKED"
}
```

若 ZIP 內另有一層版本目錄，`$Extract` 同樣必須指向實際含 `audio\vad\`
與 `.runtime\python.exe` 的 package root。腳本會反查 `rms_vad.py`、
`silero_vad.py` 的實際匯入路徑；指定不完整或錯誤 root 時直接失敗，不會
退回目前 checkout 產生假 PASS。只有加上 `--keep-wav` 才會在報告同名
目錄保留四段 WAV；音訊含真人聲音，除錯結束後應依本文件第八節處置，
不得 commit 或附在公開 issue。

腳本的 `PASS` 只表示：正常說話時兩引擎皆達門檻，且三種非語音情境中
Silero 的觸發情境數嚴格少於 RMS。它提供公平數值對照，但不會操作 app 的
全時模式狀態機，也不會送 STT；因此仍要完成下列 UI／端到端操作：

1. 設定 → 辨識 AI → 語音偵測引擎，先確認 Silero 顯示「可用」。
2. 選 Silero、開啟全時模式並儲存；依提示重啟後再確認設定仍是 Silero。
3. 分別測：正常說話、單次咳嗽、呼吸聲、鍵盤／環境雜音。
4. 記錄每一種聲音是否開始錄音、是否送出辨識、是否產生文字。
5. 切回 RMS、重啟並用相同聲音與距離重測。

通過標準：兩個引擎都能辨識正常說話；RMS 行為與舊版一致；Silero 對非語音的
誤觸發明顯較少。只有 ONNX 單元測試或合成音訊數值，不能把本項轉成 `PASS`。
真人腳本若回 `BLOCKED`／`FAIL`，也不能只憑 UI 看似有反應改寫為 `PASS`。

## 六、前景視窗自動情境

先驗證設定頁實際使用的三秒 callback 不會把自己搶回前景。下列命令啟動後，
看到 `[READY]` 時在三秒內切到目標程式；只有最終列出同一個 `.exe` 才算
這一層 PASS：

```powershell
$env:VOXPROSE_SOURCE_ROOT = $Extract
$env:VOXPROSE_EXPECT_FOREGROUND = "LINE.exe"
& "$Extract\.runtime\python.exe" `
  ".\tests\manual\manual_foreground_countdown_check.py"
$ForegroundExitCode = $LASTEXITCODE
Remove-Item Env:\VOXPROSE_SOURCE_ROOT
Remove-Item Env:\VOXPROSE_EXPECT_FOREGROUND
if ($ForegroundExitCode -ne 0) {
  throw "前景視窗倒數 callback 未取得預期程式"
}
```

可把 `LINE.exe` 換成實際目標。腳本會走
`SoulPageMixin._detect_foreground_app_for_rule()` 本身、反查 `soul_page.py`
與 `foreground.py` 確實來自 `$Extract`，並把原本會阻塞的結果訊息盒轉成
stdout。CI／桌面自動化若需要先準備再觸發，可另設
`VOXPROSE_FOREGROUND_ARM_FILE`；腳本會等該檔案出現後才開始三秒倒數，
外層必須設 timeout，避免協調檔未建立時無限等待。

這個 PASS 只證明 Win32 偵測與設定頁 callback；仍不包含 LLM 請求。接著完成：

1. 先啟用一個可用的 LLM provider，並手動選定 fallback 情境。
2. 設定 → 靈魂設定，啟用「前景視窗自動情境切換」。
3. 按「偵測目前前景程式」，倒數期間切到目標程式；成功訊息必須顯示目標
   `.exe`，不得是 `python.exe`、`VoxProse.exe` 或設定頁本身。
4. 把目標程式綁到一個輸出風格容易辨認的情境並儲存。
5. 在目標程式說一句，確認 LLM 輸出符合綁定情境。
6. 到未綁定程式說同類句子，確認回到手動選定的 fallback 情境。
7. 關閉自動情境後再測一次，確認不沿用上一次 override。

缺真 API key、未實際送出 LLM 請求，或只驗證 `get_foreground_process_name()`，
一律記 `BLOCKED`，不能算端到端通過。

## 七、結果紀錄

| 項目 | 結果 | 證據／備註 |
|---|---|---|
| HEAD 與 origin/main | PASS／FAIL | commit |
| pytest | PASS／FAIL | passed、skipped |
| SHA-256 | PASS／FAIL | asset、digest |
| ZIP validator | PASS／FAIL | entry 數、錯誤 |
| Expand-Archive | PASS／FAIL | 目的目錄 |
| runtime imports | PASS／FAIL | Python、依賴版本 |
| 麥克風預檢 | PASS／FAIL／BLOCKED | 裝置、峰值 |
| 基本語音貼字 | PASS／FAIL／BLOCKED | 目標程式、句子 |
| 系統匣 | PASS／FAIL／BLOCKED | 名稱、圖示 |
| Silero 真人音訊 | PASS／FAIL／BLOCKED | 說話／咳嗽／呼吸／雜音 |
| RMS 回歸 | PASS／FAIL／BLOCKED | 相同測試條件 |
| 前景情境命中 | PASS／FAIL／BLOCKED | process、scenario |
| 未命中 fallback | PASS／FAIL／BLOCKED | process、scenario |
| 真雲端 provider | PASS／FAIL／BLOCKED | provider；不記 key |

驗證完成後，把結論與日期回註根目錄 `REVIEW.md`；修 bug 時依 `AGENTS.md`
補上修復日期與 commit。

## 八、驗證後清理暫存目錄

只刪除本次自行建立的 `$VerifyRoot`，不要對整個 `$env:TEMP`、萬用字元或
尚未解析的環境變數執行遞迴刪除。先確認完整路徑仍位於系統暫存目錄：

```powershell
if ([System.String]::IsNullOrWhiteSpace($VerifyRoot)) {
  throw "拒絕刪除空白路徑"
}

$TrimSeparators = [char[]]@('\', '/')
$TempBase = ([System.IO.Path]::GetFullPath(
  [System.IO.Path]::GetTempPath()
)).TrimEnd($TrimSeparators)
$CleanupTarget = ([System.IO.Path]::GetFullPath($VerifyRoot)).TrimEnd($TrimSeparators)
$TempChildPrefix = $TempBase + [System.IO.Path]::DirectorySeparatorChar

if (
  $CleanupTarget.Equals(
    $TempBase,
    [System.StringComparison]::OrdinalIgnoreCase
  ) -or
  -not $CleanupTarget.StartsWith(
    $TempChildPrefix,
    [System.StringComparison]::OrdinalIgnoreCase
  )
) {
  throw "拒絕刪除非暫存子目錄：$CleanupTarget"
}

if (Test-Path -LiteralPath $CleanupTarget) {
  Remove-Item -LiteralPath $CleanupTarget -Recurse -Force
}
```

若受控自動化環境的安全政策即使在明確授權後仍攔截 `Remove-Item -Recurse`，
可在完成相同路徑邊界檢查後，以同一個 PowerShell 行程呼叫 .NET：

```powershell
if ([System.IO.Directory]::Exists($CleanupTarget)) {
  [System.IO.Directory]::Delete($CleanupTarget, $true)
}
```

刪除後用 `Test-Path -LiteralPath $CleanupTarget` 確認回傳 `False`。若驗證資料
需要留作事故證據，則不要清理，並在結果紀錄中寫明保留位置與用途。
