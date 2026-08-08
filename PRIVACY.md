# Privacy contract

Last updated: 2026-08-06. This document describes the intended GA contract. Production downloads
must not be published until automated tests and a manual review confirm it.

## Data that stays local

Agent Factory must never transmit to its control plane:

- model-provider keys, account tokens, or authorization headers;
- source code, prompts, model responses, diffs, patches, filenames, repository names, or paths;
- terminal output, command arguments, environment variables, or error text;
- OS credential-store values.

The local runtime sends provider requests directly to the OpenAI-compatible endpoint configured by
the user. The Agent Factory control plane is not an inference proxy.

## Required daily effectiveness statistics

Registered use requires acceptance of one content-free statistics sync per 24 hours. The exact
boundary is shown during onboarding and the accepted policy version is recorded per installation.
The accepted schema is closed: random event/run UUIDs, coarse task category and locale, worker role,
provider kind, model identifier, result category, verification flag, token/tool counts, duration,
retry count, and cost only when its provenance is known.

This telemetry is pseudonymous because it is associated with an installation/account. It is not
described as anonymous. It cannot accept arbitrary properties or execution content. Failed uploads
remain in the local JSON queue. A registered installation has a documented offline grace period;
after it expires, pending statistics block only new work until sync succeeds. Running work is never
interrupted. Withdrawing the terms stops uploads and continued registered use after that grace.

## Identity and service providers

RoKenshi operates Agent Factory. Privacy, account and deletion requests may be sent to
`rouronikenshi@gmail.com`. Google identity tokens are validated in memory; the application persists
an opaque issuer/subject pair and does not persist the Google email claim. Cloudflare delivers the
public edge, AWS runs the application, Neon stores PostgreSQL data, Google provides identity and
GitHub distributes releases. These providers may process network and security metadata under their
own terms and may operate internationally.

Raw effectiveness events are retained for 90 days and body-free security audit records for 365
days. The account dashboard supports analytics export and deletion. Users may request access,
correction, restriction, portability or deletion through the contact above and may complain to
their local supervisory authority.

Network infrastructure such as GitHub, a CDN, or the control-plane host may process IP addresses and
security logs under their own policies. Agent Factory application logs must not retain request
bodies, authorization headers, source IPs, or telemetry payloads.

## Verification before GA

- canary secrets, paths, source fragments, and prompts fail schema validation;
- packet capture equals the documented event schema;
- provider keys never reach the control-plane host;
- account export/deletion and statistics-terms withdrawal are tested end to end;
- retention and small-cohort suppression are enforced server-side;
- the public statement matches deployed behavior.
