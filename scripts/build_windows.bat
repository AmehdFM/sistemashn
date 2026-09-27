@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

REM ===============================================================================
REM  SistemasHN - Build de distribucion para Windows (flet build windows)
REM
REM  Uso:  scripts\build_windows.bat [vertical]
REM
REM  [vertical] es opcional (por defecto "repuestos"; hoy es la unica vertical con
REM  entrypoint propio en src\sistemashn\app\, ver src\main.py). Cuando exista otra
REM  vertical con su propio entrypoint, se agrega aqui su nombre "bonito" para el
REM  archivo de salida (ver bloque VERTICAL_LABEL mas abajo).
REM
REM  La version del ejecutable es la version GLOBAL del sistema, definida en un solo
REM  lugar (src\sistemashn\__init__.py::__version__). No es la version de la vertical
REM  ni se incrementa sola en cada build: para publicar una version nueva, se cambia
REM  __version__ a mano y se vuelve a correr este script.
REM
REM  Resultado: build\SistemasHN<Vertical><Version>.zip (se sobrescribe en cada build;
REM  la carpeta build\ en la raiz del proyecto es donde siempre queda el build mas
REM  reciente listo para copiar a otra maquina y probar).
REM ===============================================================================

set VERTICAL=%~1
if "%VERTICAL%"=="" set VERTICAL=repuestos

if /i "%VERTICAL%"=="repuestos" (
    set VERTICAL_LABEL=Repuestos
) else (
    echo Vertical desconocida: "%VERTICAL%".
    echo Verticales soportadas hoy: repuestos
    exit /b 1
)

set PY=evn\Scripts\python.exe
set FLET=evn\Scripts\flet.exe

if not exist "%PY%" (
    echo No se encontro el entorno virtual "evn".
    echo Cree el entorno primero ^(ver scripts\pruebas.bat, opcion 1^):
    echo.
    echo   py -3.14 -m venv evn
    echo   evn\Scripts\python.exe -m pip install -r requirements-dev.txt
    echo   evn\Scripts\python.exe -m pip install -e . --no-deps
    echo.
    exit /b 1
)

if not exist "%FLET%" (
    echo No se encontro "evn\Scripts\flet.exe". Verifique que flet este instalado en "evn".
    exit /b 1
)

REM La version es global del sistema: una sola fuente de verdad, no se toca aqui.
for /f "usebackq delims=" %%v in (`"%PY%" -c "from sistemashn import __version__; print(__version__)"`) do set VERSION=%%v
if "%VERSION%"=="" (
    echo No se pudo leer la version desde sistemashn.__version__.
    exit /b 1
)

set NOMBRE_SALIDA=SistemasHN%VERTICAL_LABEL%%VERSION%
set BUILD_DIR=build
set FLET_OUT=%BUILD_DIR%\_flet_out_%VERTICAL%
set DESTINO=%BUILD_DIR%\%NOMBRE_SALIDA%.zip

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo ===============================================
echo   SistemasHN - Build de distribucion (Windows)
echo   Vertical: %VERTICAL_LABEL%     Version: %VERSION%
echo ===============================================
echo.

REM Carpeta de trabajo de flet limpia en cada build, para no arrastrar restos de
REM una compilacion anterior (p. ej. un DLL que ya no corresponde).
if exist "%FLET_OUT%" rmdir /s /q "%FLET_OUT%"

echo Compilando con "flet build windows" (puede tardar varios minutos)...
"%FLET%" build windows --product "SistemasHN %VERTICAL_LABEL%" --build-version %VERSION% -o "%FLET_OUT%"
if !ERRORLEVEL! neq 0 (
    echo.
    echo RESULTADO: FALLA en "flet build windows" ^(codigo !ERRORLEVEL!^)
    exit /b !ERRORLEVEL!
)

REM El ejecutable final queda en una subcarpeta de "%FLET_OUT%" (la ruta exacta
REM depende de la version de Flet/Flutter, p. ej. algo como
REM "%FLET_OUT%\x64\runner\Release\sistemashn.exe"): se busca en vez de asumir la
REM ruta, para no romper el script si esa ruta interna cambia.
set EXE_DIR=
for /r "%FLET_OUT%" %%f in (sistemashn.exe) do set "EXE_DIR=%%~dpf"

if not defined EXE_DIR (
    echo.
    echo No se encontro "sistemashn.exe" dentro de "%FLET_OUT%" tras el build.
    echo Revise la salida de "flet build windows" arriba.
    exit /b 1
)

echo.
echo Empaquetando "!EXE_DIR!" en "%DESTINO%" (se sobrescribe si ya existia)...
if exist "%DESTINO%" del /f /q "%DESTINO%"
powershell -NoProfile -Command "Compress-Archive -Path '!EXE_DIR!*' -DestinationPath '%DESTINO%' -Force"
if !ERRORLEVEL! neq 0 (
    echo.
    echo RESULTADO: FALLA al comprimir el resultado ^(codigo !ERRORLEVEL!^)
    exit /b !ERRORLEVEL!
)

echo.
echo RESULTADO: OK
echo Listo para copiar a otra maquina y probar: %DESTINO%

endlocal
exit /b 0
