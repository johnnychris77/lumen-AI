# LPR-DIR-012 — Interface & API Inventory

**Basis:** live route introspection via `scripts/generate_endpoint_inventory.py`
against `app.main:app` at `c9797b2`.

## HTTP API — quantitative baseline (observed)

| Metric | Value |
|---|---|
| Total endpoints | **1,912** |
| Write endpoints | 728 |
| Unauthenticated write endpoints | **10** (all PUBLIC_BY_DESIGN) |
| AUTHENTICATED | 882 |
| TENANT_SCOPED | 855 |
| PUBLIC | 93 |
| UNKNOWN classification | **0** |
| Route modules / decorators | 205 files / ~1,965 decorators |

The 10 unauthenticated writes are the governed PUBLIC_BY_DESIGN set (login, signed
webhooks, self-service registration, token refresh, device-key capture, stateless
compute) — verified by the Directive 002 governance regression test.

## Interface classes inventoried

| Interface class | Where | Auth | Tenant | Audit | Notes |
|---|---|---|---|---|---|
| HTTP endpoints | `app/routes/*` (205 modules) | Typed principal on protected/write | 855 tenant-scoped | Governed writes audited | 0 UNKNOWN |
| Internal service interfaces | `app/services/*` (489) | Caller-enforced | Yes | Yes | Business logic layer |
| Database repositories | SQLAlchemy models (147) | via service | Tenant columns | Yes | `RetainedImage` sole byte owner |
| Event interfaces | NEXUS event types / webhooks | Signature-verified (webhooks) | Yes | Yes | Async/publish |
| File formats / manifests | dataset/evidence manifests | n/a | Tenant | Checksummed | Reproducibility |
| CLI / scripts | `scripts/`, `validation/` | Local | n/a | n/a | Inventory generator, tooling |
| Scheduled processes | CI (ml-eval-nightly), monitoring | Service creds | Yes | Yes | Async |
| Report-generation interfaces | reporting/evidence release | Auth | Tenant | Yes | Governed artifacts |
| Model-execution interfaces | ML inference adapter | Auth | Tenant | Yes | Safe unavailable-model states |

## Per-interface attributes (representative)

For governed HTTP write endpoints: **owner** = domain team (ownership matrix);
**auth** = typed principal required; **authorization** = `require_*` guard;
**tenant enforcement** = `TenantMembership`; **request/response schema** = pydantic
models; **failure schema** = 401/403/422/409 fail-closed; **audit** = hash-chained
event; **deprecation** = tracked (e.g. header-fallback migration F1).

## Findings

| ID | Sev | Finding | Evidence | Action |
|---|---|---|---|---|
| I-01 | OBSERVATION | Duplicate endpoint path | Two handlers on `POST /api/billing/webhook` | Confirm intended handler; deprecate other |
| I-02 | MINOR | Deprecated interfaces present | Header-fallback routes (Directive 002 F1) | Complete migration in later phase |
| I-03 | OBSERVATION | Large public surface | 93 PUBLIC endpoints | Confirm each is intentionally public (0 UNKNOWN is reassuring) |
| I-04 | OBSERVATION | No live-published OpenAPI diff gate | OpenAPI generated; PR gate unconfirmed | Add schema-diff check in CI |

**No insecure/bypass/orphan endpoints surfaced:** 0 UNKNOWN classification, 10
unauthenticated writes all PUBLIC_BY_DESIGN, and privilege-escalation defenses
tested (`test_header_role_privilege_escalation`, `test_high_risk_route_permission_guards`
pass). Schema consistency is enforced by pydantic; versioning/deprecation is
tracked but not yet gated in CI (I-04).
