param([switch]$SkipTests)
$ErrorActionPreference='Stop'
$ecrRoot=Split-Path $PSScriptRoot
Set-Location -LiteralPath $ecrRoot
$ecrToolRoot=Join-Path $ecrRoot '../PDFinator/.tools'
$ecrCargo=Join-Path $ecrToolRoot 'cargo/bin/cargo.exe'
if(Test-Path -LiteralPath $ecrCargo){$env:CARGO_HOME=(Resolve-Path "$ecrToolRoot/cargo").Path;$env:RUSTUP_HOME=(Resolve-Path "$ecrToolRoot/rustup").Path}else{$ecrCargo='cargo'}
New-Item -ItemType Directory -Force -Path test-output/tmp,runtime | Out-Null
$env:TEMP=(Resolve-Path test-output/tmp).Path;$env:TMP=$env:TEMP
$env:ECRINATOR_DATA_DIR=Join-Path $ecrRoot 'test-output/test-data'
& python scripts/package_library.py
if($LASTEXITCODE){throw 'Bibliothèque scolaire invalide.'}
if(-not $SkipTests){& $ecrCargo test --locked --offline -- --test-threads=1;if($LASTEXITCODE){throw 'Tests en échec.'}}
& $ecrCargo build --release --locked --offline
if($LASTEXITCODE){throw 'Compilation en échec.'}
Copy-Item -LiteralPath target/release/ecrinator.exe -Destination runtime/Ecrinator.exe -Force
Copy-Item -LiteralPath assets/library/library.eclib -Destination runtime/library.eclib -Force
& python scripts/generate_licenses.py
if($LASTEXITCODE){throw 'Mentions légales incomplètes.'}
Write-Output 'Application construite dans runtime/Ecrinator.exe'
