param(
    [string]$Version = "",
    [string]$Repository = "RoKenshi/agent-factory-client",
    [string]$InstallRoot = "$env:LOCALAPPDATA\Programs\AgentFactory",
    [string]$ReleaseBaseUrl = $env:AGENT_FACTORY_RELEASE_BASE_URL,
    [string]$ReleasePublicKeyModulus = "",
    [switch]$NoPathUpdate
)

$ErrorActionPreference = "Stop"
if (-not [Environment]::Is64BitOperatingSystem) { throw "64-bit Windows is required" }
$Architecture = if ($env:PROCESSOR_ARCHITEW6432) {
    $env:PROCESSOR_ARCHITEW6432
} else {
    $env:PROCESSOR_ARCHITECTURE
}
if ($Architecture -ne "AMD64") { throw "Only Windows x86-64 is currently published" }

if ($Version) {
    $Tag = if ($Version.StartsWith("v")) { $Version } else { "v$Version" }
} elseif ($ReleaseBaseUrl) {
    throw "Version is required with ReleaseBaseUrl"
} else {
    $Release = Invoke-RestMethod "https://api.github.com/repos/$Repository/releases/latest"
    $Tag = $Release.tag_name
}

$CleanVersion = $Tag.TrimStart("v")
if ($CleanVersion -notmatch "^[0-9A-Za-z][0-9A-Za-z.+-]*$") {
    throw "Invalid release version"
}
$Asset = "agent-factory-v$CleanVersion-windows-x86_64.zip"
$Base = if ($ReleaseBaseUrl) {
    $ReleaseBaseUrl.TrimEnd("/")
} else {
    "https://github.com/$Repository/releases/download/$Tag"
}
if (-not $Base.StartsWith("https://") -and -not $ReleaseBaseUrl) {
    throw "Refusing a non-HTTPS download"
}
if ($ReleasePublicKeyModulus -and -not $ReleaseBaseUrl) {
    throw "A custom release key is allowed only with an explicit ReleaseBaseUrl"
}

$Temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("agent-factory-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Temporary | Out-Null

try {
    $Archive = Join-Path $Temporary $Asset
    $Checksums = Join-Path $Temporary "SHA256SUMS"
    $Signature = Join-Path $Temporary "SHA256SUMS.sig"
    Invoke-WebRequest "$Base/$Asset" -OutFile $Archive
    Invoke-WebRequest "$Base/SHA256SUMS" -OutFile $Checksums
    Invoke-WebRequest "$Base/SHA256SUMS.sig" -OutFile $Signature

    $PinnedModulus = "po1I9vmvIGg2IQ1n7/MStLnNMqRmQUd+kO9TrQreT+X0gxjwtF/ZDQta+7vDkDu6dZhXNma2flaxMrp8VrPJEXdx89XzycLLuv0Gf8e1tHfg2WV1TRKkMtJa4BFPRQBSXFc1TXM4CUDNSwknAJl8qfb5miMm8QU+7bL2lkEpkPt6h8Rq56RV5eWH4g+1xgN14T14+9FSEK24TLaWK8Uue5clRLYuTcNAscU90fyi0NvTeg0gFOcvrf/FUMEJY4IXyGdTX8bWUcHIRWp9EE+UXjrdr6nC4Mc1G24nPBtfDhFh2ml4A6fal+Y9CYkd4sOFnXtVcBY89vvP+7g30qPu5A7UwMgCocNu1YUYq9I/tfcMjHCxIJAySZJb7tJgmN63ljV7adx3esz8Kr92fctQefO/GYdUFjv7FUygtuNlrOrRr2VBlLWwylfSr75ZX91vl/22lnpjezFIXj7NjBeBZMkANypnRQhr2H/zE97EFXuVKWPeeYoAIXf1dLSx4RAm1AZ7WfWUG76nsCOro1T1x7cQ5EoGcBpFa1PawBb9MMsBGS2eCLiZX8Ogf+9spGvjv1L0mtBoRUxOtjaZRi3/smhp+x4OZZ6JaPKXMRHbQ6AUbkAPRKTCe9f7nZUv+Ht39MimFBplOPaeF1YScqpgsEE5HHk68Q/58sKhdWOnNVU="
    $Modulus = [Convert]::FromBase64String(
        $(if ($ReleasePublicKeyModulus) { $ReleasePublicKeyModulus } else { $PinnedModulus })
    )
    $Exponent = [Convert]::FromBase64String("AQAB")
    $Parameters = New-Object System.Security.Cryptography.RSAParameters
    $Parameters.Modulus = $Modulus
    $Parameters.Exponent = $Exponent
    $Rsa = New-Object System.Security.Cryptography.RSACryptoServiceProvider
    $Rsa.ImportParameters($Parameters)
    try {
        $SignatureValid = $Rsa.VerifyData(
            [IO.File]::ReadAllBytes($Checksums),
            [IO.File]::ReadAllBytes($Signature),
            [System.Security.Cryptography.HashAlgorithmName]::SHA256,
            [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
        )
    } finally {
        $Rsa.Dispose()
    }
    if (-not $SignatureValid) { throw "Release signature verification failed" }

    $ChecksumLine = Get-Content $Checksums |
        Where-Object { $_ -match "^[0-9a-fA-F]{64}\s+\*?$([regex]::Escape($Asset))$" } |
        Select-Object -First 1
    if (-not $ChecksumLine) { throw "Release checksum is missing" }
    $Expected = ($ChecksumLine -split "\s+")[0].ToLowerInvariant()
    $Actual = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { throw "SHA-256 verification failed" }

    $Directory = "agent-factory-v$CleanVersion-windows-x86_64"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Zip = [System.IO.Compression.ZipFile]::OpenRead($Archive)
    try {
        foreach ($Entry in $Zip.Entries) {
            $Normalized = $Entry.FullName.Replace("\", "/")
            $Parts = $Normalized.Split("/")
            if (-not $Normalized.StartsWith("$Directory/") -or $Parts -contains "..") {
                throw "Archive contains an unsafe path: $Normalized"
            }
        }
    } finally {
        $Zip.Dispose()
    }
    $ExtractRoot = Join-Path $Temporary "extracted"
    Expand-Archive -Path $Archive -DestinationPath $ExtractRoot
    $Extracted = Join-Path $ExtractRoot $Directory
    $Binary = Join-Path $Extracted "agent-factory.exe"
    if (-not (Test-Path -PathType Leaf $Binary)) { throw "Archive is missing agent-factory.exe" }
    & $Binary self-test
    if ($LASTEXITCODE -ne 0) { throw "Agent Factory self-test failed" }

    New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
    $Target = Join-Path $InstallRoot $CleanVersion
    if (Test-Path $Target) {
        $ExistingBinary = Join-Path $Target "agent-factory.exe"
        if (-not (Test-Path -PathType Leaf $ExistingBinary)) {
            throw "Existing install is invalid: $Target"
        }
        & $ExistingBinary self-test
        if ($LASTEXITCODE -ne 0) { throw "Existing Agent Factory self-test failed" }
        Write-Host "Agent Factory $CleanVersion is already installed; refreshing the command shim"
    } else {
        Move-Item $Extracted $Target
    }
    $Binary = Join-Path $Target "agent-factory.exe"

    $BinDirectory = Join-Path $InstallRoot "bin"
    New-Item -ItemType Directory -Force -Path $BinDirectory | Out-Null
    $Command = Join-Path $BinDirectory "agent-factory.cmd"
    "@echo off`r`n`"$Binary`" %*`r`n" | Set-Content -Encoding ASCII $Command
    if (-not $NoPathUpdate) {
        $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if (($UserPath -split ";") -notcontains $BinDirectory) {
            $UpdatedPath = if ($UserPath) { "$UserPath;$BinDirectory" } else { $BinDirectory }
            [Environment]::SetEnvironmentVariable("Path", $UpdatedPath, "User")
        }
        $env:Path = "$env:Path;$BinDirectory"
    }
    Write-Host "Agent Factory $CleanVersion installed at $Target"
    if ($env:AGENT_FACTORY_NO_SETUP -eq "1") {
        Write-Host "Open a new terminal, then run: agent-factory setup"
    } else {
        Write-Host "Opening local setup. Provider keys stay on this device."
        & $Binary setup
        if ($LASTEXITCODE -ne 0) { throw "Agent Factory setup failed" }
    }
} finally {
    Remove-Item -Recurse -Force $Temporary -ErrorAction SilentlyContinue
}
