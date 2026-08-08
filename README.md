# Agent Factory downloads

Public download and verification hub for Agent Factory — a local MCP delegation runtime for coding
agents.

This repository contains transparent installer scripts, privacy/security documentation, release
checksums, and compiled release binaries. It does **not** contain the proprietary Agent Factory
engine or control-plane source code.

> Pre-release: archives have project-level release signatures, but the binaries are not yet backed
> by Apple notarization or Windows Authenticode. Do not call a release GA until those platform
> signing and privacy acceptance gates pass.

## What Agent Factory never receives

- model-provider API keys;
- source code, prompts, diffs, repository names, or filesystem paths;
- terminal output or model responses;
- local environment variables or OS credential-store contents.

Provider keys stay on the user's machine and are sent only from the local runtime to the provider
endpoint selected by that user. Registered use requires one schema-limited, content-free statistics
batch per day. The installer discloses this before activation; it never includes execution content.

Read the exact contract in [PRIVACY.md](PRIVACY.md) and report vulnerabilities according to
[SECURITY.md](SECURITY.md).

## Install

One pasted command downloads the readable installer and runs it. Inspect `install.sh` or
`install.ps1` between the two operations when your security policy requires review.

### Linux and macOS

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh && sh install.sh
```

Published macOS releases are also available from the project tap:

```bash
brew install rokenshi/tap/agent-factory
```

### Windows PowerShell

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

Installers detect the operating system and architecture, download from the public GitHub Release,
verify the RSA-SHA256 signature over `SHA256SUMS`, verify the archive checksum, extract the complete
standalone directory, and run the binary's built-in `self-test`. The release public key is pinned in
both installers and published as [`RELEASE-SIGNING-KEY.pem`](RELEASE-SIGNING-KEY.pem).

After verification, the installer immediately opens the local setup UI. Re-running the same command
is safe: it re-verifies the release and refreshes the command link. For headless automation, set
`AGENT_FACTORY_NO_SETUP=1` and open setup later.

## Run

```bash
agent-factory setup
```

Setup opens the local UI, stores credentials in the current user's credential store, and registers
the selected MCP host. Never run setup with `sudo`.

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
