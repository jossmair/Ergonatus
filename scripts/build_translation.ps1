$ErrorActionPreference='Stop'
$suiteDirectory=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $suiteDirectory
$pythonExecutable=Join-Path (Split-Path $suiteDirectory -Parent) 'Redactor/.venv/Scripts/python.exe'
& $pythonExecutable -m PyInstaller --noconfirm --distpath .package-translation --workpath .build-translation scripts/translation.spec
if ($LASTEXITCODE -ne 0) {throw 'Compilation du traducteur partagé impossible.'}
New-Item -ItemType Directory -Force ergoai/translation/runtime | Out-Null
Copy-Item -Path '.package-translation/ErgoTranslate/*' -Destination ergoai/translation/runtime -Recurse -Force
