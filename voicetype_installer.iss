; VoxProse 專業安裝程式腳本 (Inno Setup)
; 創辦人視角：提供極速、穩定的安裝體驗

#define MyAppName "VoxProse"
#define MyAppVersion "3.2.0"
#define MyAppPublisher "jfamily"
#define MyAppURL "https://github.com/SanHsien/voxprose"
#define MyAppExeName "run_voicetype.bat"
#define MyIcon "assets\icon.ico"

[Setup]
; 2026-07-21: 品牌改名為 VoxProse，換發新 AppId（等同新程式，舊版不會被升級
; 覆蓋）。本專案無既有安裝基礎（維護者從未安裝過任何版本），可接受；決策見
; docs/DECISIONS.md。
AppId={{C3912B98-0808-4B52-84F5-F5BB7A040B9A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; 創辦人偏好：簡潔、專業的安裝介面
OutputBaseFilename=ShengChengWen-Windows-Setup-v3.2
SetupIconFile={#MyIcon}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; 如果您有安裝繁體中文語言包，可以取消註解下一行
Name: "chinesetraditional"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 複製所有必要的原始碼與資源 (排除 logs, venv, .git 以及測試開發檔案)
Source: "*"; DestDir: "{app}"; Excludes: ".git,venv,.runtime,archive,__pycache__,.aicore,dist,build,output,node_modules,memory,stats,test_*.py,main2.py,debug_test.py,self_check.py,diagnose_mic.py,import_check.py,tiny.py,build_*.py,post_build_fix*.py,release_win.ps1,create_shortcut.ps1,*.log,*.txt,*.patch,boot_*.txt,err*.txt,out*.txt,*.zip,AI_MEMORY.md,INTERNAL_TODO.md,HANDOVER.md,MIGRATION_GUIDE.md,VERSIONS.md,*.command"
Source: "actions\*"; DestDir: "{app}\actions"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "audio\*"; DestDir: "{app}\audio"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "hotkey\*"; DestDir: "{app}\hotkey"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "llm\*"; DestDir: "{app}\llm"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "soul\*"; DestDir: "{app}\soul"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "stats\*"; DestDir: "{app}\stats"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "stt\*"; DestDir: "{app}\stt"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "utils\*"; DestDir: "{app}\utils"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "vocab\*"; DestDir: "{app}\vocab"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIcon}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyIcon}"; Tasks: desktopicon

[Run]
; 重要：安裝完成後自動執行環境設定 (檢查 Python, 建立 venv)
; 使用 /silent 旗標避免安裝過程中斷，但開啟控制台讓用戶知道進度
Filename: "{app}\setup_win.bat"; Parameters: "/silent"; Description: "正在初始化 AI 運行環境 (這可能需要幾分鐘)..."; Flags: postinstall runascurrentuser

[UninstallRun]
; 移除時的可選清理動作 (目前保留用戶資料以防誤刪)

[Code]
// 未來可加入檢查系統是否已安裝 Python 3.12 的 Pascal Script 邏輯
