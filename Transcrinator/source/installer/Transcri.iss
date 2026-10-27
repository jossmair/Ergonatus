[Setup]
AppId={{49B2BEAF-8E76-4320-BDAE-3F4087DE4C08}
AppName=Transcrinator
AppVersion=1.3.17
AppPublisher=Transcrinator
DefaultDirName={localappdata}\Programs\Transcri
DefaultGroupName=Transcrinator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=Transcrinator-1.3.17-Setup
SetupIconFile=..\assets\transcri.ico
UninstallDisplayIcon={app}\Transcrinator.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "..\dist\Transcrinator-1.3.17\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Transcrinator"; Filename: "{app}\Transcrinator.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Transcrinator"; ValueData: """{app}\Transcrinator.exe"" --minimized"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Transcrinator.exe"; Parameters: "--show"; Flags: nowait skipifsilent

; User models/preferences are deliberately retained. No recursive user data deletion.
