# create_shortcut_v83.ps1
# Use hexadecimal character codes to avoid encoding issues with Chinese characters in PS5.1
# "聲成文" = 0x8072, 0x6210, 0x6587
$ShortcutName = [char]0x8072 + [char]0x6210 + [char]0x6587
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "$ShortcutName.lnk"
$TargetFile = Join-Path $PSScriptRoot "run_voicetype.bat"
$IconLocation = Join-Path $PSScriptRoot "assets\icon.ico" 

Write-Host "[INFO] Ensuring Desktop Shortcut..." -ForegroundColor Cyan

try {
    $WScriptShell = New-Object -ComObject WScript.Shell
    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force
    }
    $Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
    # Prefer the native launcher EXE (no console window, no cmd encoding issues);
    # fall back to run_voicetype.bat when the EXE was not built.
    $ExeLauncher = Join-Path $PSScriptRoot "VoxProse.exe"
    if (Test-Path $ExeLauncher) {
        $Shortcut.TargetPath = $ExeLauncher
        $Shortcut.Arguments = ""
    } else {
        $Shortcut.TargetPath = "cmd.exe"
        $Shortcut.Arguments = "/c `"$TargetFile`""
    }
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.WindowStyle = 7 # Minimized
    $Shortcut.IconLocation = "$IconLocation,0"
    $Shortcut.Description = "VoxProse - AI Voice Typing"
    $Shortcut.Save()
    Write-Host "[SUCCESS] Shortcut created on Desktop: $ShortcutName" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $_" -ForegroundColor Red
    exit 1
}
