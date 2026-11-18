@echo off
rem Starts the cutting-room server (if it isn't already running) and opens the hub,
rem or a project's editor if a project id is passed:  "Open cutting room.bat" my-project
cd /d "%~dp0engine"
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://localhost:8770/api/projects | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  start "" pythonw serve.py
  timeout /t 2 /nobreak >nul
)
if "%~1"=="" (start "" http://localhost:8770/) else (start "" http://localhost:8770/p/%~1/)
