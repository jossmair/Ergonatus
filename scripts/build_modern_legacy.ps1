$ErrorActionPreference='Stop'
$modernRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$workspaceRoot=Split-Path $modernRoot -Parent
foreach ($entry in @(@('Precisionator','Precisionator','Precisionator.spec'),@('Transcrinator','Transcri','Transcri.spec'),@('Redactor','Redactor','Redactor.spec'))) {
    $appName=$entry[0];$pythonProject=$entry[1];$spec=$entry[2]
    Set-Location -LiteralPath (Join-Path $modernRoot "$appName\source")
    $env:PYTHONPATH=(Get-Location).Path
    $pythonPath=Join-Path $workspaceRoot "$pythonProject\.venv\Scripts\python.exe"
    & $pythonPath -m PyInstaller --noconfirm --distpath "../../.modern-package/$($appName.ToLower())" --workpath "../../.modern-build/$($appName.ToLower())" $spec *> (Join-Path $modernRoot "docs/maintenance/modern-build-$($appName.ToLower())-2026-10-24.log")
    if ($LASTEXITCODE -ne 0) {throw "Compilation impossible : $appName"}
    Write-Output "$appName compilé"
}
