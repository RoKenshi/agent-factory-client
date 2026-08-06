# Security policy

Agent Factory is pre-release. Do not disclose a suspected vulnerability in a public issue when it
could expose credentials, user data, release-signing material, or an exploitable weakness.

Until a dedicated security mailbox is published, use GitHub's private vulnerability reporting for
this repository. Include the affected version/platform, reproduction steps, impact, and whether any
secret may have been exposed. Never include real provider or activation keys.

Release archives must have a matching entry in `SHA256SUMS`, and that file must have an Ed25519
signature that verifies against the repository-pinned `RELEASE-SIGNING-KEY.pem`. Beta binaries are
intentionally not Apple-notarized or Windows-Authenticode-signed. The installers authenticate the
project release before executing it; this is not a claim of operating-system publisher trust.

The pinned release-key SHA-256 fingerprint is
`beffec8ae3d1e3f614f81b441261176ab02b8bd800ac791eddaaf06d0da7de29`.
