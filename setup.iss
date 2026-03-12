[Setup]
AppName=VoiceType4TW
AppVersion=2.8.27
DefaultDirName={autopf}\VoiceType4TW
DefaultGroupName=VoiceType4TW
UninstallDisplayIcon={app}\VoiceType4TW.exe
Compression=lzma2/ultra64
SolidCompression=yes
OutputDir=.
OutputBaseFilename=VoiceType4TW_v2.8.27_Setup
SetupIconFile=assets\icon.png

[Files]
Source: "dist\VoiceType4TW\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\VoiceType4TW"; Filename: "{app}\VoiceType4TW.exe"
Name: "{commondesktop}\VoiceType4TW"; Filename: "{app}\VoiceType4TW.exe"

[Run]
Filename: "{app}\VoiceType4TW.exe"; Description: "Launch VoiceType4TW"; Flags: nowait postinstall skipifsilent
