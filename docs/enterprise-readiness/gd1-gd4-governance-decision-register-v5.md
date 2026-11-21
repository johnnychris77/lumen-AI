# Governance Decision Register (v5 — Batch 6)

**PR #181 (DRAFT) · Issue #188** · supersedes v4 (preserved). **No decision is signed; no signed approval
exists anywhere in the repository or the issues read (#187, #188).** Issue #188 is "a work authorization for
isolated engineering and review preparation, not governance or release approval".

## Decisions engineering cannot make — STOPPED and reported
| ID | Decision (owner) | What engineering did instead (fail closed) | Blocked behaviour |
|---|---|---|---|
| GD-5 | Tenant selection by header only, or repeated claims (API/product owner) | header + equal claim (Batch 4/5 contract) | — |
| **GD-6** | Genesis curation: who may publish/reject **another** tenant's update; self-publishing; public vs pseudonymous publishers; filtering other publishers (network/clinical governance) | B6.1: unpublished = submitter only; cross-tenant review 404; identities redacted; foreign publisher filter 403 | cross-tenant moderation; foreign-publisher filtering; public publisher identity |
| **GD-7** | GuardianX ledger ownership model, attribution of history, retention, privileged reader (platform-security owner) | B6.2: read gate on audit-trail ownership; legacy unprovable entries readable by no tenant; dry-run classifier only | ownership migration; release of quarantined entries; platform-wide reader |
| GD-8 | Commercial platform-wide view (commercial + security) | UI does not offer it | UI platform view |
| GD-9 | Manufacturer IAM: grant/revoke authority, proofing, roles, expiry, API (IAM owner) | grants gated closed; audited revocation service (no route); expiry enforced | granting memberships; HTTP lifecycle API |
| AUTH-1 | Legacy users-table login (authentication owner) | disabled, logged | users-table login |
| AUTH-2 | Accept `users.role` application + inventory before deploy (authentication owner) | applied per documented order | — (deployment check pending) |
| PA-1 | Platform-admin / dev-token exception (platform security) | unchanged, logged | — |
| CLIN-1 | Legacy attribution (GD-3 baselines, GD-7 ledger) (clinical operations) | quarantined | release of quarantined records |
| HIST | Historical cross-tenant access investigation (incident response; needs production access) | plan only | the investigation itself |

**Disposition: HOLD / NO-GO.**
