# LPR-DIR-014 — Infrastructure Security Review (Phase 3)

**Basis:** Dockerfile, compose/Helm/K8s, CORS, `/ready`, secrets/env inspection at
`f889d95`.

## Findings by area

| Area | Status | Evidence / note |
|---|---|---|
| **Container user** | ⚠️ **runs as root** | `Dockerfile` has **no `USER` directive** / no `adduser` → process runs as root (SEC-INF-01, MEDIUM) |
| Container base | ✅ | single pinned Python base; `--no-cache-dir`; installs pinned root manifest |
| Secrets | ⚠️ | env-injected; **insecure fallback defaults** for `SECRET_KEY` (SEC-AUTH-01) and no startup validation (SEC-AUTH-02) |
| IAM | n/a-app | object storage access-controlled (foundation); cloud IAM is deployment-side |
| Networking / CORS | ⚠️/✅ | `CORSMiddleware` uses **config-driven `CORS_ORIGINS`** (not wildcard — the old any-`*.onrender.com` default was removed) with `allow_credentials=True` → keep origin list strict (SEC-INF-02) |
| TLS | ✅ deploy | terminated at ingress (Helm/K8s/Render); app assumes HTTPS |
| Storage / backups / recovery | ✅ | governed object storage + integrity hashing; DR with measured RTO/RPO (foundation) |
| Logging | ⚠️ | logging present but inconsistent (`print()` vs logger, EH-03); ~70 silent excepts reduce security observability (SEC-INF-03) |
| Monitoring | ✅ | `/ready` per-dependency probe hard-gates the DB; monitoring/health service (foundation) |
| Environment variables | ⚠️ | config sprawl (~199/215 reads bypass central `Settings`; no startup secret validation) — SEC-AUTH-02 |
| IaC | ✅/OBS | Helm/K8s/Compose present; no IaC security scan gated (SEC-INF-04) |

## Findings
| ID | Sev | Finding |
|---|---|---|
| SEC-INF-01 | MEDIUM | Container runs as root (no `USER` in Dockerfile) — add a non-root user |
| SEC-INF-02 | OBSERVATION | CORS `allow_credentials=True` — ensure `CORS_ORIGINS` is a strict allowlist per environment |
| SEC-INF-03 | LOW | Logging inconsistency + ~70 silent excepts reduce security observability (EH-01/EH-03) |
| SEC-INF-04 | OBSERVATION | No gated IaC/container-image security scan |

**Positive:** pinned base image + pinned prod deps, config-driven (non-wildcard)
CORS, `/ready` dependency hard-gate, DR with measured RTO/RPO, integrity-hashed
object storage. The material infra items are container-as-root (SEC-INF-01) and the
recurring secret-default/startup-validation theme.
