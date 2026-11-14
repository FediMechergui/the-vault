param([int]$Port = 8443,
      [ValidateSet('auto','matlab-engine','python-reference')][string]$Backend = 'auto',
      [string]$MatlabRoot = '')
$ErrorActionPreference = 'Stop'
$vaultRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $vaultRoot
$python = Join-Path $vaultRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Run the setup instructions in README.md first.' }
$arguments = @('scripts/start.py','--local','--port',"$Port",'--backend',$Backend)
if ($MatlabRoot) { $arguments += @('--matlab-root',$MatlabRoot) }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw 'THE VAULT could not start; see the diagnostic above.' }
