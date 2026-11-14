@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\setup.ps1"
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" "scripts\start.py" --local --backend matlab-engine
:failed
pause
