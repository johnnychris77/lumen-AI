# LPR-DIR-025 — Configuration Audit (Workstream 5)

Audit of the release baseline (`main` @ `3c30d8a`).

| Area | Baseline state | Finding |
|---|---|---|
| **Migrations** | Alembic migrations present (baseline + backfills from prior sprints) | ✅ No migration change is pending from V1.1 (the SEC-C-01 fix is code-only, adds no schema). |
| **Configuration** | Central `Settings` exists; `main.py` startup guards `sys.exit` on default `SECRET_KEY` and require explicit `AUTH_MODE` in production | ⚠️ `Settings.validate()` still omits `SECRET_KEY` and webhook secrets (SEC-H-02 OPEN on baseline). |
| **Secrets** | SHA-256-only API-key storage; env-driven secrets | ⚠️ Hardcoded dev fallbacks still present in `core/config.py` / `auth_simple.py` (SEC-H-01 OPEN). **Webhook signing secrets are still optional** on the baseline — the fail-open path (SEC-C-01) is live. |
| **Feature flags** | `ai_strict_no_placeholder`, coverage-gate flag, `DEMO_MODE`, etc. | ✅ No new V1.1 flag introduced on the baseline (the SEC-C-01 fix adds env vars `WEBHOOK_SECRET_{SYSTEM}` / `WEBHOOK_TENANT_{SYSTEM}` / enforced `STRIPE_WEBHOOK_SECRET`, but **that config contract is on PR #119, not merged**). |
| **Deployment configuration** | Dockerfile (single worker), Helm/k8s manifests, `deploy.yml` | ⚠️ `deploy.yml` still **echoes** kubectl (OPS-DEP-01); single-worker Dockerfile (SCAL-01); k8s `replicas:2` vs Helm `replicas:1` drift (ENV-01) — all **unchanged on baseline**. |

## Determination
The baseline configuration is **internally consistent but carries the known open
security/deploy gaps**. Critically, the **webhook signing-secret + server-side tenant
binding config contract required to close SEC-C-01 is NOT on the baseline** (it ships
with PR #119). No merged V1.1 change alters migrations, flags, or deployment config.
