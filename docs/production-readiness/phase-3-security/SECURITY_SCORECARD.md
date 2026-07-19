# LPR-DIR-014 — Security Scorecard (Phase 3)

**Scale:** 0 (absent) – 5 (excellent). Evidence-based at `f889d95`.

| Subsystem | Score | Rationale (evidence) |
|---|---|---|
| **Authentication** | **3 / 5** | Strong OIDC/JWKS + KDF hashing, dev-token gated; **HS256 secret fallbacks (SEC-AUTH-01)** + no startup validation (SEC-AUTH-02) + path fragmentation pull it down |
| **Authorization** | **4 / 5** | Default-deny, 1,593 `require_*` guards, escalation tested; governance-in-code completeness pending (AR-03) |
| **Tenant Isolation** | **3 / 5** | Strong for authenticated surface (test-verified); **webhook cross-tenant injection (SEC-C-01)** is the one break |
| **API Security** | **3 / 5** | 0 UNKNOWN, pydantic + ORM; conditions on auth (API2), misconfig (API8), 3rd-party ingress (API10) |
| **Audit** | **4 / 5** | Hash-chained, append-only, tamper-evident, single writer; write/audit atomicity gap (SEC-AUD-01) |
| **Evidence** | **4 / 5** | Checksummed, authz-gated, immutable, quarantine-on-incomplete; test-verified |
| **Data Protection** | **3 / 5** | Immutable governed objects, SHA-256 secret storage, DR w/ RTO-RPO; dataset-freeze not enforced (SEC-DP-03), at-rest is infra |
| **Infrastructure** | **3 / 5** | Pinned base, `/ready` gate, config-driven CORS; **container-as-root (SEC-INF-01)** + secret defaults |
| **Supply Chain** | **3 / 5** | 0 CVEs, pinned prod manifest, SBOM, scanners in CI; **CI unpinned manifest (SEC-SC-01)** |
| **AI Governance** | **4 / 5** | No AI final authority, Unknown≠approved, absence≠clean, checksum-pinned models, honest placeholder disclosure |
| **Compliance** | **3 / 5** | Foundational ASVS/SSDF/SOC2/HIPAA-technical controls; not certified; IR/disclosure processes pending |
| **Logging** | **3 / 5** | Present + `/ready`; inconsistency (`print` vs logger) + ~70 silent excepts (SEC-INF-03) |
| **Monitoring** | **3 / 5** | `/ready` dependency probe + health service; deeper alerting/monitoring pending |
| **Secrets** | **2 / 5** | SHA-256-only storage of API keys ✅, but **insecure fallback defaults + no startup validation** is the weakest area (SEC-AUTH-01/02, SEC-C-01) |
| **Configuration** | **3 / 5** | Central frozen `Settings` + safe-default flags; sprawl (~199/215 bypass) + no startup secret validation |

## Aggregate
**Weighted security posture: ~3.2 / 5 — "Solid architecture, secure-by-default not
yet met."**

- **Strong (4):** Authorization, Audit, Evidence, AI Governance.
- **Conditions (3):** Authentication, Tenant Isolation, API, Data Protection,
  Infrastructure, Supply Chain, Compliance, Logging, Monitoring, Configuration.
- **Weakest (2):** **Secrets** — the single theme (insecure fallback defaults + no
  fail-closed startup validation) that also drives the CRITICAL webhook finding and
  the HIGH auth finding.

**Lowest-scoring area = the #1 remediation priority.** No subsystem scored ≤ 1.
