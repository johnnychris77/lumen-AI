# LPR-DIR-014 — Authorization Security Review (Phase 3)

**Basis:** code inspection + live escalation tests at `f889d95`.

## Implemented controls (verified)

| Control | Implementation | Evidence |
|---|---|---|
| RBAC | `TenantMembership` is the authoritative role source; `require_tenant_roles` / `require_*` guards | `auth/tenant_membership.py` |
| Endpoint authorization | **1,593** `require_*` guard usages across `app/routes/*` | grep count |
| Guard-before-side-effect | Guards run as FastAPI dependencies before the handler body | `test_high_risk_route_permission_guards` |
| Authenticated-principal propagation | Typed principal (`security/principal.py`) derived per request; header cannot elevate | `security/principal.py` |
| Least privilege | Per-route role/permission requirements; default-deny (no guard → not a governed write) | route inventory (Phase 1) |
| Privilege-escalation defense | Header-role escalation rejected | `test_header_role_privilege_escalation` |

## Escalation testing (live)

The following passed **50/50** in this phase's subset:
- **Vertical escalation:** `test_header_role_privilege_escalation` — a client cannot
  elevate role via request headers.
- **High-risk routes:** `test_high_risk_route_permission_guards` — governance/export
  endpoints require the correct permission guard.
- **Permission model:** `test_permission_authorization`.
- **Horizontal escalation / cross-tenant object access:** covered by
  `test_tenant_isolation` + `test_directive_002_tenant_context` (see
  `TENANT_ISOLATION_REVIEW.md`).
- **Anonymous access:** protected/write routes require a typed principal → 401.

## Findings

### SEC-AUTHZ-01 (MEDIUM) — governance enforced in code vs policy (carryover B-02/AR-03)
Phase 1 recorded that some governance gates are policy-enforced rather than
universally code-enforced. Authorization *guards* are present and tested, but the
Production Readiness program should complete moving High-priority governance gates
into code (Phase 1 AR-03). Not a bypass — a defense-in-depth completeness item.

### SEC-AUTHZ-02 (OBSERVATION) — large public surface
93 PUBLIC endpoints (Phase 1 I-03); all 10 unauthenticated writes are
PUBLIC_BY_DESIGN and classification is regression-tested (0 UNKNOWN). Keep the
PUBLIC set under review; the one exception where "public write" is a real risk is
the **webhook fail-open** (tracked as the CRITICAL SEC-C-01, not an authz-guard
defect but an input-authentication gap).

## Assessment
Authorization is **strong and test-verified**: default-deny, explicit guards before
side effects, header cannot grant authority, vertical/horizontal escalation
defended. No authorization **bypass** was found. The open items are enforcement
*completeness* (governance-in-code) and the separately-tracked webhook input-auth
CRITICAL.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| SEC-AUTHZ-01 | MEDIUM | Complete governance-gate code enforcement (carryover AR-03) |
| SEC-AUTHZ-02 | OBSERVATION | Large PUBLIC surface — keep under review (0 UNKNOWN) |
