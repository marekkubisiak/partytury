; Instalator programu Partytury (Inno Setup)
#define AppVer "1.1"

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

[Registry]
; "Otwórz za pomocą -> Partytury" dla plików PDF (bez zmiany domyślnego programu PDF)
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "Partytury.pdf"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Partytury.pdf"; ValueType: string; ValueName: ""; ValueData: "PDF z partiami"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Partytury.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Partytury.exe,0"
Root: HKA; Subkey: "Software\Classes\Partytury.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Partytury.exe"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\Partytury.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\Partytury.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Partytury.exe"" ""%1"""

[Run]
Filename: "{app}\Partytury.exe"; Description: "{cm:LaunchProgram,Partytury}"; Flags: nowait postinstall skipifsilent
