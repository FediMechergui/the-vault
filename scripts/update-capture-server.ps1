param([Parameter(Mandatory=$true)][string]$ServerPath)
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$serverRoot = (Resolve-Path -LiteralPath $ServerPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $serverRoot 'scripts/start.py'))) {
    throw 'Choose the existing server folder containing scripts/start.py.'
}
function TextHash([string]$Path) {
    $value = [IO.File]::ReadAllText($Path).Replace("`r`n", "`n")
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($value)))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
$baseline = @{
    'gateway/app/clients.py' = 'fe4406e46d11a4b7ddda54f629d6119488767305c1d045d28484db473081e817'
    'gateway/app/main.py' = 'b363ed72019d5aa1c0dedf2773d2504617c12c0a169d27518f36adfabb395754'
    'gateway/app/errors.py' = ''
}
$pending = @()
foreach ($relative in $baseline.Keys) {
    $source = Join-Path $sourceRoot $relative
    $target = Join-Path $serverRoot $relative
    if (-not (Test-Path -LiteralPath $source)) { throw "Update source is incomplete: $relative" }
    if (Test-Path -LiteralPath $target) {
        $current = TextHash $target
        if ($current -eq (TextHash $source)) { continue }
        if ($current -ne $baseline[$relative]) { throw "Local changes found in $relative. No files were changed; review them before updating." }
    } elseif ($baseline[$relative] -ne '') { throw "Server file missing: $relative" }
    $pending += $relative
}
if ($pending.Count -eq 0) { Write-Output 'The capture server patch is already installed.'; exit 0 }
$backup = Join-Path $serverRoot ('.local/server-backups/v0.1.3-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($relative in $pending) {
    $target = Join-Path $serverRoot $relative
    if (Test-Path -LiteralPath $target) {
        $saved = Join-Path $backup $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $saved) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $saved
    }
}
foreach ($relative in $pending) {
    Copy-Item -LiteralPath (Join-Path $sourceRoot $relative) -Destination (Join-Path $serverRoot $relative) -Force
}
Write-Output "Capture server patch installed. Backup: $backup"
Write-Output 'Restart the existing server to load the update. Its data, certificates, Python environment and MATLAB settings are preserved.'
