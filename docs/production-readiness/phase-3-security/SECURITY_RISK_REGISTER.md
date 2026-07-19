# LPR-DIR-014 — Security Risk Register (Phase 3)

Severity: **Critical / High / Medium / Low / Observation**. Blocking = must be
resolved before any production authorization. Baseline `f889d95`. All items are
**pre-existing platform behavior**; this PR changes documentation only.

| ID | Description | Evidence | Impact | Likelihood | Severity | Owner | Mitigation | Blocking |
|---|---|---|---|---|---|---|---|---|
| **SEC-C-01** | External-integration webhooks fail **open** when signing secret unset; tenant from `X-Tenant-Id` header | `integrations.webhook_ingest`, `billing.stripe_webhook` (code-confirmed; =AR-15/TB-02) | **Cross-tenant data injection on public write** | Med (valid config permits it; no startup guard) | **CRITICAL** | Security Eng | Require signing secret at startup (fail closed); reject unsigned; bind tenant to verified signature, not header | **YES** |
| **SEC-H-01** | Hardcoded HS256 secret fallbacks (`main.py`, `core/config.py`, `auth_simple.py`); `deps.py` reuses them | code-confirmed | **JWT forgery / auth bypass on HS256 paths if `SECRET_KEY` unset** | Med (no guard forces `SECRET_KEY`) | **HIGH** | Security Eng | Remove fallback literals; require `SECRET_KEY` at startup; consolidate onto OIDC/JWKS | **YES** |
| **SEC-H-02** | No fail-closed startup secret/config validation (`validate()` omits `SECRET_KEY` and is not invoked) | `config.py:78-97`; no `.validate()` in `main.py` | Root cause of SEC-C-01 & SEC-H-01 reaching prod | Med | **HIGH** | Backend Eng | Invoke `validate()` at startup; extend to require `SECRET_KEY` + webhook secrets; refuse boot on missing | **YES** |
| SEC-M-01 | Audit write not atomic with business write | `integrations.webhook_ingest` etc. (=AR-16) | Committed data without chain entry on audit failure (completeness) | Med | MEDIUM | Backend Eng | Single transaction / outbox; surface audit failure | No |
| SEC-M-02 | Auth path fragmentation (multiple HS256 issuers + OIDC; mixed KDF) | code (=SEC-AUTH-03) | Enlarged auth attack surface; multiple secret sites | Med | MEDIUM | Security Eng | Consolidate onto one signed-token service (Directive 002 F5) | No |
| SEC-M-03 | Container runs as root (no `USER` in Dockerfile) | `Dockerfile` | Larger blast radius on container compromise | Med | MEDIUM | Infra Eng | Add non-root user | No |
| SEC-M-04 | Frozen `DatasetVersion` not lock-enforced | `dataset_builder` (=AR-17) | Dataset integrity / model-lineage reproducibility | Med | MEDIUM | ML Eng | Enforce `frozen` guard on entry writes | No |
| SEC-M-05 | CI installs mostly-unpinned `backend/requirements.txt` vs pinned prod | manifests (=DH-01/SEC-SC-01) | Tests ≠ shipped versions; supply-chain determinism | Med | MEDIUM | Quality Eng | Install pinned prod manifest in CI | No |
| SEC-M-06 | Rate limiter wired best-effort (`try/except pass`) | `main.py:214-221` | Possible under-enforced rate limiting (API4) | Low-Med | MEDIUM | Backend Eng | Verify limiter engages; fail-closed wiring | No |
| SEC-L-01 | Image dedup check-then-insert; `image_sha256` non-unique (TOCTOU) | `dataset_registry.register_image` (=AR-18) | Duplicate records under concurrency | Low | LOW | ML Eng | Unique `(tenant_id, image_sha256)` + integrity handling | No |
| SEC-L-02 | MD5 used for non-security purposes (29 bandit-High) | `benchmark_engine._seed` etc. | None (non-security); scanner noise | Low | LOW | Backend Eng | Add `usedforsecurity=False` | No |
| SEC-L-03 | ~70 silent `except: pass` in advisory paths | grep (=EH-01) | Reduced security observability | Low | LOW | Backend Eng | Narrow + log | No |
| SEC-O-01 | Allowlisted string-built SQL (`# nosec`) | `capa_service` etc. | Low (parameterized + allowlist) | Low | OBSERVATION | Backend Eng | Migrate to ORM/expression | No |
| SEC-O-02 | CORS `allow_credentials=True` | `main.py:273-277` | Risk only if origins not strict | Low | OBSERVATION | Security Eng | Keep `CORS_ORIGINS` a strict allowlist | No |
| SEC-O-03 | Actions not SHA-pinned; no image/IaC/license scan gated | CI | Supply-chain hardening | Low | OBSERVATION | DevSecOps | SHA-pin actions; add Trivy/license scan | No |
| SEC-O-04 | Deprecated `app.audit` shim (second call path) | runtime warning (=B-01) | Maintenance; not a bypass | Low | OBSERVATION | Backend Eng | Migrate callers; remove shim | No |

## Summary
- **CRITICAL: 1 (SEC-C-01)** — blocking. **HIGH: 2 (SEC-H-01, SEC-H-02)** — blocking.
- **MEDIUM: 6**, **LOW: 3**, **OBSERVATION: 4**.
- **Unifying theme:** *secure-by-default is not fully met* — insecure secret
  fallback defaults + no fail-closed startup secret validation drive the CRITICAL
  and both HIGH findings. Fixing that single theme (require secrets at startup, fail
  closed; remove fallback literals; consolidate auth) closes the blocking set.
- All findings are pre-existing, tracked, and remediable; **no production or
  clinical deployment is authorized.**
