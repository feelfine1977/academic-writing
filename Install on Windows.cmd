@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 or newer from https://www.python.org/downloads/windows/ first. Enable the Python launcher during setup.
  pause
  exit /b 1
)
py -3 install.py
pause
