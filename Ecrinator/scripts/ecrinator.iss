#ifndef AppVersion
#error AppVersion is required
#endif
[Setup]
AppId={{65175457-12AB-4978-8A24-CC847E2C2F99}
AppName=Écrinator
AppVersion={#AppVersion}
AppPublisher=Ergonatus
DefaultDirName={localappdata}\Programs\Ergonatus\Ecrinator
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.10240
DefaultGroupName=Ergonatus
OutputDir=..\dist
OutputBaseFilename=Ecrinator-{#AppVersion}-Setup
SetupIconFile=..\assets\ecrinator.ico
UninstallDisplayIcon={app}\Ecrinator.exe
UninstallDisplayName=Écrinator
WizardStyle=modern
DisableProgramGroupPage=yes
Compression=lzma2/max
SolidCompression=yes
CloseApplications=no
RestartApplications=no
SetupLogging=yes
VersionInfoVersion={#AppVersion}
VersionInfoDescription=Installation Écrinator — Ergonatus
CreateUninstallRegKey=not IsSmokeTest
[Languages]
Name: french; MessagesFile: compiler:Languages\French.isl
[Tasks]
Name: desktopicon; Description: Créer un raccourci sur le Bureau; Flags: unchecked; Check: not IsSmokeTest
[Files]
Source: ..\runtime\Ecrinator.exe; DestDir: {app}; Flags: ignoreversion
Source: ..\licenses\LICENCES.txt; DestDir: {app}; Flags: ignoreversion
Source: ..\LIRE-MOI.txt; DestDir: {app}; Flags: ignoreversion
[Icons]
Name: {userprograms}\Ergonatus\Écrinator; Filename: {app}\Ecrinator.exe; WorkingDir: {app}; Check: not IsSmokeTest
Name: {userdesktop}\Écrinator; Filename: {app}\Ecrinator.exe; WorkingDir: {app}; Tasks: desktopicon; Check: not IsSmokeTest
[Run]
Filename: {app}\Ecrinator.exe; Description: Ouvrir Écrinator; Flags: nowait postinstall skipifsilent
[Code]
function IsSmokeTest: Boolean;
begin
  Result := ExpandConstant('{param:TESTINSTALL|0}') = '1';
end;
