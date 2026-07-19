# LPR-DIR-016 — Deployment Operations Review (Phase 5)

**Basis:** `.github/workflows/*`, Dockerfile, compose/Helm/k8s/render inspection at
baseline `bd94bc5`.

## CI/CD pipeline (11 workflows)

| Workflow | Purpose | Status |
|---|---|---|
| `ci.yml` | lint (ruff) + backend tests (SQLite/PG16) + frontend build + secret/dep scan | ✅ gating |
| `backend-compliance-tests.yml`, `enterprise-quality-gate.yml`, `pilot-zero-gate.yml` | compliance/quality gates | ✅ gating |
| `security-baseline.yml`, `security-hardening-validation.yml` | pip-audit/npm/bandit/safety/secret-scan | ✅ gating |
| `ml-eval-nightly.yml` | scheduled ML eval | ✅ scheduled |
| `release-ghcr.yml` | **on tag push** → build + push GHCR images (`lumen-ai-api`, `lumen-ai-worker`) tagged `${version}` + `latest` | ✅ real image release + versioning |
| `deploy.yml` | build image + **"deploy-staging"** | ⚠️ **stub (see OPS-DEP-01)** |
| `staging-deploy.yml` | staging deploy | ⚠️ verify wiring |
| `github-pages-demo.yml` | public demo | ✅ |

## Findings

### OPS-DEP-01 (MAJOR) — production deployment is not actually automated
`deploy.yml`'s `deploy-staging` job (gated to `main`/`workflow_dispatch`, environment
`staging`) **`echo`s the kubectl commands** (`echo "  kubectl set image ..."`,
`echo "  kubectl rollout status ..."`) rather than executing them. So the pipeline
**builds and tests** but the actual rollout is a **documented manual step, not an
executed, verified deployment**. Production deployment automation + post-deploy
verification must be wired before production operation.

### OPS-DEP-02 (MAJOR) — no production rollback drill
Per the existing `docs/general-availability/OPERATIONS_RUNBOOK.md`, the **only
rollback script that runs is `scripts/public-demo-rollback-local.sh`** (demo landing
page). **No real application/DB rollback drill has been executed.** Image-tag
rollback is *possible* (GHCR keeps versioned tags → `kubectl set image` to a prior
tag; model rollback is checksum-verified, Directive 009), but the procedure is
**untested**. Run one real rollback drill before production.

### OPS-DEP-03 (MEDIUM) — deployment verification not codified
No automated post-deploy smoke/verification gate that asserts `/ready` green +
key-endpoint health after a rollout (a staging smoke-test runbook exists but is not
wired into the deploy job).

## What works (positive)
- **Version tagging + immutable image release** via `release-ghcr.yml` (tag → GHCR,
  api + worker, versioned + latest).
- **Strong pre-merge gating:** lint, tests (SQLite + PG16), frontend build,
  security/dep/secret scans, compliance + quality gates — all required checks.
- **Config validation exists** (`config.Settings.validate()`) though it is **not
  invoked at startup** (Phase 3 SEC-AUTH-02) — a deployment-safety gap.
- **Release documentation:** `RELEASE_NOTES.md`, `VERSION_1_0.md`,
  `PRODUCTION_HARDENING.md`, go-live runbook.

## Release approvals / promotion
- GitHub `environment: staging` provides an approval hook; **production environment
  gating/approval is not configured** (OPS-DEP-04, MEDIUM).
- Promotion path dev → staging → prod is documented (compose/Helm/k8s) but the
  prod promotion is manual/unwired (ties OPS-DEP-01).

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| OPS-DEP-01 | MAJOR | `deploy.yml` echoes kubectl — deployment not actually automated/verified |
| OPS-DEP-02 | MAJOR | No executed production rollback drill (only demo rollback runs) |
| OPS-DEP-03 | MEDIUM | No automated post-deploy verification gate |
| OPS-DEP-04 | MEDIUM | No production environment approval gate |

**Also inherited (blocking, from prior phases):** SEC-AUTH-02 (no startup config/
secret validation) makes an unwired deploy riskier — a misconfigured prod deploy
would not fail closed at boot.
