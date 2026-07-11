# Project Infinity — Certification Program & Developer Sandbox

LumenAI OS v5.0, Sections 7 & 9.

## Certification Program (Section 7)

Reuses Project Forge's `WorkflowApprovalChain`/`WorkflowApprovalInstance`
(v4.1, `forge_approval_service.py`) a **third** time — already reused by
Athena (v4.8) and Phoenix's 6-stage Continuous Validation (v4.9). The
chain's `steps_json` is a generic ordered list of role strings, not a
fixed-length schema, so Infinity instantiates it with the seven named
gates:

```
Security → Performance → Clinical Safety → Explainability → Accessibility → Documentation → Governance
```

A rejection at any gate ends certification immediately (Forge's existing
`decide_step` behavior) and the listing's `certification_status` becomes
`rejected` — it can never reach `certified` without an explicit approval
recorded at every one of the seven gates.

```
POST /api/infinity/certification/listings/{id}/start
POST /api/infinity/certification/listings/{id}/advance
GET  /api/infinity/certification/listings/{id}
```

## Developer Sandbox (Section 9)

No isolated dev/test/validation/certification environment concept
existed anywhere in this codebase before Infinity — `pilot_config.py`/
`pilot_error_log.py` (v1.9) are a different, older "pilot" concept
(per-tenant sales-pilot configuration), not a developer sandbox.

Every `DeveloperSandboxSession` is scoped to a synthetic
`sandbox_tenant_id` generated with a fixed, unmistakable `sandbox-`
prefix (`infinity_sandbox_service.is_sandbox_tenant` distinguishes it
from any real tenant_id) — this guarantees no production impact, since
every other tenant-scoped query in this codebase filters by an exact
`tenant_id` match and a sandbox tenant_id can never coincide with a real
one.

Sessions expire on a real timer (`expires_at`) and are marked `expired`
— never silently treated as still active — via
`expire_stale_sessions`, intended to run as a periodic maintenance task.

```
POST /api/infinity/sandbox/sessions
GET  /api/infinity/sandbox/sessions?developer_account_id=...
GET  /api/infinity/sandbox/sessions/{id}
POST /api/infinity/sandbox/sessions/{id}/terminate
POST /api/infinity/sandbox/sessions/expire-stale
```
