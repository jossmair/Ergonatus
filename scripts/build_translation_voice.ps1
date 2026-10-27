$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
$voicePython=Join-Path (Get-Location) 'ergoai\voice\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $voicePython)) {throw 'Créer le venv vocal et installer ergoai/voice/requirements-lock.txt avant le build.'}
& $voicePython -m PyInstaller --noconfirm --clean --windowed --onedir --name ErgoTranslateVoice --distpath .package-translation-voice --workpath .build-translation-voice --specpath .build-translation-voice --paths . --collect-all piper --collect-all onnxruntime --exclude-module pytest run_translation_voice.py
if ($LASTEXITCODE -ne 0) {throw 'Compilation vocale impossible.'}
New-Item -ItemType Directory -Force ergoai/translation_voice/runtime | Out-Null
Copy-Item -Path '.package-translation-voice\ErgoTranslateVoice\*' -Destination ergoai\translation_voice\runtime -Recurse -Force
