; Instalator programu Partytury (Inno Setup)
#define AppVer "1.0"

[Setup]
AppId={{77264ab4-ec60-4d6b-8d94-167fc2b6005a}
AppName=Partytury
AppVersion={#AppVer}
AppVerName=Partytury {#AppVer}
AppPublisher=Partytury
DefaultDirName={autopf}\Partytury
DefaultGroupName=Partytury
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=Partytury-setup
SetupIconFile=program\partytury.ico
UninstallDisplayIcon={app}\Partytury.exe
UninstallDisplayName=Partytury
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Partytury\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Partytury"; Filename: "{app}\Partytury.exe"
Name: "{autodesktop}\Partytury"; Filename: "{app}\Partytury.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Partytury.exe"; Description: "{cm:LaunchProgram,Partytury}"; Flags: nowait postinstall skipifsilent
