; Kree AI — Inno Setup Installer Script
; Version: 0.1.0
; Run with: iscc "installer\kree_setup.iss"
; Requires: Inno Setup 6+ (free from https://jrsoftware.org/isinfo.php)

#define MyAppName "Kree AI"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Kree"
#define MyAppExeName "Kree AI.exe"
#define MyAppURL "https://github.com/your-repo/Kree"

[Setup]
AppId={{A3F8E2C1-7D4B-4E6A-9C5F-2B8D1A0E3F7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\release
OutputBaseFilename=Kree-AI-Setup-v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
PrivilegesRequired=lowest
SetupIconFile=..\assets\kree.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; Bundle the entire PyInstaller dist folder
Source: "..\dist\Kree AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Include the README
Source: "..\README-INSTALL.txt"; DestDir: "{app}"; Flags: ignoreversion

; IMPORTANT: Preserve user config on upgrade — never overwrite these
Source: "..\dist\Kree AI\config\*"; DestDir: "{app}\config"; Flags: onlyifdoesntexist recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
