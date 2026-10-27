$ErrorActionPreference = 'Stop'
$cleanupRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')).TrimEnd('\')
$cleanupPlanPath = Join-Path $cleanupRoot 'docs\maintenance\cleanup-plan-2026-10-20.json'
$cleanupPlan = Get-Content -LiteralPath $cleanupPlanPath -Raw | ConvertFrom-Json
if ((Get-Date) - (Get-Item -LiteralPath $cleanupPlanPath).LastWriteTime -gt [TimeSpan]::FromHours(1)) { throw 'Plan de nettoyage expiré : refaire un inventaire avant toute suppression.' }
if ($cleanupPlan.root -ne $cleanupRoot) { throw 'La racine du plan ne correspond pas au dossier Ergonatus.' }
$cleanupTargets = @()
foreach ($entry in $cleanupPlan.candidates) {
    $targetPath = [IO.Path]::GetFullPath($entry.path).TrimEnd('\')
    if (-not $targetPath.StartsWith($cleanupRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Cible hors Ergonatus : $targetPath" }
    if ($targetPath -eq $cleanupRoot) { throw 'Suppression de la racine interdite.' }
    if (Test-Path -LiteralPath $targetPath) {
        $resolvedTarget = (Resolve-Path -LiteralPath $targetPath).Path.TrimEnd('\')
        if ($resolvedTarget -ne $targetPath) { throw "Résolution inattendue : $targetPath" }
        $item = Get-Item -LiteralPath $targetPath -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Lien refusé : $targetPath" }
        if ($item.PSIsContainer) {
            $linkedItems = @(Get-ChildItem -LiteralPath $targetPath -Force -Recurse -Attributes ReparsePoint)
            if ($linkedItems.Count -gt 0) { throw "Lien interne refusé : $targetPath" }
        }
        $cleanupTargets += $entry
    }
}
foreach ($process in Get-Process) {
    try { $processPath = $process.Path } catch { continue }
    if (-not $processPath) { continue }
    foreach ($entry in $cleanupTargets) {
        if ($processPath -eq $entry.path -or $processPath.StartsWith($entry.path + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Un processus utilise encore une cible : $processPath" }
    }
}
$cleanupResults = @()
foreach ($entry in $cleanupTargets) {
    try {
        Remove-Item -LiteralPath $entry.path -Recurse -Force
        $cleanupResults += [pscustomobject]@{ path=$entry.relative; bytes=$entry.bytes; removed=$true }
    } catch {
        $cleanupResults += [pscustomobject]@{ path=$entry.relative; bytes=$entry.bytes; removed=$false; error=$_.Exception.Message }
    }
}
$cleanupResults | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $cleanupRoot 'docs\maintenance\cleanup-results-2026-10-20.json') -Encoding utf8
$cleanupRemoved = @($cleanupResults | Where-Object { $_.removed })
$cleanupFailed = @($cleanupResults | Where-Object { -not $_.removed })
Write-Output "Supprimés : $($cleanupRemoved.Count) ; échecs : $($cleanupFailed.Count)"
if ($cleanupFailed.Count -gt 0) { $cleanupFailed | Select-Object path,error | Format-Table -AutoSize }
