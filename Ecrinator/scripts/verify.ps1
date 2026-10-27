param([string]$Output='', [switch]$Independent)
$ErrorActionPreference='Stop'
$ecrRoot=Split-Path $PSScriptRoot
Set-Location -LiteralPath $ecrRoot
if(-not $Output){$Output=Join-Path $ecrRoot 'test-output/acceptance-release'}
$Output=[IO.Path]::GetFullPath($Output)
$env:ECRINATOR_DATA_DIR=Join-Path $ecrRoot 'test-output/acceptance-data'
$ecrProcess=Start-Process -FilePath (Join-Path $ecrRoot 'runtime/Ecrinator.exe') -ArgumentList @('--verify',('"'+$Output+'"')) -WindowStyle Hidden -PassThru -Wait
if($ecrProcess.ExitCode -ne 0){throw "Vérification Écrinator en échec ($($ecrProcess.ExitCode))."}
Get-Content -LiteralPath (Join-Path $Output 'verification.json')
if($Independent){
    & python scripts/verify_exports.py $Output
    if($LASTEXITCODE){throw 'Contrôle PDF/ODT/DOCX indépendant en échec.'}
}
