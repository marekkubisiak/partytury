; Instalator programu PartiMaster (Inno Setup)
#define AppName "PartiMaster"
#define AppVer "1.3"
#define AppAuthor "Marek Kubisiak"

[Setup]
AppId={{77264ab4-ec60-4d6b-8d94-167fc2b6005a}
AppName={#AppName}
AppVersion={#AppVer}
AppVerName={#AppName} {#AppVer} – {#AppAuthor}
AppPublisher={#AppAuthor}
AppCopyright=© {#AppAuthor}
VersionInfoCompany={#AppAuthor}
VersionInfoDescription={#AppName} – porządkowanie partii i partytur
DefaultDirName={autopf}\{#AppName}
UsePreviousAppDir=no
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=Output
OutputBaseFilename=PartiMaster-setup
SetupIconFile=program\partytury.ico
UninstallDisplayIcon={app}\PartiMaster.exe
UninstallDisplayName={#AppName} – {#AppAuthor}
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

[InstallDelete]
; sprzątanie po poprzedniej nazwie programu ("Partytury")
Type: files; Name: "{autoprograms}\Partytury.lnk"
Type: files; Name: "{autodesktop}\Partytury.lnk"
Type: filesandordirs; Name: "{autopf}\Partytury"

[Files]
Source: "dist\PartiMaster\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\PartiMaster.exe"; Comment: "{#AppName} – {#AppAuthor}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\PartiMaster.exe"; Tasks: desktopicon; Comment: "{#AppName} – {#AppAuthor}"

[Registry]
; usunięcie wpisów poprzedniej wersji
Root: HKA; Subkey: "Software\Classes\Applications\Partytury.exe"; ValueType: none; Flags: deletekey
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: none; ValueName: "Partytury.pdf"; Flags: deletevalue
Root: HKA; Subkey: "Software\Classes\Partytury.pdf"; ValueType: none; Flags: deletekey
; "Otwórz za pomocą -> PartiMaster" dla plików PDF (bez zmiany domyślnego programu PDF)
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "PartiMaster.pdf"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\PartiMaster.pdf"; ValueType: string; ValueName: ""; ValueData: "PDF z partiami (PartiMaster)"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\PartiMaster.pdf\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\PartiMaster.exe,0"
Root: HKA; Subkey: "Software\Classes\PartiMaster.pdf\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PartiMaster.exe"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\PartiMaster.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName} – {#AppAuthor}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\PartiMaster.exe\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\PartiMaster.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PartiMaster.exe"" ""%1"""

[Run]
Filename: "{app}\PartiMaster.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
