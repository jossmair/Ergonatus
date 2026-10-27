$ErrorActionPreference = 'Stop'
$suiteDirectory = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $suiteDirectory
$pythonExecutable = Join-Path $suiteDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    $pythonExecutable = Join-Path (Split-Path $suiteDirectory -Parent) 'Redactor\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Créer .venv et installer requirements-dev.txt.' }
& $pythonExecutable scripts\make_icons.py
& $pythonExecutable -m PyInstaller --noconfirm --clean --windowed --onedir --name Ergonatus --icon (Join-Path $suiteDirectory 'assets\orbs\ergonatus.ico') --distpath .package --workpath .build --specpath .build --paths . --exclude-module llama_cpp --exclude-module numpy run_ergonatus.py
if ($LASTEXITCODE -ne 0) { throw 'Compilation impossible.' }
Copy-Item -Path '.package\Ergonatus\*' -Destination 'Hub' -Recurse -Force
Write-Output 'Exécutable : Hub\Ergonatus.exe. Conserver tout le dossier Ergonatus pour la livraison.'
