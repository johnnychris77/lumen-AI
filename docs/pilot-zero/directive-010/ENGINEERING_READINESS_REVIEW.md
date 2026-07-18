# LPZ-DIR-010 — Engineering Readiness Review (ERR)

**Purpose:** review engineering maturity for Pilot Alpha. Evidence-based.

## Review items

| Item | Evidence | Status |
|---|---|---|
| **Security controls** | Directive 002 Security & Engineering Gate passed; typed auth principal, fail-closed multi-tenant authz, secured enterprise/vendor writes (unauth writes 21→10, all PUBLIC_BY_DESIGN) | ✅ Strong |
| **Build reproducibility** | `docs/pilot-zero/REPRODUCIBLE_BUILDS.md`; pinned deps; SBOM (CycloneDX) | ✅ Complete |
| **CI/CD** | Repository GitHub Actions appear **disabled** (0 registered checks on PRs) | ⚠️ Gap |
| **Testing strategy** | 212 backend test files; governance regression tests; fresh-DB discipline | ✅ Strong |
| **Static analysis** | `ruff` clean gate on changed code | ✅ Complete |
| **Dependency governance** | SBOM + dependency-integrity practices (Directive 002) | ✅ Complete |
| **Audit logging** | `docs/foundation/AUDIT_ARCHITECTURE.md`; lifecycle audit events across annotation/baseline/dataset | ✅ Complete |
| **Observability** | `/ready` readiness probe with per-dependency checks; `docs/foundation/MONITORING.md` | ✅ Complete |
| **Recovery procedures** | `docs/foundation/{BACKUP_RESTORE,DISASTER_RECOVERY}.md` — executed with measured RTO/RPO | ✅ Complete |

## Findings

* **ERR-1 (gap):** CI/CD automation is not active in the repository — PR checks show
  `total_count: 0`. Tests exist and pass locally (fresh DB), but automated gating is
  not enforced on merge. **Condition:** activate CI to run the backend suite +
  `ruff` + build on every PR before Pilot Alpha.
* **ERR-2 (governance-in-code):** Several Directive 006–009 governance gates
  (GT-gated creation, separation-of-duties, dataset immutability, first-class
  experiment records) are **documented but not enforced in code**. **Condition:**
  implement the High-priority enforcement steps from Directives 006–009 migration
  plans.
* **ERR-3 (strength):** Security gate, reproducible builds, SBOM, audit, readiness
  probe, and executed backup/restore/DR give strong engineering fundamentals.

## ERR determination

**CONDITIONAL PASS.** Engineering fundamentals (security, reproducibility, testing,
audit, observability, recovery) are strong and evidence-backed. Two conditions
(ERR-1 CI activation, ERR-2 governance-in-code enforcement) must close before Pilot
Alpha *execution*. No blocking engineering defect identified.
