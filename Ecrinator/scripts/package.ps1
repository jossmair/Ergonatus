param([string]$Compiler='', [switch]$SkipAssets)
$ErrorActionPreference='Stop'
$ecrRoot=Split-Path $PSScriptRoot
Set-Location -LiteralPath $ecrRoot
$ecrVersion=[regex]::Match((Get-Content Cargo.toml -Raw),'(?m)^version = "([^"]+)"').Groups[1].Value
if((Get-Item runtime/Ecrinator.exe).VersionInfo.ProductVersion -ne $ecrVersion){throw "La version de l’exécutable ne correspond pas au manifeste."}
& python scripts/generate_licenses.py --check
if($LASTEXITCODE){throw 'Mentions légales périmées.'}
New-Item -ItemType Directory -Force -Path dist/portable/Ecrinator | Out-Null
Copy-Item -LiteralPath runtime/Ecrinator.exe -Destination dist/portable/Ecrinator/Ecrinator.exe -Force
Copy-Item -LiteralPath licenses/LICENCES.txt -Destination dist/portable/Ecrinator/LICENCES.txt -Force
Copy-Item -LiteralPath LIRE-MOI.txt -Destination dist/portable/Ecrinator/LIRE-MOI.txt -Force
Set-Content -LiteralPath dist/portable/Ecrinator/portable.flag -Value 'Écrinator portable : données locales dans le dossier data voisin.' -Encoding utf8
$ecrZip="dist/Ecrinator-$ecrVersion-portable-windows-x64.zip"
# Archive only distribution files. A previous portable launch may have created
# personal data beside the executable; it must never enter a later release.
Add-Type -AssemblyName System.IO.Compression
$ecrArchive=[IO.Compression.ZipArchive]::new([IO.File]::Open((Join-Path $ecrRoot $ecrZip),[IO.FileMode]::Create),[IO.Compression.ZipArchiveMode]::Create)
try {
    foreach($ecrFile in @('Ecrinator.exe','LICENCES.txt','LIRE-MOI.txt','portable.flag')) {
        $ecrEntry=$ecrArchive.CreateEntry("Ecrinator/$ecrFile",[IO.Compression.CompressionLevel]::Optimal)
        $ecrInput=[IO.File]::OpenRead((Join-Path $ecrRoot "dist/portable/Ecrinator/$ecrFile"))
        $ecrOutput=$ecrEntry.Open()
        try {$ecrInput.CopyTo($ecrOutput)} finally {$ecrOutput.Dispose();$ecrInput.Dispose()}
    }
} finally {$ecrArchive.Dispose()}
if(-not $SkipAssets){
& python scripts/package_assets.py $ecrVersion
if($LASTEXITCODE){throw 'Paquet de ressources graphiques en échec.'}
}
if(-not $Compiler){$Compiler=Join-Path $ecrRoot '../PDFinator/.tools/innosetup/ISCC.exe'}
if(-not(Test-Path -LiteralPath $Compiler)){throw 'Indiquez le compilateur Inno Setup avec -Compiler.'}
& $Compiler '/Qp' "/DAppVersion=$ecrVersion" scripts/ecrinator.iss
if($LASTEXITCODE){throw "Construction de l’installeur en échec."}
$ecrPackages=@($ecrZip,"dist/Ecrinator-$ecrVersion-Setup.exe","dist/Ecrinator-$ecrVersion-icones-et-illustration.zip","dist/Ecrinator-$ecrVersion-fonds-matieres.zip","dist/Ecrinator-$ecrVersion-bibliotheque-scolaire.zip")
$ecrHashes=$ecrPackages | Get-FileHash -Algorithm SHA256
$ecrHashes | ForEach-Object { $_.Hash.ToLowerInvariant()+' *'+[IO.Path]::GetFileName($_.Path) } | Set-Content -LiteralPath dist/SHA256SUMS.txt -Encoding utf8
$ecrHashes | Format-List
