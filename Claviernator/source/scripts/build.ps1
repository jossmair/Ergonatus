$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
New-Item -ItemType Directory -Path docs/test-settings -Force | Out-Null
python -m pytest -q --basetemp docs/test-settings/build-tests
if ($LASTEXITCODE) { throw "Les tests ont échoué." }
python scripts/make_icon.py
if ($LASTEXITCODE) { throw "La création de l’icône a échoué." }
python -m PyInstaller --noconfirm Fortinatus.spec
if ($LASTEXITCODE) { throw "La compilation a échoué." }
python scripts/package_release.py
if ($LASTEXITCODE) { throw "La création de la distribution a échoué." }

