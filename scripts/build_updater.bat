@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

REM ===============================================================================
REM  SistemasHN - Empaquetado del proceso updater (PyInstaller onefile)
REM
REM  Uso:  scripts\build_updater.bat
REM
REM  El updater es un ejecutable APARTE del programa principal (ver T6.3 en
REM  docs\superpowers\plans\fase-6-operacion-entrega.md): la app principal lo invoca
REM  para aplicar un paquete de actualizacion ya validado y descargado, y del cual
REM  la app ya se despidio (cierra antes de que el updater reemplace sus archivos).
REM
REM  Resultado: build\updater\updater.exe (se sobrescribe en cada build). El
REM  instalador (installer\sistemashn.iss) espera encontrarlo ahi para incluirlo
REM  junto al programa principal.
REM ===============================================================================

set PY=evn\Scripts\python.exe

if not exist "%PY%" (
    echo No se encontro el entorno virtual "evn".
    echo Cree el entorno primero ^(ver scripts\pruebas.bat, opcion 1^):
    echo.
    echo   py -3.14 -m venv evn
    echo   evn\Scripts\python.exe -m pip install -r requirements-dev.txt
    echo   evn\Scripts\python.exe -m pip install -e . --no-deps
    echo.
    pause
    exit /b 1
)

if not exist "src\updater_main.py" (
    echo No se encontro "src\updater_main.py" ^(entrypoint del updater, T6.3^).
    pause
    exit /b 1
)

set BUILD_DIR=build
set DIST_DIR=%BUILD_DIR%\updater
REM Cache/spec de PyInstaller: solo son un paso intermedio, se arman FUERA de build\
REM (igual que el proyecto Flutter temporal de build_windows.bat) para que build\ solo
REM termine con updater.exe, y se borran al final.
set WORK_DIR=%TEMP%\sistemashn-build-updater

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"

echo ===============================================
echo   SistemasHN - Build del updater (PyInstaller)
echo ===============================================
echo.

REM --onefile: un solo .exe, sin carpeta de dependencias aparte, para copiarlo junto
REM al programa principal sin arrastrar mas archivos de los necesarios.
"%PY%" -m PyInstaller --onefile --name updater --distpath "%DIST_DIR%" --workpath "%WORK_DIR%" --specpath "%WORK_DIR%" src\updater_main.py
if !ERRORLEVEL! neq 0 (
    echo.
    echo RESULTADO: FALLA en PyInstaller ^(codigo !ERRORLEVEL!^)
    pause
    exit /b !ERRORLEVEL!
)

if not exist "%DIST_DIR%\updater.exe" (
    echo.
    echo No se encontro "%DIST_DIR%\updater.exe" tras el build.
    pause
    exit /b 1
)

rmdir /s /q "%WORK_DIR%" 2>nul

echo.
echo RESULTADO: OK
echo build\updater\ solo contiene lo compilado: %DIST_DIR%\updater.exe

pause
endlocal
exit /b 0
