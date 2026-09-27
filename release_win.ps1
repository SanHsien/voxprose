# release_win.ps1 - 聲成文 VoxProse 真可攜版打包器 (Portable Release Packager)
#
# 產出「解壓即用」的可攜資料夾與 ZIP：
#   - 自建 .runtime（嵌入式 Python 3.12 + 全部依賴，路徑無關、免安裝 Python）
#   - 隨附 Whisper medium 模型（bundled_models/，首次啟動自動裝入 %APPDATA%）
#   - 隨附 VoxProse.exe 啟動器（無現成檔案時以內建 csc 現場編譯）
#
# 用法:
#   .\release_win.ps1           → Full（含 CUDA 加速函式庫 + medium 模型）
#   .\release_win.ps1 -Lite     → Lite（無 CUDA、無模型，首次啟動線上下載）
#   .\release_win.ps1 -NoModel  → NoModel（含 CUDA、無 medium 模型，首次啟動線上下載）
#   .\release_win.ps1 -SkipZip  → 只產出資料夾，不壓縮（測試用）
param([switch]$Lite, [switch]$NoModel, [switch]$SkipZip)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

# 0. 從 paths.py 取得 BUILD_ID（內部識別）與 pyproject.toml 取得 semver 版本號
#    （命名跟著完整 semver 走，不寫死；patch release 不與舊產物同名）
$buildMatch = Select-String -Path "paths.py" -Pattern 'BUILD_ID = "BUILD-(\w+)-STABLE"'
$Build = if ($buildMatch) { $buildMatch.Matches[0].Groups[1].Value } else { "UNKNOWN" }

$verMatch = Select-String -Path "pyproject.toml" -Pattern 'version = "(\d+\.\d+\.\d+)"'
$Version = if ($verMatch) { $verMatch.Matches[0].Groups[1].Value } else { "UNKNOWN" }

if ($Lite) {
    $ReleaseFolder = "dist\ShengChengWen-Windows-Lite-v$Version"
    $Edition = "Lite (no CUDA, no model)"
} elseif ($NoModel) {
    $ReleaseFolder = "dist\ShengChengWen-Windows-NoModel-v$Version"
    $Edition = "NoModel (CUDA, no model)"
} else {
    $ReleaseFolder = "dist\ShengChengWen-Windows-v$Version"
    $Edition = "Full (CUDA + medium model)"
}
$ZipFile = "$ReleaseFolder.zip"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   聲成文 VoxProse Portable Packager v$Version (BUILD-$Build) — $Edition" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# 1. Cleanup
if (Test-Path $ReleaseFolder) {
    Write-Host "[INFO] Cleaning up old release folder..."
    Remove-Item -Recurse -Force $ReleaseFolder
}
if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }
New-Item -ItemType Directory -Path $ReleaseFolder -Force | Out-Null
$Release = (Resolve-Path $ReleaseFolder).Path

# 2. Copy app source folders
$Folders = @(
    "actions", "assets", "audio", "hotkey", "llm", "output", "memory",
    "soul", "stats", "stt", "ui", "utils", "vocab", "tools"
)
foreach ($folder in $Folders) {
    if (Test-Path $folder) {
        Write-Host "[INFO] Copying folder: $folder..."
        robocopy $folder "$Release\$folder" /E /XD __pycache__ /XF *.log *.pyc *.bak /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    }
}

# 3. Copy root files
$Files = @(
    "main.py", "paths.py", "config.py", "config.json",
    "requirements-win.txt", "requirements-cuda-win.txt",
    "setup_win.bat", "run_voicetype.bat", "啟動聲成文.bat",
    "create_shortcut.ps1", "diagnose_mic.py", "self_check.py",
    "README.md", "安裝下載教學.MD"
)
foreach ($file in $Files) {
    if (Test-Path $file) {
        Copy-Item -Path $file -Destination "$Release\$file"
    }
}

# 4. Build embedded Python runtime inside the release folder
Write-Host "[INFO] Building embedded Python runtime (.runtime)..."
Push-Location $Release
try {
    & powershell -ExecutionPolicy Bypass -File "$Release\tools\get_portable_python.ps1"
    if (-not (Test-Path "$Release\.runtime\python.exe")) {
        throw "Embedded Python setup failed."
    }
    $Py = "$Release\.runtime\python.exe"

    Write-Host "[INFO] Installing dependencies into embedded runtime..."
    & $Py -m pip install --no-warn-script-location -r "$Release\requirements-win.txt"
    if ($LASTEXITCODE -ne 0) { throw "pip install (base) failed." }

    if (-not $Lite) {
        Write-Host "[INFO] Installing CUDA acceleration libraries..."
        & $Py -m pip install --no-warn-script-location -r "$Release\requirements-cuda-win.txt"
        if ($LASTEXITCODE -ne 0) { throw "pip install (CUDA) failed." }
    }

    Write-Host "[INFO] Verifying runtime imports..."
    & $Py -c "import PyQt6, faster_whisper, sounddevice, numpy, requests; print('RUNTIME_OK')"
    if ($LASTEXITCODE -ne 0) { throw "Runtime import verification failed." }
} finally {
    Pop-Location
}

# 5. Bundle Whisper medium model (Full only) — installed to %APPDATA% on first launch
if (-not $Lite -and -not $NoModel) {
    $ModelSrc  = "$env:APPDATA\VoxProse\whisper_models\models--Systran--faster-whisper-medium"
    $ModelDest = "$Release\bundled_models\models--Systran--faster-whisper-medium"
    if (Test-Path "$ModelSrc\snapshots") {
        Write-Host "[INFO] Bundling Whisper medium model..."
        robocopy $ModelSrc $ModelDest /E /XD .locks /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    } else {
        Write-Host "[WARN] Medium model not found at $ModelSrc — ZIP will download on first run."
    }
}

# 6. Include the launcher EXE (copy prebuilt, or compile with the built-in csc)
if (Test-Path "$ProjectRoot\VoxProse.exe") {
    Copy-Item "$ProjectRoot\VoxProse.exe" "$Release\VoxProse.exe"
    Write-Host "[INFO] Copied existing launcher EXE."
} else {
    $Csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if (-not (Test-Path $Csc)) { $Csc = "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe" }
    if (Test-Path $Csc) {
        Write-Host "[INFO] Compiling launcher EXE..."
        & $Csc /nologo /target:winexe /out:"$Release\VoxProse.exe" /win32icon:"$Release\assets\icon.ico" /r:System.Windows.Forms.dll "$Release\tools\launcher.cs"
    } else {
        Write-Host "[WARN] csc.exe not found — users will launch via run_voicetype.bat."
    }
}

# 7. Portable readme
$Notes = @"
聲成文 VoxProse — Windows 真可攜版 (v$Version)
=====================================================

【使用方式】
1. 把整個資料夾放到任何位置（硬碟、隨身碟皆可，建議路徑不含中文）
2. 雙擊 VoxProse.exe 即可使用（或 run_voicetype.bat）
3. 首次啟動會自動把隨附的辨識模型裝入 %APPDATA%\VoxProse（約需十幾秒）

【注意事項】
- 免安裝 Python、免網路（Full 版）；Lite 版、NoModel 版首次啟動需網路下載模型
- NoModel 版已含 CUDA 加速函式庫（與 Full 版相同），僅不隨附 medium 模型，體積較小
- 個人設定與詞庫存於 %APPDATA%\VoxProse，不在本資料夾內
- 有 NVIDIA 顯示卡自動使用 CUDA 加速，沒有則自動改用 CPU
- 桌面捷徑可執行 create_shortcut.ps1 建立（非必要）
"@
Set-Content -Path "$Release\可攜版說明.txt" -Value $Notes -Encoding UTF8

# 8. Normalize .bat to CRLF without BOM
Write-Host "[INFO] Normalizing line endings for .bat files..."
Get-ChildItem -Path $Release -Filter "*.bat" -Recurse | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    $content = $content -replace "`r`n", "`n" -replace "`n", "`r`n"
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($_.FullName, $content, $enc)
}

# 8.5. Remove app-source bytecode caches (e.g. left behind by a pre-zip smoke
# test). .runtime 內 pip 預編譯的 __pycache__ 刻意保留 — 加快首次啟動。
Get-ChildItem -Path $Release -Directory -Recurse -Filter "__pycache__" |
    Where-Object { $_.FullName -notlike "*\.runtime\*" } |
    Remove-Item -Recurse -Force

# 9. ZIP
#
# 不使用 Windows 內建 tar.exe 的 ZIP backend：它在 Windows 會經過系統 ANSI
# code page，且不一定替 entry name 設 UTF-8 flag。英文 GitHub runner 因此會
# 把中文檔名直接替換成 literal "?"，產出連 Expand-Archive 都無法解開的 ZIP。
# .NET ZipArchive 會為非 ASCII entry name 寫入 UTF-8 flag，並自動支援 ZIP64。
if ($SkipZip) {
    Write-Host "[INFO] -SkipZip: folder ready at $Release"
} else {
    Write-Host "[INFO] Compressing into $ZipFile (this may take a few minutes)..."
    $ZipFull = Join-Path $ProjectRoot $ZipFile
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $ArchiveStream = [System.IO.File]::Open(
        $ZipFull,
        [System.IO.FileMode]::Create,
        [System.IO.FileAccess]::Write,
        [System.IO.FileShare]::None
    )
    $Archive = $null
    try {
        $Archive = [System.IO.Compression.ZipArchive]::new(
            $ArchiveStream,
            [System.IO.Compression.ZipArchiveMode]::Create,
            $false,
            [System.Text.Encoding]::UTF8
        )
        $ReleaseParent = Split-Path $Release
        Get-ChildItem -LiteralPath $Release -File -Recurse | ForEach-Object {
            $RelativeName = $_.FullName.Substring($ReleaseParent.Length + 1).Replace("\", "/")
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $Archive,
                $_.FullName,
                $RelativeName,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    } finally {
        if ($null -ne $Archive) {
            $Archive.Dispose()
        } else {
            $ArchiveStream.Dispose()
        }
    }
    $SizeGB = [math]::Round((Get-Item $ZipFull).Length / 1GB, 2)
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "   Portable Release: $ZipFile ($SizeGB GB)" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
}
