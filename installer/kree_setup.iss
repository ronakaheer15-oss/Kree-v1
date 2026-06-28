; Kree AI — Inno Setup Installer Script
; Version: 0.1.0
; Run with: iscc "installer\kree_setup.iss"
; Requires: Inno Setup 6+ (free from https://jrsoftware.org/isinfo.php)

#define MyAppName "Kree AI"
#define MyAppVersion "0.9.0-beta.1"
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
Source: "..\dist\Kree AI\config\*"; DestDir: "{app}\config"; Flags: onlyifdoesntexist recursesubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  WV2Exists: Boolean;
  VCPPExists: Boolean;
begin
  Result := True;

  // Check WebView2
  WV2Exists := RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}') or
               RegKeyExists(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}');
  if not WV2Exists then
  begin
    MsgBox('Microsoft Edge WebView2 Runtime was not detected on your system.' + #13#10#13#10 +
           'Kree AI requires WebView2 for its UI to function. Please download and install it from Microsoft.', mbError, MB_OK);
  end;

  // Check VC++ 2015-2022
  VCPPExists := RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64');
  if not VCPPExists then
  begin
    MsgBox('Visual C++ 2015-2022 Redistributable (x64) was not detected.' + #13#10#13#10 +
           'Kree AI may fail to launch without it. Please install it from Microsoft.', mbError, MB_OK);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('Do you want to delete your Kree configurations, API keys, and logs?', mbConfirmation, MB_YESNO) = idYes then
    begin
      DelTree(ExpandConstant('{localappdata}\Kree'), True, True, True);
    end
    else
    begin
      DelTree(ExpandConstant('{localappdata}\Kree\cache'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\Kree\temp'), True, True, True);
    end;
  end;
end;
