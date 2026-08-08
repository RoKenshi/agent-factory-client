$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Temporary = Join-Path ([IO.Path]::GetTempPath()) ("agent-factory-test-" + [guid]::NewGuid())
$Server = $null

try {
    $Version = "9.8.7"
    $Directory = "agent-factory-v$Version-windows-x86_64"
    $Release = Join-Path $Temporary "release"
    $Distribution = Join-Path (Join-Path $Temporary "staging") $Directory
    New-Item -ItemType Directory -Force -Path $Release, $Distribution | Out-Null

    $Source = @'
using System;
public static class Program {
    public static int Main(string[] args) {
        Console.WriteLine("{\"status\":\"ok\"}");
        return args.Length == 1 && args[0] == "self-test" ? 0 : 2;
    }
}
'@
    $Binary = Join-Path $Distribution "agent-factory.exe"
    $SourcePath = Join-Path $Temporary "Program.cs"
    [IO.File]::WriteAllText($SourcePath, $Source, [Text.UTF8Encoding]::new($false))
    & powershell.exe -NoProfile -NonInteractive -Command "Add-Type -Path '$SourcePath' -OutputAssembly '$Binary' -OutputType ConsoleApplication"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Binary)) {
        throw "Failed to build the Windows installer test stub"
    }
    $Asset = "$Directory.zip"
    $Archive = Join-Path $Release $Asset
    Compress-Archive -Path $Distribution -DestinationPath $Archive
    $Digest = (Get-FileHash -Algorithm SHA256 $Archive).Hash.ToLowerInvariant()
    $Checksums = Join-Path $Release "SHA256SUMS"
    [IO.File]::WriteAllText($Checksums, "$Digest  $Asset`n", [Text.UTF8Encoding]::new($false))

    $SigningKey = [Security.Cryptography.RSA]::Create(2048)
    $Parameters = $SigningKey.ExportParameters($true)
    $Signature = $SigningKey.SignData(
        [IO.File]::ReadAllBytes($Checksums),
        [Security.Cryptography.HashAlgorithmName]::SHA256,
        [Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    [IO.File]::WriteAllBytes((Join-Path $Release "SHA256SUMS.sig"), $Signature)
    $Modulus = [Convert]::ToBase64String($Parameters.Modulus)

    $Probe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $Probe.Start()
    $Port = ([Net.IPEndPoint]$Probe.LocalEndpoint).Port
    $Probe.Stop()
    $Server = Start-Process python -ArgumentList @(
        "-m", "http.server", "$Port", "--bind", "127.0.0.1", "--directory", $Release
    ) -PassThru -WindowStyle Hidden
    $Base = "http://127.0.0.1:$Port"
    for ($Attempt = 0; $Attempt -lt 20; $Attempt++) {
        try {
            Invoke-WebRequest "$Base/SHA256SUMS" | Out-Null
            break
        } catch {
            Start-Sleep -Milliseconds 100
        }
    }

    $InstallRoot = Join-Path $Temporary "AgentFactory"
    $env:AGENT_FACTORY_NO_SETUP = "1"
    & (Join-Path $Root "install.ps1") -Version $Version -InstallRoot $InstallRoot `
        -ReleaseBaseUrl $Base -ReleasePublicKeyModulus $Modulus -NoPathUpdate
    if ($LASTEXITCODE -ne 0) { throw "Installer returned $LASTEXITCODE" }
    $Command = Join-Path (Join-Path $InstallRoot "bin") "agent-factory.cmd"
    if (-not (Test-Path $Command)) { throw "Installer did not create the command shim" }
    & (Join-Path $Root "install.ps1") -Version $Version -InstallRoot $InstallRoot `
        -ReleaseBaseUrl $Base -ReleasePublicKeyModulus $Modulus -NoPathUpdate
    if ($LASTEXITCODE -ne 0) { throw "Idempotent installer returned $LASTEXITCODE" }

    [IO.File]::WriteAllText((Join-Path $Release "SHA256SUMS.sig"), "tampered")
    $Rejected = $false
    try {
        & (Join-Path $Root "install.ps1") -Version $Version `
            -InstallRoot (Join-Path $Temporary "tampered-install") `
            -ReleaseBaseUrl $Base -ReleasePublicKeyModulus $Modulus -NoPathUpdate
    } catch {
        $Rejected = $_.Exception.Message -match "signature verification failed"
    }
    if (-not $Rejected) { throw "Installer accepted a tampered signature" }

    & (Join-Path $Root "uninstall.ps1") -InstallRoot $InstallRoot
    if (Test-Path $InstallRoot) { throw "Uninstaller did not remove the install root" }
} finally {
    if ($Server) { Stop-Process -Id $Server.Id -Force -ErrorAction SilentlyContinue }
    if (Test-Path $Temporary) { Remove-Item -Recurse -Force $Temporary }
}
