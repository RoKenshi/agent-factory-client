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

## Optional effectiveness telemetry

Remote telemetry is disabled by default. Upload requires both explicit local consent and active
server-side consent. The accepted schema is closed: event/run UUIDs, coarse task category and
locale, worker role, provider kind, model identifier, result, verification flag, token/tool counts,
duration, retry count, and cost only when its provenance is known.

This telemetry is pseudonymous because it is associated with an installation/account. It is not
described as anonymous. It cannot accept arbitrary properties or execution content. Disabling
consent stops uploads; queued events remain local until the user purges or re-enables them.

## Personal-data acceptance gate

The current pre-release control-plane implementation may process an OIDC email during sign-in.
That does not satisfy the intended data-minimization promise. Before a GA release, Agent Factory
must either remove email persistence and use an opaque authentication subject, or explicitly revise
this policy and obtain appropriate consent.

Network infrastructure such as GitHub, a CDN, or the control-plane host may process IP addresses and
security logs under their own policies. Agent Factory application logs must not retain request
bodies, authorization headers, source IPs, or telemetry payloads.

## Verification before GA

- canary secrets, paths, source fragments, and prompts fail schema validation;
- packet capture equals the documented event schema;
- provider keys never reach the control-plane host;
- account export/deletion and telemetry withdrawal are tested end to end;
- retention and small-cohort suppression are enforced server-side;
- the public statement matches deployed behavior.
