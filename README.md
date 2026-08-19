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

For the stable channel:

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh && sh install.sh
```

An explicitly selected prerelease never changes `/releases/latest`; install v0.1.2 with:

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.sh && AGENT_FACTORY_VERSION=0.1.2 sh install.sh
```

Signed stable macOS releases are also available from the project tap:

```bash
brew install rokenshi/tap/agent-factory
```

### Windows PowerShell

For the stable channel:

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1; .\install.ps1
```

For the explicitly selected v0.1.2 prerelease:

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/install.ps1 -OutFile install.ps1; .\install.ps1 -Version 0.1.2
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

Normal setup is four decisions: provider, provider key, savings/balanced/quality mode, and the
detected coding agent. Agent Factory assigns role models automatically. Advanced settings exposes
exact model checkboxes, custom OpenAI-compatible endpoints, ordered per-role fallback routes, and
key replacement. New keys are verified before activation; active runs keep their original
non-secret routing snapshot when a key is rotated. Use `agent-factory open` to return to the local
dashboard. No persistent local database is required.

## Update and uninstall

Re-run the install command to verify and activate the newest release. Existing settings, provider
credentials and restart-safe run state are preserved. To remove only the binaries on Linux/macOS:

```bash
curl -fLO https://raw.githubusercontent.com/RoKenshi/agent-factory-client/main/uninstall.sh && sh uninstall.sh
```

On Windows, download and run `uninstall.ps1`. Uninstall preserves local state by default. Set
`AGENT_FACTORY_PURGE_STATE=1` on POSIX or pass `-PurgeState` on Windows only when local settings,
credentials and run history should also be deleted.

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

Every published version must contain all five archives plus `SHA256SUMS` and
`SHA256SUMS.sig`. This repository is the public distribution and verification hub; it does not
compile the proprietary runtime. Runtime binaries are built in the private engine release workspace
and copied into one staging directory using these exact names:

```text
agent-factory-vVERSION-linux-x86_64.tar.gz
agent-factory-vVERSION-linux-arm64.tar.gz
agent-factory-vVERSION-macos-x86_64.zip
agent-factory-vVERSION-macos-arm64.zip
agent-factory-vVERSION-windows-x86_64.zip
```

Before upload, sign `SHA256SUMS` with the offline release key and run the local, CI-independent
release gate:

```bash
tools/release-check.sh VERSION /absolute/path/to/release-directory
```

The gate verifies the pinned public key, installer behavior, the complete platform matrix, the
RSA-SHA256 signature, every archive checksum, bounded and collision-safe archive layouts, the
expected executable, and clean same-commit provenance in every embedded manifest.

Compiled binaries are distributed under [BINARY-LICENSE.md](BINARY-LICENSE.md). The readable
installer scripts in this repository are MIT licensed so anyone can audit how downloads and
checksums are handled.

Русское описание: [README.ru.md](README.ru.md). 中文说明：[README.zh-CN.md](README.zh-CN.md).
