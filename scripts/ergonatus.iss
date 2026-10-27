#ifndef ReleaseRoot
#error ReleaseRoot required
#endif
[Setup]
AppId={{E5CE25D3-E597-4C66-A066-1B4A337CB765}
AppName=Ergonatus
AppVersion=2026.10.27
AppPublisher=Ergonatus
AppPublisherURL=https://github.com/jossmair/Ergonatus
DefaultDirName={localappdata}\Programs\Ergonatus
DefaultGroupName=Ergonatus
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.10240
OutputDir={#ReleaseRoot}\assets
OutputBaseFilename=Ergonatus-2026.10.27-Setup
SetupIconFile=..\assets\orbs\ergonatus.ico
UninstallDisplayIcon={app}\Hub\Ergonatus.exe
WizardStyle=modern
DisableProgramGroupPage=yes
Compression=zip/1
SolidCompression=no
DiskSpanning=yes
DiskSliceSize=1500000000
SlicesPerDisk=1
CloseApplications=no
RestartApplications=no
SetupLogging=yes
CreateUninstallRegKey=not IsSmokeTest
[Languages]
Name: french; MessagesFile: compiler:Languages\French.isl
[Tasks]
Name: desktopicon; Description: Créer un raccourci sur le Bureau; Flags: unchecked; Check: not IsSmokeTest
[Files]
Source: {#ReleaseRoot}\payload\Ergonatus\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: {userprograms}\Ergonatus; Filename: {app}\Hub\Ergonatus.exe; WorkingDir: {app}; Check: not IsSmokeTest
Name: {userdesktop}\Ergonatus; Filename: {app}\Hub\Ergonatus.exe; WorkingDir: {app}; Tasks: desktopicon; Check: not IsSmokeTest
[Run]
Filename: {app}\Hub\Ergonatus.exe; Description: Ouvrir Ergonatus; Flags: nowait postinstall skipifsilent
[Code]
function IsSmokeTest: Boolean;
begin
  Result := ExpandConstant('{param:TESTINSTALL|0}') = '1';
end;
