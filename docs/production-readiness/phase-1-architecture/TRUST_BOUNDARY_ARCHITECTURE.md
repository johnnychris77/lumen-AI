# LPR-DIR-012 — Trust Boundary Architecture

For each boundary: trusted side, untrusted side, validation, authentication,
authorization, tenant enforcement, sanitization, audit, failure behavior. Status
reflects the Phase 1 validation run (186/186 passed).

| # | Boundary | Untrusted → Trusted | Controls | Failure behavior | Status |
|---|---|---|---|---|---|
| 1 | User → Frontend | User → SPA | Input validation in UI; no secrets in client | Safe UI states | ✅ |
| 2 | Frontend → API | SPA → HTTP API | HTTPS; schema validation (pydantic); no direct DB | 422 on bad input | ✅ |
| 3 | API → Authenticated Principal | Request → typed principal | Token verify (JWT/OIDC); prod dev-token rejected | 401 fail-closed | ✅ `test_enterprise_auth` |
| 4 | Principal → Tenant Context | Principal → tenant | `TenantMembership` is authoritative; header cannot grant authority | 403 fail-closed | ✅ `test_directive_002_tenant_context` |
| 5 | Tenant Context → Authorization | Tenant → guard | `require_*` role/tenant guards before service | 403 fail-closed | ✅ `test_permission_authorization` |
| 6 | Authorization → Service | Guard → business logic | Guard precedes side effects | No side effect on deny | ✅ `test_high_risk_route_permission_guards` |
| 7 | Service → Database | Service → DB | Tenant-scoped queries; parameterized ORM | `/ready` DB hard-gate | ✅ `test_tenant_isolation` |
| 8 | Service → Object Storage | Service → storage | Access-controlled; integrity-hashed | Fail-closed reads | ✅ (foundation) |
| 9 | Candidate Model → Governed Workflow | Model output → workflow | Advisory only; safe unavailable-model states | No confident result on missing model | ✅ `test_candidate_model_training` |
| 10 | Human Reviewer → Final Disposition | Reviewer → disposition | Human authoritative; AI cannot finalize | No autonomous close | ✅ |
| 11 | System → Audit Chain | Action → audit | Hash-chained, append-only | Failed write ≠ auditable success | ✅ `test_audit_chain_verification` |
| 12 | Evidence Generation → Immutable Archive | Bundle → archive | Checksums; append-only | Incomplete bundle not promoted | ✅ `test_evidence_authorization_baseline` |
| 13 | External Integration → Internal Platform | Webhook/IdP → platform | Signature/JWKS verification; idempotency | Reject unverifiable | ✅ (OIDC/webhook suites) |

## Cross-boundary invariants

* **Authority flows one way:** untrusted input never elevates trust; a header may
  request but never grant tenant authority (boundary 4).
* **Fail-closed at every boundary:** denials produce no side effects.
* **Audit spans boundaries:** every governed cross-boundary action emits a
  tamper-evident audit event (boundary 11).
* **AI is inside the human-authority boundary:** model outputs cross into the
  workflow only as advisory input (boundaries 9–10).

## Findings

* **No CRITICAL trust-boundary defect.** All 13 boundaries have defined controls
  and fail-closed behavior, and the safety-critical ones (3–12) are test-verified.
* **MINOR:** external-integration signature verification and idempotency should be
  standardized and explicitly tested for every webhook (I-01 duplicate handler is a
  related cleanup).
