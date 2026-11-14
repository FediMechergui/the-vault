param([switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$vaultRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $vaultRoot
if (-not $SkipInstall) {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw 'Install uv first: winget install --id astral-sh.uv --exact. Then reopen PowerShell.'
    }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & uv venv --python 3.11 .venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed.' }
    }
    & uv pip install --python .venv/Scripts/python.exe -r requirements.txt -r vision-py/requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
& .venv/Scripts/python.exe scripts/bootstrap.py --models
if ($LASTEXITCODE -ne 0) { throw 'Server preparation failed.' }
Write-Host 'Setup complete. Start with: .venv/Scripts/python.exe scripts/start.py --local --backend matlab-engine'
