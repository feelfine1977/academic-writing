@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Install on Windows.cmd first.
  pause
  exit /b 1
)
start "Academic Writing Lab" ".venv\Scripts\pythonw.exe" -X utf8 "%~dp0desktop.py"
