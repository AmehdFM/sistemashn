@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0sistemashn.ps1" %*
set "result=%ERRORLEVEL%"
echo.
if not "%result%"=="0" echo El programa termino con error (codigo %result%).
pause
exit /b %result%
