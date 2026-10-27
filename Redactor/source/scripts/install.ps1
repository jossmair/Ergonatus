param([string]$Python312 = '', [switch]$Offline, [switch]$Dev)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (-not $Python312) {
        $candidates = @(
            (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
            (Join-Path $root '..\Precisionator\.tools\python312\tools\python.exe'),
            'C:\Program Files\Python312\python.exe'
        )
        $Python312 = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if (-not $Python312) { throw 'Installez Python 3.12 x64 ou indiquez -Python312 chemin\python.exe.' }
    & $Python312 -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 requis"'
    if ($LASTEXITCODE) { throw 'Python 3.12 requis.' }
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        & $Python312 -m venv --without-pip .venv
        if ($LASTEXITCODE) { throw 'Création de l’environnement impossible.' }
    }
    & $python -c 'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("pip") else 1)'
    if ($LASTEXITCODE) {
        $bootstrap = Join-Path $root 'vendor\wheels\pip-25.2-py3-none-any.whl'
        if (-not (Test-Path -LiteralPath $bootstrap)) { throw 'Wheel pip de bootstrap absente de vendor\wheels.' }
        $previousPythonPath = $env:PYTHONPATH
        try {
            $env:PYTHONPATH = $bootstrap
            & $python -m pip install --no-index --find-links vendor\wheels pip==25.2
            if ($LASTEXITCODE) { throw 'Installation du bootstrap pip impossible.' }
        } finally { $env:PYTHONPATH = $previousPythonPath }
    }
    $requirements = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
    if ($Offline) {
        & $python -m pip install --no-index --find-links vendor\wheels -r $requirements -c requirements-lock.txt
    } else {
        & $python -m pip install --find-links vendor\wheels -r $requirements -c requirements-lock.txt
    }
    if ($LASTEXITCODE) { throw 'Installation incomplète. Vérifiez le réseau, la place disque ou les wheels locales.' }
    Write-Host 'Redactor est prêt. Lancez « Lancer Redactor.cmd ».'
    Write-Host 'Aucun modèle téléchargé par ce script. scripts\download_models.py exige --consent.'
} finally { Pop-Location }
