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
REM  Sin argumento, muestra un menu para elegir que vertical compilar. Con
REM  argumento (p. ej. "scripts\build_windows.bat repuestos"), compila esa
REM  vertical directamente sin preguntar (util para automatizar).
REM
REM  La version del ejecutable es la version GLOBAL del sistema, definida en un solo
REM  lugar (src\sistemashn\__init__.py::__version__). No es la version de la vertical
REM  ni se incrementa sola en cada build: para publicar una version nueva, se cambia
REM  __version__ a mano y se vuelve a correr este script.
REM
REM  Al terminar, la carpeta build\ en la raiz del proyecto SOLO contiene lo
REM  compilado: build\SistemasHN<Vertical><Version>.zip (el build mas reciente,
REM  listo para copiar a otra maquina y probar) y build\windows_release\ (la misma
REM  copia sin comprimir, ruta ESTABLE que usa installer\sistemashn.iss como
REM  fuente). Todo lo que "flet build" arma para compilar (el proyecto Flutter
REM  completo, sus paquetes y cachés) es un paso intermedio que este script borra
REM  al final desde una carpeta de trabajo FUERA de build\ (ver TRABAJO mas abajo)
REM  para no ensuciar la carpeta del proyecto con eso.
REM ===============================================================================

set VERTICAL=%~1
if not "%VERTICAL%"=="" goto :vertical_elegida

:menu
cls
echo ===============================================
echo   SistemasHN - Elegir vertical a compilar
echo ===============================================
echo  1. Repuestos
echo  0. Cancelar
echo ===============================================
set /p opcion=Elija una opcion:
if "%opcion%"=="1" set VERTICAL=repuestos & goto :vertical_elegida
if "%opcion%"=="0" exit /b 0
echo Opcion invalida.
pause
goto menu

:vertical_elegida
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
set RELEASE_DIR=%BUILD_DIR%\windows_release
set DESTINO=%BUILD_DIR%\%NOMBRE_SALIDA%.zip

REM TRABAJO: "flet build" siempre crea su propio proyecto Flutter completo (con todo
REM el SDK/paquetes/cache que eso implica, varios cientos de MB) en "<carpeta que se
REM le pasa>\build\flutter" -- no hay forma de configurar esa ruta con un parametro,
REM asi que el truco es pasarle como "carpeta del proyecto" una carpeta temporal
REM FUERA del repositorio: toda esa maquinaria intermedia queda ahi y nunca toca
REM nuestra carpeta build\ real.
set TRABAJO=%TEMP%\sistemashn-build-%VERTICAL%
set FLET_OUT=%TRABAJO%\salida

if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo ===============================================
echo   SistemasHN - Build de distribucion (Windows)
echo   Vertical: %VERTICAL_LABEL%     Version: %VERSION%
echo ===============================================
echo.

REM Carpeta de trabajo limpia en cada build, para no arrastrar restos de una
REM compilacion anterior (p. ej. un DLL que ya no corresponde).
if exist "%TRABAJO%" rmdir /s /q "%TRABAJO%"
mkdir "%TRABAJO%"

echo Copiando el proyecto a la carpeta de trabajo temporal...
REM Solo hace falta "pyproject.toml" (metadatos, dependencias, [tool.flet]) y "src\"
REM (path del programa segun [tool.flet.app]): copiar nada mas mantiene esto rapido.
mkdir "%TRABAJO%\proyecto"
copy /y pyproject.toml "%TRABAJO%\proyecto\" >nul
robocopy src "%TRABAJO%\proyecto\src" /e /xd __pycache__ /xf *.pyc >nul
if !ERRORLEVEL! geq 8 (
    echo.
    echo RESULTADO: FALLA al copiar el proyecto a la carpeta de trabajo ^(codigo !ERRORLEVEL!^)
    exit /b 1
)

echo Compilando con "flet build windows" (puede tardar varios minutos)...
"%FLET%" build windows --product "SistemasHN %VERTICAL_LABEL%" --build-version %VERSION% -o "%FLET_OUT%" "%TRABAJO%\proyecto"
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
    echo La carpeta de trabajo temporal NO se borro, para poder revisarla: %TRABAJO%
    exit /b 1
)

echo.
echo Copiando "!EXE_DIR!" a la ruta estable "%RELEASE_DIR%" (se sobrescribe)...
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
xcopy "!EXE_DIR!*" "%RELEASE_DIR%\" /e /i /y >nul
if !ERRORLEVEL! neq 0 (
    echo.
    echo RESULTADO: FALLA al copiar el resultado a "%RELEASE_DIR%" ^(codigo !ERRORLEVEL!^)
    exit /b !ERRORLEVEL!
)

echo.
echo Empaquetando "%RELEASE_DIR%" en "%DESTINO%" (se sobrescribe si ya existia)...
if exist "%DESTINO%" del /f /q "%DESTINO%"
powershell -NoProfile -Command "Compress-Archive -Path '%RELEASE_DIR%\*' -DestinationPath '%DESTINO%' -Force"
if !ERRORLEVEL! neq 0 (
    echo.
    echo RESULTADO: FALLA al comprimir el resultado ^(codigo !ERRORLEVEL!^)
    exit /b !ERRORLEVEL!
)

echo.
echo Limpiando la carpeta de trabajo temporal (%TRABAJO%)...
rmdir /s /q "%TRABAJO%" 2>nul

echo.
echo RESULTADO: OK
echo build\ solo contiene lo compilado:
echo   - Distribuible: %DESTINO%
echo   - Fuente estable para el instalador (installer\sistemashn.iss): %RELEASE_DIR%

endlocal
exit /b 0
