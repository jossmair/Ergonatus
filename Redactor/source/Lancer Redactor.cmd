@echo off
cd /d "%~dp0"
if exist "%~dp0dist\Redactor-0.2.1\Redactor.exe" (
  start "" "%~dp0dist\Redactor-0.2.1\Redactor.exe" --show --link-suite
  exit /b
)
if exist "%~dp0.venv\Scripts\pythonw.exe" (
  start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
  exit /b
)
echo Environnement absent. Executez scripts\install.ps1 avec PowerShell.
pause
