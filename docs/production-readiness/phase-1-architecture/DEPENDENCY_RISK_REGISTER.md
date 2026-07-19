# LPR-DIR-012 — Dependency Risk Register

Probability (P) / Impact (I): Low / Med / High. Release-blocking = would block a
future production release if unresolved.

| ID | Dependency risk | Evidence | P | I | Severity | Owner | Mitigation | Release-blocking |
|---|---|---|---|---|---|---|---|---|
| D-01 | Single database = SPOF | Modular monolith, one authoritative DB | Med | High | MAJOR | Infra Eng | Backup/restore + DR (measured RTO/RPO); HA in later phase | No (mitigated) |
| D-02 | Single backend runtime = SPOF | One FastAPI runtime | Med | Med | MAJOR | Infra Eng | Horizontal container scaling; `/ready` gating | No |
| D-03 | Deprecated audit shim path | `app.audit.log_audit_event` still called | Med | Med | MAJOR | Backend Eng | Migrate callers; remove shim | No |
| D-04 | Import-cycle / arch-boundary not CI-enforced | No proven import-cycle check in CI run | Med | Med | MAJOR | Quality Eng | Add import-linter/arch check to CI | No |
| D-05 | Transitive third-party CVE exposure | SBOM present; scan execution unconfirmed on PRs | Med | High | MAJOR | Security Eng | Run SBOM/dep scan in CI; track CVEs | No |
| D-06 | External IdP (OIDC/JWT) dependency | OIDC/JWKS auth mode | Low | High | MAJOR | Security Eng | Cached JWKS; fail-closed on unverifiable token | No |
| D-07 | Object storage availability | Foundation object storage | Low | High | MAJOR | Infra Eng | Integrity-hashed access; backup; fail-closed reads | No |
| D-08 | Billing/integration webhooks (external) | Stripe/integration webhook routes | Low | Med | MINOR | Backend Eng | Signature verification; idempotency | No |
| D-09 | Governed pipeline depends on unbuilt physical inputs | No governed images/datasets/model yet | High | Med | MAJOR | PMO | Execution prerequisites (Directive 010 conditions) | No (not an arch defect) |
| D-10 | Duplicate billing webhook handler | Two handlers on same path | Low | Low | MINOR | Backend Eng | Deprecate one | No |

## Summary

No **CRITICAL, release-blocking** dependency risk. The dominant risks are the
monolith SPOFs (mitigated by DR + scaling) and CI-enforcement gaps for dependency
scanning and import-cycle detection — all addressable in later Production Readiness
phases without architectural change.
