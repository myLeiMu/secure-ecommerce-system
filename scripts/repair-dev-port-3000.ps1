#Requires -RunAsAdministrator
# Keep this file ASCII: Windows PowerShell 5.1 reads BOM-less scripts as ANSI.
$ErrorActionPreference = 'Stop'

function Test-DevPort {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 3000)
    try { $listener.Start(); return $true }
    catch [Net.Sockets.SocketException] {
        if ($_.Exception.SocketErrorCode -eq [Net.Sockets.SocketError]::AddressAlreadyInUse) {
            throw '3000 is already in use. Stop the owning server; do not change network settings.'
        }
        if ($_.Exception.SocketErrorCode -ne [Net.Sockets.SocketError]::AccessDenied) { throw }
        return $false
    }
    finally { $listener.Stop() }
}

if (Test-DevPort) { Write-Host '3000 bind OK; no system changes needed.'; exit 0 }

$projectRoot = Split-Path -Parent $PSScriptRoot
$backupDir = Join-Path $projectRoot ('dist-releases/port-3000-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
$rollback = @('#Requires -RunAsAdministrator')
foreach ($family in @('ipv4', 'ipv6')) {
    $snapshot = & netsh interface $family show dynamicport tcp
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read dynamic port configuration.' }
    $snapshot | Set-Content -LiteralPath (Join-Path $backupDir "$family-dynamic-before.txt")
    $numbers = @($snapshot | ForEach-Object {
        if ($_ -match '[:\uFF1A]\s*(\d+)\s*$') { [int]$Matches[1] }
    })
    if ($numbers.Count -ne 2) { throw 'Cannot parse existing range; no settings changed.' }
    $rollback += "netsh interface $family set dynamicport tcp start=$($numbers[0]) num=$($numbers[1])"
    & netsh interface $family show excludedportrange protocol=tcp |
        Set-Content -LiteralPath (Join-Path $backupDir "$family-exclusions-before.txt")
}
$rollback | Set-Content -LiteralPath (Join-Path $backupDir 'restore-dynamic-ranges.ps1')
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters' |
    Select-Object MaxUserPort | ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $backupDir 'registry-context.json')

Write-Host "Backup: $backupDir"
Write-Host 'Restoring default TCP dynamic ranges; restarting WinNAT briefly interrupts WSL/container networking.'
foreach ($family in @('ipv4', 'ipv6')) {
    & netsh interface $family set dynamicport tcp start=49152 num=16384
    if ($LASTEXITCODE -ne 0) { throw "Failed to update $family; rollback commands are in $backupDir" }
}
Restart-Service -Name WinNat -ErrorAction Stop
Start-Sleep -Seconds 3
foreach ($family in @('ipv4', 'ipv6')) {
    & netsh interface $family show excludedportrange protocol=tcp |
        Set-Content -LiteralPath (Join-Path $backupDir "$family-exclusions-after.txt")
}
if (-not (Test-DevPort)) {
    throw '3000 remains reserved. Save work and restart Windows, then rerun this check. No successful repair is claimed.'
}
Write-Host '3000 bind OK. Start the frontend with npm run dev and open https://localhost:3000.'
