# LPR-DIR-022 — Security Remediation Report (Phase 2)

## SEC-C-01 (CRITICAL) — RESOLVED (implementation + tests + regression)

### The defect (verified across Phases 1–6)
Two public webhook ingress points **failed open and trusted attacker-controlled
tenant input**:

1. **External integrations** — `app/routes/integrations.py::webhook_ingest`: when
   `WEBHOOK_SECRET_{SYSTEM}` was unset, HMAC verification was **skipped entirely**, and
   the tenant was read from the client-supplied `X-Tenant-Id` header. → an
   unauthenticated attacker could write arbitrary events into **any tenant**.
2. **Billing** — `app/routes/billing.py::stripe_webhook` (the live handler; a second
   shadowed copy exists in `billing_webhooks.py`): when the Stripe secret was unset the
   raw payload was parsed **without verification**, and the tenant came from **unverified
   payload metadata**. → an attacker could flip **any tenant's** subscription state.

### The fix (fail-closed + server-bound tenant)
- **Integrations webhook:** a missing `WEBHOOK_SECRET_{SYSTEM}` now returns **503**
  (rejection, not bypass); the HMAC signature is always verified (**401** on mismatch);
  the tenant is taken **only** from server-side `WEBHOOK_TENANT_{SYSTEM}` config
  (**503** if unset) — the `X-Tenant-Id` header is **no longer read at all**.
- **Billing webhook:** a missing `STRIPE_WEBHOOK_SECRET` now returns **503**; an
  invalid signature returns **400** (previously a silent 200); the secret is read at
  request time; only the **signature-verified (Stripe-signed)** payload's metadata is
  trusted for the tenant. The shadowed `billing_webhooks.py` handler was hardened the
  same way for defense in depth.

### Verification (automated tests)
`tests/test_p17_recommendations.py::TestWebhook` and
`tests/test_p14_recommendations.py::TestBillingWebhooks`, rewritten to assert the
secure behavior:
- no secret → **503** (both webhooks);
- bad signature → **401** (integrations) / **400** (billing);
- no server-side tenant binding → **503** (integrations);
- valid signed request → **200** and processed;
- **definitive proof** (`test_webhook_binds_server_tenant_not_client_header`): with a
  valid signature **and** an attacker `X-Tenant-Id: tenant-attacker` header, the stored
  record's `tenant_id == "tenant-server-bound"` (server config), **never** the header.

**Result: the tests that previously encoded the vulnerability now encode the fix, and
pass.** SEC-C-01 is closed for the code paths that carried it.

## Remaining HIGH security findings

| ID | Status | Note |
|---|---|---|
| SEC-H-01 (secret fallbacks) | **PARTIAL** | `main.py` already `sys.exit`s in production if `SECRET_KEY` is the default; removing the dev fallbacks in `core/config.py`/`auth_simple.py` is recommended follow-up |
| SEC-H-02 (startup secret validation) | **PARTIAL** | Production startup guards for `SECRET_KEY` and `AUTH_MODE` exist; webhook secrets now fail closed per-request; folding `SECRET_KEY` + webhook secrets into a single invoked `Settings.validate()` is recommended follow-up |

## Validation of the security surface (unchanged, re-affirmed)
- **Authentication:** OIDC/JWKS enterprise path with explicit algorithm allowlist.
- **Authorization:** 1,593 `require_*` guards; `TenantMembership` authoritative.
- **Tenant isolation:** header cannot grant tenant authority; **now also true for
  webhooks** (this fix).
- **Audit:** hash-chained tamper-evident; webhook events still audited.
- **Billing ingress / external endpoints:** now fail-closed (this fix).

## Determination
**SEC-C-01 (the sole CRITICAL) is RESOLVED** with implementation, automated tests, and
regression. The remaining security HIGHs are **partially mitigated** (production
startup guards) with clear, non-pilot-blocking follow-ups. No security finding was
hidden or downgraded.
