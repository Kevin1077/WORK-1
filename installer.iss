#define MyAppName "Étoffe Laundry"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Étoffe Laundry"
#define MyAppExeName "Étoffe Laundry.exe"

[Setup]
AppId={{Etoffe-Laundry-Management-System}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\Étoffe Laundry
DefaultGroupName={#MyAppName}

OutputDir=installer
OutputBaseFilename=Étoffe Laundry Setup

Compression=lzma
SolidCompression=yes

ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

WizardStyle=modern

UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\Étoffe Laundry\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"

Name: "{autodesktop}\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName}"; \
    Flags: nowait postinstall skipifsilent