param(
    [string]$Version = "",
    [string]$Repository = "RoKenshi/agent-factory-client",
    [string]$InstallRoot = "$env:LOCALAPPDATA\AgentFactory",
    [switch]$SkipSetup
)

$ErrorActionPreference = "Stop"
$ReleaseKeySha256 = "beffec8ae3d1e3f614f81b441261176ab02b8bd800ac791eddaaf06d0da7de29"
if (-not [Environment]::Is64BitOperatingSystem) { throw "64-bit Windows is required" }
if ($env:PROCESSOR_ARCHITECTURE -notin @("AMD64", "x86")) {
    throw "Only Windows x86-64 is currently published"
}
$OpenSsl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $OpenSsl) {
    throw "OpenSSL is required to verify the Agent Factory release signature"
}

if ($Version) {
    $Tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
} else {
    $Release = Invoke-RestMethod "https://api.github.com/repos/$Repository/releases/latest"
    $Tag = $Release.tag_name
}

$CleanVersion = $Tag.TrimStart("v")
$Asset = "agent-factory-v$CleanVersion-windows-x86_64.zip"
$Base = "https://github.com/$Repository/releases/download/$Tag"
$Temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("agent-factory-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Temporary | Out-Null

try {
    $Archive = Join-Path $Temporary $Asset
    Invoke-WebRequest "$Base/$Asset" -OutFile $Archive
    Invoke-WebRequest "$Base/SHA256SUMS" -OutFile (Join-Path $Temporary "SHA256SUMS")
    Invoke-WebRequest "$Base/SHA256SUMS.sig" -OutFile (Join-Path $Temporary "SHA256SUMS.sig")
    $PublicKey = Join-Path $Temporary "RELEASE-SIGNING-KEY.pem"
    Invoke-WebRequest `
        "https://raw.githubusercontent.com/$Repository/main/RELEASE-SIGNING-KEY.pem" `
        -OutFile $PublicKey
    $KeyDigest = (Get-FileHash -Algorithm SHA256 $PublicKey).Hash.ToLowerInvariant()
    if ($KeyDigest -ne $ReleaseKeySha256) {
        throw "Release verification key fingerprint mismatch"
    }
    & $OpenSsl.Source pkeyutl -verify -rawin `
        -pubin `
        -inkey $PublicKey `
        -sigfile (Join-Path $Temporary "SHA256SUMS.sig") `
        -in (Join-Path $Temporary "SHA256SUMS") | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Release checksum signature verification failed" }
    $ChecksumLine = Get-Content (Join-Path $Temporary "SHA256SUMS") |
        Where-Object { $_ -match "^[0-9a-fA-F]{64}\s+$([regex]::Escape($Asset))$" } |
        Select-Object -First 1
    if (-not $ChecksumLine) { throw "Release checksum is missing" }
    $Expected = ($ChecksumLine -split "\s+")[0].ToLowerInvariant()
    $Actual = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { throw "SHA-256 verification failed" }

    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $Target = Join-Path $InstallRoot $CleanVersion
    if (Test-Path $Target) { throw "$Target already exists" }
    Expand-Archive -Path $Archive -DestinationPath $Temporary
    $Extracted = Join-Path $Temporary "agent-factory-v$CleanVersion-windows-x86_64"
    Move-Item $Extracted $Target
    $Binary = Join-Path $Target "agent-factory.exe"
    $Signature = Get-AuthenticodeSignature $Binary
    if ($Signature.Status -eq [System.Management.Automation.SignatureStatus]::Valid) {
        Write-Host "Authenticode signature: valid"
    } else {
        Write-Warning "Unsigned beta (Authenticode status: $($Signature.Status)). Ed25519 release signature and archive SHA-256 are valid."
    }
    & $Binary self-test

    $BinDirectory = Join-Path $InstallRoot "bin"
    New-Item -ItemType Directory -Force -Path $BinDirectory | Out-Null
    $Command = Join-Path $BinDirectory "agent-factory.cmd"
    "@echo off`r`n`"$Binary`" %*`r`n" | Set-Content -Encoding ASCII $Command
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (($UserPath -split ";") -notcontains $BinDirectory) {
        $UpdatedPath = if ($UserPath) { "$UserPath;$BinDirectory" } else { $BinDirectory }
        [Environment]::SetEnvironmentVariable("Path", $UpdatedPath, "User")
    }
    $env:Path = "$env:Path;$BinDirectory"
    Write-Host "Agent Factory $CleanVersion installed at $Target"
    if (-not $SkipSetup -and $env:AGENT_FACTORY_SKIP_SETUP -ne "1") {
        Write-Host "Opening the local setup wizard..."
        & $Binary setup
    } else {
        Write-Host "Run: agent-factory setup"
    }
} finally {
    Remove-Item -Recurse -Force $Temporary -ErrorAction SilentlyContinue
}
