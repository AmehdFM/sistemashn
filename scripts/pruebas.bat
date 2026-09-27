@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."

REM Lista de pruebas de la ultima fase cerrada. Actualizar esta variable al cerrar cada fase
REM con las carpetas/archivos nuevos de esa fase (hoy: Fase A, esquema de base de datos).
set ULTIMA_FASE_TESTS=tests\core\db\test_schema_matches_models.py

set PY=evn\Scripts\python.exe

if not exist "%PY%" (
    echo No se encontro el entorno virtual "evn".
    echo Para crearlo, ejecute desde la raiz del repositorio:
    echo.
    echo   py -3.14 -m venv evn
    echo   evn\Scripts\python.exe -m pip install -r requirements-dev.txt
    echo   evn\Scripts\python.exe -m pip install -e . --no-deps
    echo.
    exit /b 1
)

if not exist "test-results" mkdir "test-results"

:menu
cls
echo ===============================================
echo   SistemasHN - Menu de pruebas
echo ===============================================
echo  1. Instalar/actualizar dependencias (requirements-dev + pip install -e . --no-deps)
echo  2. Suite completa (pytest -q)
echo  3. Paso a paso: cada archivo de prueba por separado
echo  4. Solo Core           (tests\core)
echo  5. Solo Comercial      (tests\comercial)
echo  6. Solo Repuestos      (tests\repuestos)
echo  7. App/arquitectura/tools (tests\app tests\test_architecture.py tests\tools tests\scripts)
echo  8. Pruebas de la ULTIMA fase (%ULTIMA_FASE_TESTS%)
echo  9. Ruff (check + format --check)
echo 10. Migraciones: alembic upgrade head sobre una base temporal y prueba de esquema
echo 11. Abrir la app con datos de prueba (.dev-data\manual)
echo  0. Salir
echo ===============================================
set /p opcion=Elija una opcion:

if "%opcion%"=="1" goto instalar
if "%opcion%"=="2" goto suite
if "%opcion%"=="3" goto pasoapaso
if "%opcion%"=="4" goto core
if "%opcion%"=="5" goto comercial
if "%opcion%"=="6" goto repuestos
if "%opcion%"=="7" goto arquitectura
if "%opcion%"=="8" goto ultimafase
if "%opcion%"=="9" goto ruff
if "%opcion%"=="10" goto migraciones
if "%opcion%"=="11" goto abrirapp
if "%opcion%"=="0" goto fin
echo Opcion invalida.
pause
goto menu

:sello_tiempo
REM Genera un sello de fecha/hora seguro para nombre de archivo (sin caracteres invalidos).
set "SELLO=%date%_%time%"
set "SELLO=%SELLO: =0%"
set "SELLO=%SELLO:/=-%"
set "SELLO=%SELLO::=-%"
set "SELLO=%SELLO:.=-%"
exit /b 0

:instalar
call :sello_tiempo
echo Instalando/actualizando dependencias...
powershell -NoProfile -Command "& { & '%PY%' -m pip install -r requirements-dev.txt } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !ERRORLEVEL! neq 0 (
    echo RESULTADO: FALLA ^(codigo !ERRORLEVEL!^)
    pause
    goto menu
)
powershell -NoProfile -Command "& { & '%PY%' -m pip install -e . --no-deps } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt' -Append"
type "test-results\ultimo.txt" > "test-results\%SELLO%.txt"
if !ERRORLEVEL! equ 0 (
    echo RESULTADO: OK
) else (
    echo RESULTADO: FALLA ^(codigo !ERRORLEVEL!^)
)
pause
goto menu

:suite
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (
    echo RESULTADO: OK
) else (
    echo RESULTADO: FALLA ^(codigo !RC!^)
)
pause
goto menu

:pasoapaso
call :sello_tiempo
set /p detener=Detenerse en cada falla? (S/N):
set OKCOUNT=0
set FALLACOUNT=0
set FALLADOS=
echo Ejecutando cada archivo de prueba por separado... > "test-results\ultimo.txt"
for /r tests %%f in (test_*.py) do (
    echo.
    echo --- %%f ---
    echo. >> "test-results\ultimo.txt"
    echo --- %%f --- >> "test-results\ultimo.txt"
    powershell -NoProfile -Command "& { & '%PY%' -m pytest -q '%%f' } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt' -Append"
    if !ERRORLEVEL! equ 0 (
        echo [OK] %%f
        set /a OKCOUNT+=1
    ) else (
        echo [FALLA] %%f
        set /a FALLACOUNT+=1
        set FALLADOS=!FALLADOS! %%f
        if /i "!detener!"=="S" pause
    )
)
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
echo.
echo Total OK: !OKCOUNT!    Total FALLA: !FALLACOUNT!
if !FALLACOUNT! gtr 0 (
    echo Archivos que fallaron:!FALLADOS!
    echo RESULTADO: FALLA ^(codigo !FALLACOUNT!^)
) else (
    echo RESULTADO: OK
)
pause
goto menu

:core
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q tests\core } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:comercial
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q tests\comercial } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:repuestos
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q tests\repuestos } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:arquitectura
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q tests\app tests\test_architecture.py tests\tools tests\scripts } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:ultimafase
call :sello_tiempo
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q %ULTIMA_FASE_TESTS% } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:ruff
call :sello_tiempo
echo --- ruff check --- > "test-results\ultimo.txt"
powershell -NoProfile -Command "& { & '%PY%' -m ruff check src tests tools } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt' -Append"
set RC1=!ERRORLEVEL!
echo. >> "test-results\ultimo.txt"
echo --- ruff format --check --- >> "test-results\ultimo.txt"
powershell -NoProfile -Command "& { & '%PY%' -m ruff format --check src tests tools } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt' -Append"
set RC2=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC1! equ 0 if !RC2! equ 0 (
    echo RESULTADO: OK
) else (
    echo RESULTADO: FALLA ^(codigo check=!RC1! format=!RC2!^)
)
pause
goto menu

:migraciones
call :sello_tiempo
REM No existe una interfaz CLI custom de alembic en tools\; se usan las pruebas de
REM migraciones y esquema, que ya montan una base temporal y validan contra los modelos.
powershell -NoProfile -Command "& { & '%PY%' -m pytest -q tests\core\db\test_migrations.py tests\core\db\test_schema_matches_models.py } 2>&1 | Tee-Object -FilePath 'test-results\ultimo.txt'"
set RC=!ERRORLEVEL!
copy /y "test-results\ultimo.txt" "test-results\%SELLO%.txt" >nul
if !RC! equ 0 (echo RESULTADO: OK) else (echo RESULTADO: FALLA ^(codigo !RC!^))
pause
goto menu

:abrirapp
REM Abre la app de escritorio con datos de prueba aislados en .dev-data\manual.
"%PY%" src\main.py --data-dir .dev-data\manual
pause
goto menu

:fin
endlocal
exit /b 0
