# Security policy

Agent Factory is pre-release. Do not disclose a suspected vulnerability in a public issue when it
could expose credentials, user data, release-signing material, or an exploitable weakness.

Until a dedicated security mailbox is published, use GitHub's private vulnerability reporting for
this repository. Include the affected version/platform, reproduction steps, impact, and whether any
secret may have been exposed. Never include real provider or activation keys.

Release archives must have a matching entry in `SHA256SUMS`. Production releases additionally
require Apple notarization, Windows Authenticode, and signed Linux checksum/package metadata.
