# LPR-DIR-026 — Release Configuration Certification (Workstream 5)

Configuration audit of the Release Candidate (`main @ 5c22345`), from the merged baseline.

| Area | RC state (verified) | Certification |
|---|---|---|
| **Environment variables** | Central `Settings` (`app/core/config.py`); `APP_ENV`/`ENVIRONMENT` drive prod detection (`main.py:169–176`). | ✅ **Certified consistent.** V1.1 adds the SEC-C-01 webhook env contract (below); no other env change. |
| **Secrets** | `main.py:180` `sys.exit`s if `SECRET_KEY == "dev-secret-change-in-production"` in production. API keys stored SHA-256-only. | ⚠️ **Certified with condition (SEC-H-01/02 OPEN):** dev fallbacks still present in `core/config.py`/`auth_simple.py`; `Settings.validate()` does not cover `SECRET_KEY`/webhook secrets. Startup prod guard mitigates the highest-risk path. |
| **OIDC** | `app/auth/jwt_validator.py`, `app/auth/jwks_validator.py` present and wired in `main.py`. | ✅ **Unchanged by V1.1** — no OIDC config delta in the RC. |
| **Tenant configuration** | `app/auth/tenant_membership.py`, `app/tenant_authz.py` (TenantMembership multi-tenancy; `require_tenant_*`). | ✅ **Unchanged by V1.1.** The SEC-C-01 fix *strengthens* tenant integrity on webhooks (server-bound tenant). |
| **Feature flags** | `ai_strict_no_placeholder`, coverage-gate flag, `DEMO_MODE`, etc. | ✅ **No new V1.1 flag.** |
| **Webhook configuration** | **New RC contract (from PR #119):** `WEBHOOK_SECRET_{SYSTEM}` (HMAC signing key; absent → 503), `WEBHOOK_TENANT_{SYSTEM}` (server-side tenant binding; absent → 503), `STRIPE_WEBHOOK_SECRET` (absent → 503, invalid → 400). `X-Tenant-Id` header no longer trusted. | ✅ **Certified — fail-closed.** ⚠️ **Operational action required:** operators MUST set these per environment/integration or the webhooks reject all traffic (the intended safe posture). |
| **Database migrations** | Alembic head `e7b2f4a86c31`; 13-file linear chain; **no V1.1 migration** (SEC-C-01 is code-only). | ✅ **Certified.** Forward migration path intact; no new schema to apply for V1.1. |
| **Rollback compatibility** | RC adds no migration and no schema change → **schema-compatible with the immediately prior baseline**. Code rollback = revert `f291186` (restores prior, *vulnerable*, fail-open webhooks — not recommended). Note **OPS-DEP-02 (no executed rollback drill) remains OPEN** — rollback is verified as *schema-safe by construction*, not by an executed drill. | ⚠️ **Certified schema-compatible; drill NOT executed.** |
| **Deployment configuration** | `deploy.yml` deploy steps only `echo` example kubectl (lines 148–186) — a **stub** (OPS-DEP-01). Single-worker Dockerfile (SCAL-01). k8s/Helm manifests present. | ⚠️ **NOT certified for production rollout** — deploy automation is a placeholder. |

## Determination

The Release Candidate's **application configuration is internally consistent and
certified**, with two conditions carried forward from the security verification:

1. **Operational config action (blocking for any real deployment):** the new fail-closed
   webhook secrets/tenant-binding env vars MUST be provisioned per environment.
2. **Production-deploy config remains OPEN** (OPS-DEP-01 stub, OPS-DEP-02 no rollback
   drill, SCAL-01 single worker) — infrastructure items, not closable from the repo.

Rollback is **schema-compatible by construction** (no migration in V1.1); an executed
rollback drill is still outstanding (OPS-DEP-02).
