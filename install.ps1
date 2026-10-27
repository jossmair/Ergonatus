param([string]$Destination=(Join-Path $env:LOCALAPPDATA 'Programs\Ergonatus'))
$ErrorActionPreference='Stop'
$sourceDirectory=$PSScriptRoot
$targetDirectory=[IO.Path]::GetFullPath($Destination)
if (Test-Path -LiteralPath $targetDirectory) {throw 'La destination existe déjà. Choisissez un nouveau dossier pour conserver la version précédente.'}
New-Item -ItemType Directory -Path $targetDirectory | Out-Null
foreach ($name in @('Hub','assets','models','shared','orb_manager','docs')) {
    Copy-Item -LiteralPath (Join-Path $sourceDirectory $name) -Destination $targetDirectory -Recurse
}
$voiceTarget=Join-Path $targetDirectory 'ergoai'
New-Item -ItemType Directory -Path $voiceTarget | Out-Null
Get-ChildItem -LiteralPath (Join-Path $sourceDirectory 'ergoai') -Force | Where-Object {$_.Name -notin @('voice','__pycache__')} | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $voiceTarget -Recurse}
New-Item -ItemType Directory -Path (Join-Path $voiceTarget 'voice') | Out-Null
Get-ChildItem -LiteralPath (Join-Path $sourceDirectory 'ergoai\voice') -Force | Where-Object {$_.Name -notin @('.venv','__pycache__')} | ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $voiceTarget 'voice') -Recurse}
$applications=@('Claviernator','Precisionator','Transcrinator','Redactor','Scanator','Ecrinator','Organisator','Lector','Applinator','Temporator','Concentrator','PDFinator','Calculinator','Communicator','Memorinator','Planinator','Traductor','Corrector','Dictionnator','Explicator','Tablinator')
foreach ($name in $applications) {
    $appTarget=Join-Path $targetDirectory $name
    New-Item -ItemType Directory -Path $appTarget | Out-Null
    foreach ($entry in @('runtime','source','README.md','main.py') + $(if ($name -eq 'Dictionnator') {@('data')} else {@()})) {
        $sourceEntry=Join-Path (Join-Path $sourceDirectory $name) $entry
        if (Test-Path -LiteralPath $sourceEntry) {Copy-Item -LiteralPath $sourceEntry -Destination $appTarget -Recurse}
    }
}
foreach ($file in @('Lancer Ergonatus.cmd','README.md','uninstall.ps1','suite_design.py','suite_interactions.py','suite_interactions.json','run_ergonatus.py','run_satellite.py','run_ergoai.py','requirements.txt','requirements-dev.txt')) {Copy-Item -LiteralPath (Join-Path $sourceDirectory $file) -Destination $targetDirectory}
Copy-Item -LiteralPath (Join-Path $sourceDirectory 'scripts') -Destination $targetDirectory -Recurse
$shellObject=New-Object -ComObject WScript.Shell
$shortcut=$shellObject.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ergonatus.lnk'))
$shortcut.TargetPath=Join-Path $targetDirectory 'Hub\Ergonatus.exe';$shortcut.WorkingDirectory=$targetDirectory;$shortcut.Save()
Write-Output "Ergonatus installé dans $targetDirectory. Aucun programme lancé ni démarrage Windows activé."
