@echo off
cd /d "%~dp0"
if exist "dist\orbes-liees\Precisionator-1.0.7\Precisionator.exe" (
  start "" "dist\orbes-liees\Precisionator-1.0.7\Precisionator.exe"
) else if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "main.py"
) else (
  echo Lancez build.bat avec Python 3.12 x64 pour preparer Precisionator.
  pause
)
