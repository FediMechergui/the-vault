# Run once from an Administrator PowerShell on the PC hosting THE VAULT.
# Only devices on directly connected local subnets can reach these ports.
$ErrorActionPreference = 'Stop'
$vaultRoot = Split-Path $PSScriptRoot -Parent
$rules = @(
    @{Name='TheVault-Https'; DisplayName='THE VAULT local HTTPS'; Protocol='TCP'; LocalPort=8443},
    @{Name='TheVault-Discovery'; DisplayName='THE VAULT local discovery'; Protocol='UDP'; LocalPort=5353}
)
foreach ($rule in $rules) {
    $existing = Get-NetFirewallRule -Name $rule.Name -ErrorAction SilentlyContinue
    if ($existing) { Remove-NetFirewallRule -Name $rule.Name -ErrorAction Stop }
    New-NetFirewallRule @rule -Direction Inbound -Action Allow -Profile Any -RemoteAddress LocalSubnet -ErrorAction Stop | Out-Null
}
Write-Host 'THE VAULT is allowed from local subnets on all network profiles (TCP 8443 and UDP 5353).'
