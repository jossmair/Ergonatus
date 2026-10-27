$ErrorActionPreference='Stop'
$suiteDirectory=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $suiteDirectory
$pythonExecutable=Join-Path (Split-Path $suiteDirectory -Parent) 'Redactor/.venv/Scripts/python.exe'
& $pythonExecutable -m PyInstaller --noconfirm --distpath .package-proofreader --workpath .build-proofreader scripts/proofreader.spec
if ($LASTEXITCODE -ne 0) {throw 'Compilation du correcteur partagé impossible.'}
New-Item -ItemType Directory -Force ergoai/proofreading/runtime | Out-Null
Copy-Item -Path '.package-proofreader/ErgoProofread/*' -Destination ergoai/proofreading/runtime -Recurse -Force
