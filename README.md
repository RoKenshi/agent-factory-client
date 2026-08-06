# Agent Factory downloads

Public download and verification hub for Agent Factory — a local MCP delegation runtime for coding
agents.

This repository contains transparent installer scripts, privacy/security documentation, release
checksums, and compiled release binaries. It does **not** contain the proprietary Agent Factory
engine or control-plane source code.

> Beta releases are intentionally distributed without paid Apple notarization or Windows
> Authenticode. Release files are protected by signed checksums; the privacy acceptance gates in
> [PRIVACY.md](PRIVACY.md) remain mandatory before GA.

## What Agent Factory never receives

- model-provider API keys;
- source code, prompts, diffs, repository names, or filesystem paths;
- terminal output or model responses;
- local environment variables or OS credential-store contents.

Provider keys stay on the user's machine and are sent only from the local runtime to the provider
endpoint selected by that user. Remote effectiveness telemetry is off by default, schema-limited,
content-free, and requires separate local and server-side consent.

Read the exact contract in [PRIVACY.md](PRIVACY.md) and report vulnerabilities according to
[SECURITY.md](SECURITY.md).

## Install

Do not pipe remote scripts directly into a shell. Download and inspect the installer first.

### Linux and macOS

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh
less install.sh
sh install.sh
```

### Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1
Get-Content .\install.ps1
.\install.ps1
```

Installers detect the operating system and architecture, download from the public GitHub Release,
verify the Ed25519 signature over `SHA256SUMS`, verify the archive checksum, extract the complete
standalone directory, and run the binary's built-in `self-test`. Windows requires OpenSSL for the
same Ed25519 verification and reports, but does not require, Authenticode for the unsigned beta.

## Run

```bash
agent-factory serve
```

Configure the MCP host to run the same executable with the `mcp` argument:

```json
{
  "mcpServers": {
    "factory": {
      "command": "/absolute/path/to/agent-factory",
      "args": ["mcp"],
      "env": {"FACTORY_API_URL": "http://127.0.0.1:8787"}
    }
  }
}
```

## Supported artifacts

- Linux x86-64 and ARM64
- Windows x86-64
- macOS Intel and Apple Silicon

Compiled binaries are distributed under [BINARY-LICENSE.md](BINARY-LICENSE.md). The readable
installer scripts in this repository are MIT licensed so anyone can audit how downloads and
checksums are handled.

Русское описание: [README.ru.md](README.ru.md). 中文说明：[README.zh-CN.md](README.zh-CN.md).
