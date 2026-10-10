; ============================================================
;  闲鱼超级管家 - 安装程序脚本（Inno Setup 6）
;
;  编译命令（在项目根目录）:
;    .workbuddy\innosetup\app\ISCC.exe packaging\installer.iss
;  产物:
;    release\XianyuSuperButler-Setup-3.2.0.exe
;
;  前置要求：先运行 packaging/assemble.py 生成干净的 release 目录。
; ============================================================

#define MyAppName "闲鱼超级管家"
#define MyAppVersion "3.2.0"
#define MyAppPublisher "XianyuSuperButler"
#define MyAppExeName "闲鱼超级管家.exe"

[Setup]
AppId={{A7B3C9E1-5F2D-4E8A-9C1B-3D6F8E2A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\XianyuSuperButler
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=XianyuSuperButler-Setup-3.2.0
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: checkedonce

[Files]
Source: "..\release\xianyu-super-butler\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "logs\*,data\*,backups\*,realtime.log,*.log"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

; 说明：data / logs / backups 为用户运行期生成的数据，卸载时默认保留，
;       重装后可继续使用原有数据。
