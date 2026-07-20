# DEPLOYMENT EXECUTION REPORT — LPR-DIR-031 / WP-2

**Commit:** `4299c40` · **Operator:** automated · **Attempt timestamp:** 2026-07-20T02:33Z.
**Precondition (WP-1):** a managed environment — **NOT provisionable in this context**
(`MANAGED_ENVIRONMENT_IMPLEMENTATION.md`, `evidence/PROVISIONING_PROBE.log`).

## 1. Objective
Execute deployment, startup, migrations, health checks, smoke tests; capture timestamps,
logs, deployment IDs, application version.

## 2. Result — NOT EXECUTED
No deployment target exists (docker daemon unreachable; no cluster; no cloud CLI). Therefore:
| Required capture | Value |
|---|---|
| Deployment ID | **none — no deploy occurred** |
| Timestamps of rollout | **none** |
| Application version on a deployed instance | **none** |
| Rollout / startup logs | **none** |
| Smoke-test result against a deployed URL | **none** |

**No deployment ID, timestamp, or log is fabricated.** Absence is reported as absence.

## 3. Genuinely-executed, related engineering evidence (does NOT substitute for a deploy)
- **App boots + serves in-process:** capability harness `§3` — `GET /health → 200
  {"status":"ok","version":"P11","environment":"development"}` (real app via TestClient),
  captured in `evidence/HARNESS_RUN.log` (2026-07-20T02:33:22Z, 6/6 pass).
- **Migrations run on PostgreSQL:** PR #122 CI job "Backend tests (PostgreSQL 16)" green —
  proves `alembic`/schema works on Postgres, though against an ephemeral CI service container,
  **not** a managed instance or a deployed release.
- **Deploy automation exists + is fail-closed:** `.github/workflows/deploy.yml`
  (`kubectl set image` → `rollout status`; reports NOT-CONFIGURED instead of faking success).

## 4. Exact procedure that WOULD produce the evidence
```
# with KUBE_CONFIG set + image published:
gh workflow run deploy.yml -f environment=staging      # or Actions > Run workflow
# capture: run URL, deployment ID, kubectl rollout status output, timestamps
kubectl -n lumenai get deploy lumenai -o jsonpath='{.metadata.uid} {.spec.template.spec.containers[0].image}'
curl -fsS https://<endpoint>/health                    # expect 200 {"status":"ok",...}  ← smoke test
```

## 5. Classification
| Item | Status |
|---|---|
| Deployment executed → healthy instance (OPS-DEP-01) | **NOT EXECUTED / OPEN** |
| Deploy automation artifact | **IMPLEMENTED (verified in DIR-030)** |
| App health primitive | **VERIFIED (in-process only)** |
