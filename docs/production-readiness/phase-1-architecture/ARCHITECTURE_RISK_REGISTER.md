# LPR-DIR-012 — Architecture Risk Register

P/I: Low/Med/High. Severity: CRITICAL/MAJOR/MINOR/OBSERVATION. Release-blocking =
would block a future production release if unresolved.

| ID | Category | Description | Evidence | P | I | Severity | Owner | Mitigation | Target phase | Status | Release-blocking |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AR-01 | Boundary | God-runtime concentrates domains/ownership | 489 svcs/205 routes, 1 runtime | Med | Med | MAJOR | Program Arch | Domain maintainership + package boundaries | Phase 2+ | Open | No |
| AR-02 | Audit | Deprecated audit shim = second call path | `app.audit` still called | Med | Med | MAJOR | Backend Eng | Migrate callers; remove shim | Phase 2 | Open | No |
| AR-03 | Data-authority | Governance gates policy-enforced, not all code-enforced | Directives 006–009 migrations | Med | High | MAJOR | CTO | Enforce GT-gate/SoD/immutability/experiment in code | Phase 2–3 | Open | No |
| AR-04 | Documentation | Core decisions Implemented but Undocumented (monolith, DB, audit-chain, dataset immutability, deployment) | ADR gap analysis | Med | Med | MAJOR | Program Arch | Author missing ADRs | Phase 1–2 | Open | No |
| AR-05 | Dependency | Import-cycle/arch-boundary + dep-scan not CI-enforced | No proven CI run of these | Med | Med | MAJOR | Quality Eng | Add checks to CI | Phase 2 | Open | No |
| AR-06 | Recovery | Single DB/runtime SPOF; HA unproven | Modular monolith | Med | High | MAJOR | Infra Eng | DR (measured RTO/RPO) now; HA later | Phase 3 | Open (mitigated) | No |
| AR-07 | Placeholder | Vision inference has no governed/certified model | Directive 009/010/011 | High | Med | MAJOR | Chief AI | Certify dataset + govern model | Phase 3+ | Open (expected) | No |
| AR-08 | Scalability | Production-scale perf not characterized | Directive 011 deferred | Med | Med | MAJOR | Infra Eng | Load-test in prod-representative env | Phase 3 | Open | No |
| AR-09 | Maintainability | Duplicate billing webhook handler | Route inventory | Low | Low | MINOR | Backend Eng | Deprecate one | Phase 2 | Open | No |
| AR-10 | Documentation | Directive 005 docs not consolidated on main | Repo scan | Med | Low | MINOR | PMO | Consolidate/restate | Phase 1–2 | Open | No |
| AR-11 | Ownership | Knowledge concentration under Backend Eng | Ownership matrix | Med | Med | MAJOR | Program Arch | Distribute maintainership | Phase 2 | Open | No |
| AR-12 | Tenant-isolation | (Verification) cross-tenant paths | tests pass | Low | High | OBSERVATION | Security Eng | Keep regression tests green | Ongoing | Mitigated | No |
| AR-13 | Auth/Authz | (Verification) principal/role bypass | tests pass | Low | High | OBSERVATION | Security Eng | Keep guards + tests | Ongoing | Mitigated | No |
| AR-14 | Evidence-integrity | (Verification) evidence mutation/audit bypass | tests pass | Low | High | OBSERVATION | Security Eng | Keep hash-chain + append-only | Ongoing | Mitigated | No |

## Summary

* **CRITICAL architecture risks: 0.** No open risk permits cross-tenant exposure,
  unauthorized action, evidence corruption, audit bypass, false finalization,
  unsafe AI authority, or unrecoverable data loss — the safety-critical categories
  are verified (AR-12/13/14 mitigated).
* **MAJOR (9):** maintainability, governance-in-code, ADR documentation,
  CI-enforcement, recovery HA, model certification, scalability, ownership — all
  addressable in later phases under change control; none release-blocking at the
  architecture-freeze decision point.
* **MINOR/OBSERVATION:** duplicate webhook, Directive 005 consolidation,
  verification observations.
