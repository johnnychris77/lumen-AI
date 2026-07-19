# LPR-DIR-016 — Environment Readiness (Phase 5)

**Basis:** compose/render/Helm/k8s + config inspection at `bd94bc5`.

## Environments present

| Environment | Definition | Status |
|---|---|---|
| Development | `docker-compose.yml` | ✅ |
| Testing / CI | `ci.yml` (SQLite + PostgreSQL 16 services) | ✅ |
| Staging | `staging-deploy.yml`, `deploy.yml` (env `staging`), k8s `-n lumenai-staging` | ⚠️ deploy unwired (OPS-DEP-01) |
| Production | `docker-compose.prod.yml`(+`.example`), `render.yaml`, `helm/lumenai/`, `k8s/` | ⚠️ multiple, inconsistent (ENV-01) |

## Infrastructure parity

- The API runs the same image across environments (Dockerfile). **But deployment
  descriptors diverge:** k8s `replicas: 2` vs Helm `replicas: 1`; differing CPU/mem
  (Phase 4 HA-01). Compose-prod, render.yaml, Helm, and k8s are **four production
  descriptors** with no single authoritative source → drift risk (**ENV-01, MAJOR**).
- **Dependency parity gap (carryover):** Dockerfile installs the pinned root
  `requirements.txt`; CI installs the mostly-unpinned `backend/requirements.txt`
  (Phase 2 DH-01 / Phase 3 SEC-SC-01) → CI env ≠ prod image.

## Environment isolation

- Tenant isolation is enforced in-app (Phase 3, test-verified). **Environment**
  isolation (separate DB/storage/secrets per env) is deployment-configured; the
  compose/Helm samples separate services but a documented **hard boundary between
  staging and prod data** should be confirmed per deployment (ENV-02, MEDIUM).

## Secrets

- Secrets are env-injected. **Insecure fallback defaults** for `SECRET_KEY`
  (Phase 3 SEC-AUTH-01) + **no startup validation** (SEC-AUTH-02) mean a
  mis-provisioned environment can boot with a known secret. This is the single most
  important environment-readiness blocker — **each environment must set real
  secrets and fail closed if missing.**
- `render.yaml` / compose reference env vars; a secret-manager integration (Vault/
  cloud secrets) is not evidenced (ENV-03, MEDIUM).

## Configuration

- Central frozen `Settings` exists but ~199/215 env reads bypass it (Phase 2 CFG-01);
  config is env-var-driven with documented safe-default flags. `config.validate()`
  exists but is **not invoked** (SEC-AUTH-02).

## Environment promotion
Documented dev → staging → prod via image tag; **promotion to prod is manual/unwired**
(OPS-DEP-01). Recommend: single authoritative IaC (pick Helm **or** k8s manifests),
per-env values, secret-manager, and startup config validation that refuses to boot
on missing required secrets.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| ENV-01 | MAJOR | Four divergent production descriptors (compose/render/Helm/k8s); no single source of truth |
| ENV-02 | MEDIUM | Staging↔prod data isolation not documented as a hard boundary |
| ENV-03 | MEDIUM | No secret-manager integration evidenced; env-var secrets only |
| (SEC-AUTH-01/02) | HIGH | Insecure secret defaults + no startup validation (inherited, blocking) |

**Positive:** clear dev/test/staging/prod separation exists, same runtime image,
CI tests on real PostgreSQL 16, documented promotion path.
