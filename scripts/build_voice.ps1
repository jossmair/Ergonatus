$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
$voicePython=Join-Path (Get-Location) 'ergoai\voice\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $voicePython)) {throw 'Créer le venv vocal et installer ergoai/voice/requirements-lock.txt avant le build.'}
& $voicePython -m PyInstaller --noconfirm --clean --windowed --onedir --name ErgoVoice --distpath .package-voice --workpath .build-voice --specpath .build-voice --paths . --collect-all piper --collect-all onnxruntime --exclude-module pytest run_ergovoice.py
if ($LASTEXITCODE -ne 0) {throw 'Compilation vocale impossible.'}
Copy-Item -Path '.package-voice\ErgoVoice\*' -Destination ergoai\voice\runtime -Recurse -Force
