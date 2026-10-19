; Compile only the generated installer-entry.iss from build.py preparation.
; No compiler, installer, upgrade or signature acceptance is asserted by source.
#ifndef PreparedInputs
  #error Use build.py --source-commit <full SHA> --prepare-installer first.
#endif
#include PreparedInputs
#ifndef MyAppVersion
  #error Prepared version from the frozen product source is required.
#endif
#ifndef VerifiedSourceCommit
  #error A verified source commit is required.
#endif
#ifndef VerifiedManifestSha256
  #error A verified bundle manifest is required.
#endif
#ifndef VerifiedFilesInclude
  #error A verified explicit file inventory is required.
#endif
#ifndef VerifiedOutputDir
  #error An explicit preparation output directory is required.
#endif

#define MyAppName "Método Base"
#define MyAppExeName "MetodoBase.exe"

[Setup]
AppId={{8A2F4E7B-3C9D-4B1A-A5E6-7F8D9C0B2E3A}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher=MetodoBase
AppComments=Source {#VerifiedSourceCommit}; manifest {#VerifiedManifestSha256}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UsePreviousAppDir=yes
DisableProgramGroupPage=yes
OutputDir={#VerifiedOutputDir}
OutputBaseFilename=MetodoBaseSetup_v{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
; Preserve the previous installer registry/directory mode for upgrades.
ArchitecturesInstallIn64BitMode=
MinVersion=10.0
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
#include VerifiedFilesInclude

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; No [Run] auto-start and no [UninstallDelete] of local data. Unknown data
; under the legacy installation directory is retained, not silently migrated.
