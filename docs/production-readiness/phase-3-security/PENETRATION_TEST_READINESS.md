# LPR-DIR-014 — Penetration Test Readiness (Phase 3)

**Purpose:** assess readiness for an external/authenticated penetration test and
seed a test plan. Baseline `f889d95`. **No production/clinical environment is
authorized** — testing must target a controlled research environment.

## Readiness by test type

| Test type | Ready? | Notes / seeded targets |
|---|---|---|
| Authenticated testing | ✅ | OIDC/JWKS + HS256 paths; provide test principals per role/tenant |
| Tenant testing | ✅ | `test_tenant_isolation` gives a baseline; **priority: webhook `X-Tenant-Id` injection (SEC-C-01)** |
| Privilege escalation | ✅ | header-role escalation + high-risk guard tests exist; extend to per-object BOLA |
| API fuzzing | ✅ | 1,912 endpoints, OpenAPI generated → drive a schema-based fuzzer (pydantic 422 expected) |
| Object reference (BOLA/IDOR) | ⚠️ prioritize | verify per-object ownership beyond tenant scope (API1) |
| Upload testing | ⚠️ | CV image ingestion + hash validation; fuzz content-type/size/malformed |
| Injection testing | ✅ | ORM-parameterized; target the allowlisted string-SQL sites (SEC-API-02) to confirm allowlist holds |

## Priority pen-test targets (from this review)

1. **SEC-C-01 (CRITICAL) webhook fail-open** — confirm cross-tenant injection when
   `WEBHOOK_SECRET_*`/`STRIPE_WEBHOOK_SECRET` unset; confirm `X-Tenant-Id` is honored
   without a signature. **Highest priority.**
2. **SEC-AUTH-01 (HIGH) HS256 secret forgery** — with `SECRET_KEY` unset, attempt to
   forge an admin JWT on the HS256 paths (history/summary via `deps.py`).
3. **SEC-TEN-02** — cache/Redis per-tenant key isolation.
4. **BOLA/IDOR** — per-object ownership beyond tenant filter.
5. **Rate limiting** (SEC-API-01) — confirm limiter actually engages (it is wired
   best-effort).

## Preconditions before pen-test
- Provision a controlled environment with **secrets deliberately set** for a
  "secure config" run **and** deliberately unset for a "misconfig" run (to
  reproduce SEC-C-01 / SEC-AUTH-01).
- Provide role/tenant test accounts and seeded governed data.
- Rules of engagement: no production, no real PHI, no clinical claims.

## Assessment
The platform is **ready for authenticated penetration testing** in a controlled
environment. The two must-verify findings (SEC-C-01, SEC-AUTH-01) are already
identified by code review; the pen-test should confirm exploitability and validate
the remediation once applied.
