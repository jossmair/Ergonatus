@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto environment_ready
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -m venv .venv
) else (
  python -c "import sys; assert sys.version_info[:2] == (3,12), 'Python 3.12 x64 requis'"
  if errorlevel 1 goto failed
  python -m venv .venv
)
if errorlevel 1 goto failed
:environment_ready
set "PRECISIONATOR_PYTHON=%~dp0.venv\Scripts\python.exe"
"%PRECISIONATOR_PYTHON%" -c "import sys,struct; assert sys.version_info[:2] == (3,12) and struct.calcsize('P') == 8, 'Python 3.12 x64 requis'"
if errorlevel 1 goto failed
"%PRECISIONATOR_PYTHON%" -m pip install -r requirements-dev.txt
if errorlevel 1 goto failed
"%PRECISIONATOR_PYTHON%" scripts\prepare_assets.py
if errorlevel 1 goto failed
"%PRECISIONATOR_PYTHON%" -m pytest -q
if errorlevel 1 goto failed
"%PRECISIONATOR_PYTHON%" -m PyInstaller --noconfirm Precisionator.spec
if errorlevel 1 goto failed
"%PRECISIONATOR_PYTHON%" scripts\package_release.py
if errorlevel 1 goto failed
echo.
echo Distribution : dist\Precisionator-1.0.7\Precisionator.exe
exit /b 0
:failed
echo.
echo Echec de compilation. Voir le message ci-dessus.
exit /b 1
