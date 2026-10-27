param([switch]$SkipPortable)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$release=Join-Path $root 'output/releases/2026.10.27'
$seven=Join-Path $release 'tools/extra/x64/7za.exe'
$python=Join-Path (Split-Path $root -Parent) 'Redactor/.venv/Scripts/python.exe'
if (-not (Test-Path (Join-Path $release 'staging.json'))) {throw 'Staging non vérifié'}
if (-not $SkipPortable) {
 Push-Location (Join-Path $release 'payload')
 try {
    & $seven a -tzip (Join-Path $release 'assets/Ergonatus-2026.10.27-portable.zip') Ergonatus '-mx=1' '-mmt=2' '-v1500m' '-bsp0' *> (Join-Path $release 'portable-build.log')
    if ($LASTEXITCODE -ne 0) {throw 'Compression portable échouée'}
 } finally {Pop-Location}
}
& (Join-Path $root 'PDFinator/.tools/innosetup/ISCC.exe') "/DReleaseRoot=$release" (Join-Path $root 'scripts/ergonatus.iss') *> (Join-Path $release 'installer-build.log')
if ($LASTEXITCODE -ne 0) {throw 'Construction installeur échouée'}
Copy-Item -LiteralPath $seven -Destination (Join-Path $release 'assets/7za.exe')
Copy-Item -LiteralPath (Join-Path $release 'tools/extra/License.txt') -Destination (Join-Path $release 'assets/7-Zip-LICENSE.txt')
@'
@echo off
cd /d "%~dp0"
if not exist "7za.exe" (echo Telechargez aussi 7za.exe depuis cette meme release.& pause & exit /b 1)
"7za.exe" x "Ergonatus-2026.10.27-portable.zip.001" -o"%~dp0Portable" -aos
if errorlevel 1 (echo Extraction echouee. Verifiez que tous les volumes sont presents.& pause & exit /b 1)
echo Ouvrez Portable\Ergonatus\Lancer Ergonatus.cmd
pause
'@ | Set-Content -LiteralPath (Join-Path $release 'assets/Extraire-portable.cmd') -Encoding ascii
& $python -c "from pathlib import Path;import zipfile;p=Path(r'$release');z=zipfile.ZipFile(p/'assets/Ergonatus-2026.10.27-source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=2);[z.write(f,'Ergonatus/'+f.relative_to(p/'source').as_posix()) for f in (p/'source').rglob('*') if f.is_file() and '.git' not in f.parts];z.close()"
if ($LASTEXITCODE -ne 0) {throw 'Archivage sources échoué'}
'Archives créées.'
