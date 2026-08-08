param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\Programs\AgentFactory",
    [string]$StateRoot = "$env:LOCALAPPDATA\AgentFactory",
    [switch]$PurgeState
)

$ErrorActionPreference = "Stop"
$ResolvedInstallRoot = [IO.Path]::GetFullPath($InstallRoot).TrimEnd("\")
if ([IO.Path]::GetFileName($ResolvedInstallRoot) -ne "AgentFactory") {
    throw "InstallRoot must end in AgentFactory"
}
if (Test-Path $ResolvedInstallRoot) {
    Remove-Item -Recurse -Force $ResolvedInstallRoot
}

$BinDirectory = Join-Path $ResolvedInstallRoot "bin"
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath) {
    $Updated = (($UserPath -split ";") | Where-Object { $_ -and $_ -ne $BinDirectory }) -join ";"
    [Environment]::SetEnvironmentVariable("Path", $Updated, "User")
}

if ($PurgeState) {
    $ResolvedStateRoot = [IO.Path]::GetFullPath($StateRoot).TrimEnd("\")
    if ([IO.Path]::GetFileName($ResolvedStateRoot) -ne "AgentFactory") {
        throw "StateRoot must end in AgentFactory"
    }
    if (Test-Path $ResolvedStateRoot) {
        Remove-Item -Recurse -Force $ResolvedStateRoot
    }
    Write-Host "Agent Factory binaries and local state removed"
} else {
    Write-Host "Agent Factory binaries removed. Local settings, credentials and run state were preserved."
}
