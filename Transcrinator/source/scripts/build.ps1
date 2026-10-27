param([string]$InnoCompiler = "", [string]$RecognitionRuntime = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path .venv/Scripts/python.exe)) { python -m venv .venv }
& .venv/Scripts/python.exe -m pip install -r requirements-lock.txt
if ($LASTEXITCODE) { throw "Installation des dépendances échouée" }
& .venv/Scripts/python.exe -m pytest -q
if ($LASTEXITCODE) { throw "Tests échoués" }
& .venv/Scripts/python.exe scripts/make_icon.py
& .venv/Scripts/python.exe scripts/collect_licenses.py
& .venv/Scripts/python.exe -m PyInstaller --noconfirm Transcri.spec
if ($LASTEXITCODE) { throw "Compilation échouée" }
$bundleArguments = @("-m", "scripts.package_turnkey")
if ($RecognitionRuntime) { $bundleArguments += @("--recognition-runtime", $RecognitionRuntime) }
& .venv/Scripts/python.exe @bundleArguments
if ($LASTEXITCODE) { throw "Modèles ou runtimes de distribution manquants" }
& .venv/Scripts/python.exe scripts/package_installer.py
if ($LASTEXITCODE) { throw "Installateur utilisateur échoué" }
if (-not $InnoCompiler) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compiler) { $InnoCompiler = $compiler.Source }
}
if ($InnoCompiler) {
    & $InnoCompiler installer/Transcri.iss
    if ($LASTEXITCODE) { throw "Installateur échoué" }
}
