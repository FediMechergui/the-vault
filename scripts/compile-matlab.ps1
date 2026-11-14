param([string]$LicenseServer = $env:MLM_LICENSE_FILE)
$ErrorActionPreference = 'Stop'
$vaultRoot = (Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
if (-not $LicenseServer) {
    throw 'Set MLM_LICENSE_FILE to your activated network license, or use the browser activation instructions in docs/matlab.md.'
}
docker run --rm --shm-size=512m -e "MLM_LICENSE_FILE=$LicenseServer" --mount "type=bind,source=$vaultRoot,target=/workspace" vault-matlab-compiler:r2025b -batch "run('/workspace/matlab-engine/build_engine.m')"
if ($LASTEXITCODE -ne 0) { throw 'MATLAB compilation failed; see the license/build output above.' }
