$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Exécutez scripts\install.ps1 avant de compiler.' }
    & $python -m compileall -q app main.py
    if ($LASTEXITCODE) { throw 'Erreur Python : compilation du programme annulée.' }
    & $python scripts\qa_snapshot.py
    if ($LASTEXITCODE) { throw 'Vérification visuelle échouée.' }
    & $python -m PyInstaller --noconfirm Redactor.spec
    if ($LASTEXITCODE) { throw 'Packaging échoué.' }
    Copy-Item -LiteralPath 'README.md' -Destination 'dist\Redactor-0.4.1\README.md'
    Copy-Item -LiteralPath 'THIRD_PARTY_NOTICES.md' -Destination 'dist\Redactor-0.4.1\THIRD_PARTY_NOTICES.md'
    Write-Host 'Programme : dist\Redactor-0.4.1\Redactor.exe'
    Write-Host 'Les modèles restent dans models et ne sont pas inclus dans le programme.'
} finally { Pop-Location }
