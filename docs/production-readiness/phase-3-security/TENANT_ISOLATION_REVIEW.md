# LPR-DIR-014 — Tenant Isolation Review (Phase 3)

**Basis:** code inspection + live isolation tests at `f889d95`.

## Isolation model (verified)

| Layer | Enforcement | Evidence |
|---|---|---|
| Tenant resolution | `TenantMembership` authoritative; a request header may *request* a tenant context but never *grant* authority | `auth/tenant_membership.py`, `security/tenant_context.py` |
| Propagation | Typed principal carries tenant; services receive it explicitly | `security/principal.py` |
| Repository filters | Tenant-scoped queries; models carry tenant columns | Phase 1 data-authority review |
| Storage isolation | Object storage access-controlled + integrity-hashed | foundation |
| Audit isolation | `enterprise_audit_service` writes tenant-scoped, hash-chained events | `test_audit_chain_verification` |
| Report/dataset/Digital-Twin isolation | Tenant-scoped SoRs (`DatasetRegistryEntry`, `digital_twin_id`, reporting) | Phase 1 |

## Live testing (passed 50/50 subset)
- `test_tenant_isolation` — cross-tenant reads/writes blocked (403 fail-closed).
- `test_directive_002_tenant_context` — header cannot grant tenant authority;
  membership is authoritative.

## Findings

### SEC-TEN-01 (CRITICAL, cross-reference) — webhook cross-tenant injection
The one isolation-relevant CRITICAL is the external-integration webhook fail-open
(SEC-C-01 / Phase 1 AR-15): `integrations.webhook_ingest` derives `tenant_id` from
the attacker-controllable `X-Tenant-Id` header and, when `WEBHOOK_SECRET_{SYSTEM}`
is unset, accepts unsigned payloads — permitting **cross-tenant data injection on a
public write**. This is the exception to the otherwise-clean isolation model: it is
an *unauthenticated ingress* path where the normal "header cannot grant tenant
authority" invariant is bypassed because there is no authenticated principal and no
signature to bind the tenant. **Blocking pre-production.** Full detail in the risk
register and `TRUST_BOUNDARY_VALIDATION.md`.

### SEC-TEN-02 (LOW/OBSERVATION) — cache isolation not separately evidenced
Redis/RQ are configured; per-tenant cache-key namespacing was **not separately
verified** in this pass. No shared-cache cross-tenant leak was found, but a
dedicated cache-isolation test is recommended (penetration-test candidate).

## Assessment
For the **authenticated** application surface, tenant isolation is **strong and
test-verified** (membership-authoritative, fail-closed, header cannot elevate). The
**single** isolation defect is the unauthenticated webhook ingress (SEC-C-01),
which must be closed before production. Cache-isolation verification is a
recommended pen-test item.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| SEC-TEN-01 | CRITICAL | Webhook cross-tenant injection via `X-Tenant-Id` + fail-open (=SEC-C-01/AR-15) |
| SEC-TEN-02 | OBSERVATION | Cache per-tenant isolation not separately evidenced (pen-test candidate) |
