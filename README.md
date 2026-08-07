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
The installer then opens a local setup wizard. Set `AGENT_FACTORY_SKIP_SETUP=1` (or use
`-SkipSetup` on Windows) to postpone it.

## Run

```bash
agent-factory setup
```

The browser wizard manages multiple OpenRouter, DeepSeek, Ollama, or OpenAI-compatible profiles.
It verifies new and rotated keys, lets each role select a `provider + model` pair, and can disable
or delete profiles. Every credential version is stored separately in the operating-system
credential store, never in the local JSON. Active runs keep their original non-secret routing
snapshot when a key is rotated. Codex and Claude register automatically; other MCP hosts receive a
ready-to-paste configuration.

Normal setup is four decisions: provider, key, savings/balanced/quality mode, and detected coding
agent. Agent Factory assigns role models automatically. Exact model checkboxes, custom endpoints,
and manual role routing stay under Advanced settings. The same local page manages key replacement,
provider status, trial/account activation, and MCP connection.

After setup, the MCP host runs the executable with the `mcp` argument. That command starts the
local runtime automatically; no daemon command or local database setup is required:

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

Use `agent-factory open` to return to the dashboard. Personal preferences, bounded cache, and the
content-free sync outbox share one private `agent-factory.json`; durable statistics live in the
remote control plane when telemetry is explicitly enabled. No persistent SQLite database is used.

The optional Agent Factory account key is separate from the provider key. Enter it with
`agent-factory activate`; both secrets live as separate records in the OS credential store and are
reused after a reboot. The first 24 hours do not require an Agent Factory account key.

## Supported artifacts

- Linux x86-64 and ARM64
- Windows x86-64
- macOS Intel and Apple Silicon

Compiled binaries are distributed under [BINARY-LICENSE.md](BINARY-LICENSE.md). The readable
installer scripts in this repository are MIT licensed so anyone can audit how downloads and
checksums are handled.

Русское описание: [README.ru.md](README.ru.md). 中文说明：[README.zh-CN.md](README.zh-CN.md).
