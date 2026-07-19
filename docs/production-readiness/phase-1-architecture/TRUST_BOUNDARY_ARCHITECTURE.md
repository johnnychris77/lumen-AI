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
| 11 | System → Audit Chain | Action → audit | Hash-chained, append-only (verified). **Not atomic with the business write** — see finding TB-01 | Chain verifies once written; but a business commit that precedes a failing audit write leaves data committed without a chain entry | ⚠️ Append-only verified (`test_audit_chain_verification`); write/audit **atomicity is a gap** |
| 12 | Evidence Generation → Immutable Archive | Bundle → archive | Checksums; append-only | Incomplete bundle not promoted | ✅ `test_evidence_authorization_baseline` |
| 13 | External Integration → Internal Platform | Webhook/IdP → platform | Signature/JWKS verification **only when the relevant secret is configured** — see finding TB-02 | OIDC/JWT: reject unverifiable ✅. **Webhooks fail OPEN when their secret is unset** (no startup validation): `integrations.webhook_ingest` and `billing.stripe_webhook` accept unsigned payloads; `webhook_ingest` also derives tenant from the `X-Tenant-Id` header | ⚠️ OIDC verified; **webhook signature is conditional — cross-tenant injection risk when unconfigured** |

## Cross-boundary invariants

* **Authority flows one way:** untrusted input never elevates trust; a header may
  request but never grant tenant authority (boundary 4).
* **Fail-closed at every boundary:** denials produce no side effects.
* **Audit spans boundaries:** every governed cross-boundary action emits a
  tamper-evident audit event (boundary 11).
* **AI is inside the human-authority boundary:** model outputs cross into the
  workflow only as advisory input (boundaries 9–10).

## Findings

Boundaries 3–10 and 12 (auth, tenant, authorization, service, storage, model,
human review, evidence archive) are clean and test-verified. Two boundaries carry
verified defects surfaced during PR review (code-confirmed):

* **TB-02 (CRITICAL) — external integration webhook fails open.**
  `app.routes.integrations.webhook_ingest` verifies HMAC only when
  `WEBHOOK_SECRET_{SYSTEM}` is set; otherwise it accepts an arbitrary payload,
  takes the tenant from the attacker-controllable `X-Tenant-Id` header, and commits
  event records. `app.routes.billing.stripe_webhook` similarly parses unsigned JSON
  when `STRIPE_WEBHOOK_SECRET` is unset. There is **no startup validation** requiring
  these secrets, so a valid deployment configuration permits **cross-tenant data
  injection** on a public write. This corrects boundary 13's prior "✅" assertion.
* **TB-01 (MAJOR) — audit not atomic with the write.** Several write paths (e.g.
  `integrations.webhook_ingest`) `db.commit()` business data *before* calling the
  audit writer; if the audit insert fails, business data remains committed with no
  chain entry — so boundary 11's "failed write ≠ auditable success" is not
  guaranteed at the write/audit boundary.

Both are pre-existing platform behaviors (this PR changes only documentation) and
are added to `ARCHITECTURE_RISK_REGISTER.md`. TB-02 is the reason the
critical-findings count and freeze decision are revised (see the Phase 1 report).
