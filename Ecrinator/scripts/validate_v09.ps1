$ErrorActionPreference='Stop'
$ecrRoot=Split-Path $PSScriptRoot
Set-Location -LiteralPath $ecrRoot
./scripts/build.ps1 -SkipTests *> test-output/build-v09-final.log
./scripts/verify.ps1 -Output test-output/acceptance-v09-release -Independent *> test-output/acceptance-v09.log
& python scripts/test_libreoffice.py test-output/acceptance-v09-release v09 *> test-output/libreoffice-v09.log
if($LASTEXITCODE){throw 'Ouverture LibreOffice en échec.'}
& python scripts/render_lo.py test-output/libreoffice-v09 *> test-output/libreoffice-render-v09.log
if($LASTEXITCODE){throw 'Rendu LibreOffice en échec.'}
foreach($ecrView in @('encadres','library')){
    $env:ECRINATOR_DATA_DIR=Join-Path $ecrRoot "test-output/qa-v09-$ecrView"
    $env:ECRINATOR_QA_SCREENSHOT=Join-Path $ecrRoot "test-output/ecrinator-0.9.0-$ecrView.png"
    $env:ECRINATOR_QA_TABS='1'
    $env:ECRINATOR_QA_DIALOG=if($ecrView -eq 'library'){'library'}else{''}
    $ecrFixture=Join-Path $ecrRoot 'test-output/acceptance-v09-release/Cours de mathématiques.ecr'
    $ecrProcess=Start-Process -FilePath (Join-Path $ecrRoot 'runtime/Ecrinator.exe') -ArgumentList @(('"'+$ecrFixture+'"')) -WindowStyle Hidden -PassThru -Wait
    if($ecrProcess.ExitCode -ne 0){throw "Capture native en échec : $ecrView"}
    if(-not(Test-Path -LiteralPath $env:ECRINATOR_QA_SCREENSHOT)){throw "Capture absente : $ecrView"}
}
Write-Output 'Exécutable, exports, ouverture LibreOffice et captures natives vérifiés.'
