# Pomodoro dev: inbound TCP for Flet (8550-8581) and FastAPI (8000-8031).
# Profiles: Domain,Private,Public — iPhone hotspot is often "Public" on Windows; old rules
# were Private-only and blocked the phone. Re-run this after network changes.
# Must match app.py / pomodoro_api.py port ranges.

$FletWebPortFirst = 8550
$FletWebPortLast  = 8581
$FletWebPortRange = "$FletWebPortFirst-$FletWebPortLast"
$FletRuleDisplayName = "Pomodoro Flet Web $FletWebPortRange"

$ApiPortFirst = 8000
$ApiPortLast  = 8031
$ApiPortRange = "$ApiPortFirst-$ApiPortLast"
$ApiRuleDisplayName = "Pomodoro FastAPI $ApiPortRange"

# All Windows network categories (hotspot / guest Wi-Fi usually = Public).
$FirewallProfiles = @("Domain", "Private", "Public")

$isAdmin = (
    [Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args | Out-Null
    exit
}

$ErrorActionPreference = "Stop"

function Ensure-PortRangeRule {
    param(
        [string]$DisplayName,
        [string]$LocalPortRange
    )
    $old = Get-NetFirewallRule -DisplayName $DisplayName -ErrorAction SilentlyContinue
    if ($old) {
        Set-NetFirewallRule -DisplayName $DisplayName -Profile $FirewallProfiles
        Write-Host "[ok]   profiles Domain,Private,Public : $DisplayName"
        return
    }
    New-NetFirewallRule `
        -DisplayName $DisplayName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $LocalPortRange `
        -Profile $FirewallProfiles `
        | Out-Null
    Write-Host "[ok]   created: $DisplayName (TCP $LocalPortRange, profiles Domain,Private,Public)"
}

Write-Host ""
Remove-NetFirewallRule -DisplayName "Pomodoro Flet Web 8550" -ErrorAction SilentlyContinue
Ensure-PortRangeRule -DisplayName $FletRuleDisplayName -LocalPortRange $FletWebPortRange
Remove-NetFirewallRule -DisplayName "Pomodoro FastAPI 8000" -ErrorAction SilentlyContinue
Ensure-PortRangeRule -DisplayName $ApiRuleDisplayName -LocalPortRange $ApiPortRange
Write-Host ""
Write-Host "Done. Run: python pomodoro_api.py  then  python app.py --web"
Write-Host "If phone still fails on iPhone hotspot: try same Wi-Fi router for PC+phone,"
Write-Host "or open the phone from another device on the same hotspot."
Write-Host ""
Read-Host "Press Enter to close"
