$ErrorActionPreference='Stop'
$suiteDirectory=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $suiteDirectory
$pythonExecutable=Join-Path $suiteDirectory '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) { $pythonExecutable=Join-Path (Split-Path $suiteDirectory -Parent) 'Redactor\.venv\Scripts\python.exe' }
& $pythonExecutable scripts\make_icons.py
if ($LASTEXITCODE -ne 0) {throw 'Conversion des icônes impossible.'}
& $pythonExecutable -m PyInstaller --noconfirm --clean --distpath .package-satellites --workpath .build-satellites scripts\satellites.spec
if ($LASTEXITCODE -ne 0) {throw 'Compilation des satellites impossible.'}
& $pythonExecutable scripts\deploy_satellites.py
if ($LASTEXITCODE -ne 0) {throw 'Conditionnement des satellites impossible.'}
& $pythonExecutable -m PyInstaller --noconfirm --clean --windowed --onedir --name ErgoAI --distpath .package-service --workpath .build-service --specpath .build-service --paths . --collect-data llama_cpp --collect-binaries llama_cpp --hidden-import jinja2.ext --exclude-module pytest run_ergoai.py
if ($LASTEXITCODE -ne 0) {throw 'Compilation du moteur partagé impossible.'}
New-Item -ItemType Directory -Force ergoai\runtime | Out-Null
Copy-Item -Path '.package-service\ErgoAI\*' -Destination ergoai\runtime -Recurse -Force

& (Join-Path $PSScriptRoot 'build_proofreader.ps1')
if ($LASTEXITCODE -ne 0) {throw 'Compilation du moteur de correction impossible.'}

& (Join-Path $PSScriptRoot 'build_translation.ps1')
if ($LASTEXITCODE -ne 0) {throw 'Compilation du moteur de traduction impossible.'}

& (Join-Path $PSScriptRoot 'build_translation_voice.ps1')
if ($LASTEXITCODE -ne 0) {throw 'Compilation des voix Traductor impossible.'}
