[Setup]
AppName=Kree AI
AppVersion=1.0.0
DefaultDirName={autopf}\Kree AI
DefaultGroupName=Kree AI
OutputDir=e:\Mark-XXX-main\Mark-XXX-main\dist
OutputBaseFilename=Kree_AI_Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=e:\Mark-XXX-main\Mark-XXX-main\assets\kree.ico
UninstallDisplayIcon={app}\Kree AI.exe

[Files]
Source: "e:\Mark-XXX-main\Mark-XXX-main\dist\Kree AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Kree AI"; Filename: "{app}\Kree AI.exe"
Name: "{autodesktop}\Kree AI"; Filename: "{app}\Kree AI.exe"

[Registry]
; Make Kree AI run automatically on Windows Startup in background mode
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Kree AI"; ValueData: """{app}\Kree AI.exe"" --background"; Flags: uninsdeletevalue

[Run]
; Launch Kree seamlessly in background after installation finishes without asking
Filename: "{app}\Kree AI.exe"; Parameters: "--background"; Description: "Launch Kree AI in Background"; Flags: nowait postinstall skipifsilent
