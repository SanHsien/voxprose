# create_shortcut_v83.ps1
# Use hexadecimal character codes to avoid encoding issues with Chinese characters in PS5.1
# "嘴炮輸入法" = 0x5634, 0x70AE, 0x8F38, 0x5165, 0x6CD5
$ShortcutName = [char]0x5634 + [char]0x70AE + [char]0x8F38 + [char]0x5165 + [char]0x6CD5
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
    $Shortcut.TargetPath = "cmd.exe"
    $Shortcut.Arguments = "/c `"$TargetFile`""
    $Shortcut.WorkingDirectory = $PSScriptRoot
    $Shortcut.WindowStyle = 7 # Minimized
    $Shortcut.IconLocation = "$IconLocation,0"
    $Shortcut.Description = "VoiceType4TW - AI Voice Typing"
    $Shortcut.Save()
    Write-Host "[SUCCESS] Shortcut created on Desktop: $ShortcutName" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to create shortcut: $_" -ForegroundColor Red
    exit 1
}
