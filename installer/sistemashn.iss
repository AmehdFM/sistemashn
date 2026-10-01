; SistemasHN Repuestos - Instalador (Inno Setup)
;
; No se compiló ni se probó en este entorno (requiere Inno Setup en Windows, igual que
; el resto del empaquetado de la Fase 6 documentado en
; docs/superpowers/plans/fase-6-operacion-entrega.md, T6.6). El propietario lo compila
; y prueba en su PC Windows con Inno Setup 6.
;
; Requisitos antes de compilar este script:
;   1. powershell -File scripts\dev.ps1 build -> deja el programa en build\windows_release\
;   2. scripts\build_updater.bat        -> deja el updater listo en build\updater\updater.exe
;   3. Abrir este archivo con el compilador de Inno Setup (o "iscc sistemashn.iss").
;
; La versión que se muestra al usuario (AppVersion) se lee de VERSION_APP más abajo:
; actualícela a mano junto con sistemashn.__version__ antes de compilar un instalador
; para publicar (no hay forma de leer Python desde Inno Setup sin un paso previo, así
; que esta constante es la única fuente de verdad DENTRO de este script; debe coincidir
; con src\sistemashn\__init__.py::__version__ en el momento de compilar).

#define AppName "SistemasHN Repuestos"
#define AppPublisher "Elements System"
#define VERSION_APP "0.1.0"
#define AppExeName "sistemashn.exe"

; Rutas relativas a la ubicación de este .iss (installer\), es decir la raíz del
; repositorio es un nivel arriba.
#define SourceRelease "..\build\windows_release"
#define SourceUpdater "..\build\updater\updater.exe"

[Setup]
AppId={{B6C9C9B6-6E9E-4C2A-9A9E-6B7B8B6B6B6B}
AppName={#AppName}
AppVersion={#VERSION_APP}
AppPublisher={#AppPublisher}
; Instala en Archivos de Programa, como cualquier programa de escritorio normal.
DefaultDirName={autopf}\SistemasHN\Repuestos
DefaultGroupName=SistemasHN
DisableProgramGroupPage=yes
; Un solo instalador de 64 bits (coincide con "flet build windows", x64 únicamente).
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputBaseFilename=SistemasHNRepuestos-{#VERSION_APP}-setup
OutputDir=..\build
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Nunca desinstala los datos del negocio (ver sección [UninstallDelete] más abajo:
; deliberadamente NO se borra %LOCALAPPDATA%\SistemasHN, ver core/db/engine.py).
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; Todo el contenido de "flet build windows" (el .exe, el runtime de Flutter/Python
; embebido, y los recursos): se copia tal cual, sin filtrar nada.
Source: "{#SourceRelease}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; El updater (T6.3) va junto al programa principal: la app lo invoca por ruta relativa
; a su propia carpeta de instalación cuando aplica una actualización.
Source: "{#SourceUpdater}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName} ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Deliberadamente vacío: desinstalar SOLO quita el programa (esta sección existe
; nada más para dejar constancia de la decisión). Los datos del negocio viven en
; %LOCALAPPDATA%\SistemasHN\repuestos (ver core/db/engine.py::data_dir) y Inno Setup
; nunca toca esa carpeta porque no está listada en [Files]/[Dirs] ni aquí.
