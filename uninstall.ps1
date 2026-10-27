$ErrorActionPreference='Stop'
$installDirectory=[IO.Path]::GetFullPath($PSScriptRoot)
if (-not (Test-Path -LiteralPath (Join-Path $installDirectory 'Hub\Ergonatus.exe'))) {throw 'Ce dossier ne contient pas une installation Ergonatus.'}
$runKey='HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
$value=(Get-ItemProperty -LiteralPath $runKey -Name Ergonatus -ErrorAction SilentlyContinue).Ergonatus
if ($value -and $value.Contains((Join-Path $installDirectory 'Hub\Ergonatus.exe'))) {Remove-ItemProperty -LiteralPath $runKey -Name Ergonatus}
$shortcutPath=Join-Path ([Environment]::GetFolderPath('Desktop')) 'Ergonatus.lnk'
if (Test-Path -LiteralPath $shortcutPath) {
    $shellObject=New-Object -ComObject WScript.Shell
    if ($shellObject.CreateShortcut($shortcutPath).TargetPath -eq (Join-Path $installDirectory 'Hub\Ergonatus.exe')) {Remove-Item -LiteralPath $shortcutPath}
}
Write-Output 'Raccourci et démarrage personnel retirés. Les logiciels, modèles et documents sont conservés ; quittez les programmes avant de retirer manuellement leur dossier.'
