# LPR-DIR-017 — Security Certification (Phase 6)

Certifies the Phase 3 security review (LPR-DIR-014). Baseline `bd94bc5`.

| Item | Verdict | Evidence (Phase 3) |
|---|---|---|
| Authentication | **CERTIFIED w/ conditions** | strong OIDC/JWKS (explicit alg allowlist, exp/iat/sub, iss/aud); PBKDF2/bcrypt; **but HS256 secret fallbacks (SEC-H-01) + no startup validation (SEC-H-02)** |
| Authorization | **CERTIFIED** | default-deny; 1,593 `require_*` guards; vertical/header-role escalation defended (tested) |
| Tenant isolation | **CERTIFIED w/ condition** | membership-authoritative, header cannot elevate, test-verified; **webhook cross-tenant injection (SEC-C-01) is the one break** |
| Trust boundaries | **CERTIFIED w/ condition** | 13/14 hold + test-verified; boundary 13 (external integration) = CRITICAL SEC-C-01 |
| Evidence integrity | **CERTIFIED** | checksummed, authz-gated, immutable, quarantine-on-incomplete |
| Audit integrity | **CERTIFIED** | hash-chained, append-only, tamper-evident, single writer (atomicity gap AR-16 tracked) |
| Compliance readiness | **CERTIFIED (not certified externally)** | ASVS/API-Top-10/SSDF/SOC2/HIPAA-technical/FDA-SBOM mapped; **no clearance claimed** |
| Supply chain | **CERTIFIED** | 0 Python CVEs, 0 Node CVEs; pinned prod manifest; SBOM (100 components); scanners gated |
| Infrastructure security | **CERTIFIED w/ conditions** | pinned base, `/ready` gate, config-driven CORS; **container-as-root (SEC-INF-01)** |

## Blocking findings (must close before production)
- **SEC-C-01 (CRITICAL):** webhook fail-open → cross-tenant injection.
- **SEC-H-01/02 (HIGH):** HS256 secret fallback + no fail-closed startup secret
  validation.

## Certification statement
The security **architecture is sound and largely test-verified** (zero-trust auth,
default-deny authz, tenant authority, immutable audit/evidence, AI-advisory-only,
0 CVEs, SBOM). The recurring **secure-by-default gap** (insecure secret defaults +
no startup validation) produces 1 CRITICAL + 2 HIGH blocking findings.

**Security: CERTIFIED (PASS WITH CONDITIONS)** — SEC-C-01 + SEC-H-01/02 blocking.
