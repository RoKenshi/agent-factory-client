# Client release contract

This repository verifies and publishes Agent Factory downloads. It deliberately does not contain
the proprietary runtime source or a binary compiler. A release starts only after the engine release
workspace has produced the complete standalone artifact matrix.

## Required v0.1.2 matrix

The staging directory must contain exactly these archives, with `VERSION` replaced by `0.1.2`:

```text
agent-factory-vVERSION-linux-x86_64.tar.gz
agent-factory-vVERSION-linux-arm64.tar.gz
agent-factory-vVERSION-macos-x86_64.zip
agent-factory-vVERSION-macos-arm64.zip
agent-factory-vVERSION-windows-x86_64.zip
SHA256SUMS
SHA256SUMS.sig
```

Each archive has one same-named top-level directory. POSIX archives contain an executable
`agent-factory`; the Windows archive contains `agent-factory.exe`. Every binary must report the
release version from `agent-factory version` and pass `agent-factory self-test` without network or
provider credentials.

## Pre-publish gate

1. Run engine unit, integration, dashboard and offline MCP tests at the release commit.
2. Build each target from that exact commit and record the source revision and toolchain version.
3. For GA, sign the macOS binaries with Developer ID and complete Apple notarization, and sign the
   Windows binary with Authenticode before creating the archives. Until those credentials exist,
   require manifests to report only `adhoc` or `none` and publish exclusively as a GitHub
   prerelease with `latest=false`; an unsigned build can never be GA or stable/latest.
4. Run `version` and `self-test` on each native target. Cross-archive inspection alone is not a
   substitute for native execution.
5. Generate `SHA256SUMS` over exactly the five archives and sign it with the offline release key.
6. Run the client repository's independent gate:

   ```bash
   tools/release-check.sh 0.1.2 /absolute/path/to/staging
   ```

7. Do not create or move the Git tag until the gate passes. The tag, binary version and archive
   version must be identical.

The independent gate accepts a local staging directory only when it contains those seven regular,
non-symlink files and nothing else. It also opens every archive and requires exactly one root
`MANIFEST.json` with the exact version and platform, `releasable=true`, `source_dirty=false`, and
equal lowercase 40-character `source_commit`/`source_revision` values. All five manifests must name
the same commit. Each manifest must also use schema 1, name the exact executable, report a non-empty
Python version, and use the prerelease signature state `adhoc` or `none`. Archive validation is
bounded by member-count and total-uncompressed-size limits, rejects duplicate and Unicode/casefold
portable-path collisions, and reads every ZIP member to verify its CRC. The gate additionally
validates installer behavior, the RSA-SHA256 signature, checksums, safe archive layouts, executable
presence and POSIX execute bits. It does not replace native code-signing or runtime checks.

## Local prerelease publication

GitHub Actions are not part of the publication path. Run the local publisher from a clean `main`
checkout after the seven-file staging directory has passed the pre-publish gate. Its default mode is
a dry-run:

```bash
python3 tools/publish_release.py \
  --version 0.1.2 \
  --tag v0.1.2 \
  --staging /absolute/path/to/staging
```

The publisher runs `tools/release-check.sh`, fetches `origin`, requires local `main` to exactly match
the freshly fetched `origin/main`, verifies the authenticated `gh` repository, and refuses existing
tags or releases. The dry-run prints a revision-bound confirmation value. Only after reviewing that
plan may the same command be rerun with `--execute` and the exact printed value:

```bash
export AGENT_FACTORY_PUBLISH_CONFIRM='publish:RoKenshi/agent-factory-client:v0.1.2:<exact-client-sha>'
python3 tools/publish_release.py \
  --version 0.1.2 \
  --tag v0.1.2 \
  --staging /absolute/path/to/staging \
  --execute
```

Execution snapshots the already verified seven files and creates only a GitHub prerelease with
`latest=false`. It never creates a GA/latest release, replaces an existing tag or asset, or reads,
stores, signs with, or modifies the private release key.

The immutable Git tag always equals `v` plus the binary/archive version. Beta status is represented
only by GitHub's `prerelease=true` and `latest=false` metadata, never by decorating the tag. Because
the tag and its seven assets are immutable, a later GA must use a new version and new tag; this
prerelease is never promoted or overwritten in place.

## Native smoke matrix

| Target | Required smoke |
| --- | --- |
| macOS ARM64 | Installer, `version`, `self-test`, `codesign --verify`, documented Gatekeeper result |
| macOS x86-64 | Same checks on Intel hardware or the verified Rosetta compatibility lane |
| Linux ARM64 | Installer, `version`, `self-test`, MCP process start/stop |
| Linux x86-64 | Installer, `version`, `self-test`, MCP process start/stop |
| Windows x86-64 | PowerShell installer, `version`, `self-test`, explicit Authenticode status |

Run installers with temporary install and state roots and with setup suppressed. After the smoke,
run the matching uninstaller and confirm it preserves state by default. Run the destructive purge
case only against an isolated disposable state directory.

## Public smoke and rollback

Publish as a pre-release first. From a clean machine for every target, install the exact version
from the release URL using the public pinned key and repeat the native smoke matrix. Verify that a
modified signature and a modified archive are rejected. Do not promote an unsigned release in
place; after platform signing is available, publish a new immutable version and only then update
stable installation channels.

If any platform fails, keep the release in pre-release state, do not move a stable channel, and
publish a new version after rebuilding. Never replace an archive under an existing version because
already installed copies are intentionally treated as immutable.
