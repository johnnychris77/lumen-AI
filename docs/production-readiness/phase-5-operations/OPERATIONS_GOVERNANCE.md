# LPR-DIR-016 — Operations Governance (Phase 5)

**Basis:** CI/CD + change-control + governance-doc inspection at `bd94bc5`.

## Change management
- **Present:** all changes flow through **PRs with required CI gates** (lint, tests,
  security/dep/secret scans, compliance + quality gates) — a real change-control
  spine. The architecture is **frozen** with a Class A/B/C change-control policy
  (Phase 1 `ARCHITECTURE_CHANGE_CONTROL.md`).
- **Gap OPS-GOV-01 (MEDIUM):** no documented **operational** change-management process
  (maintenance windows, change advisory, freeze calendars, emergency-change path) —
  distinct from code-review change control.

## Release approvals
- GitHub `environment: staging` approval hook exists; **no production-environment
  approval gate** configured (OPS-DEP-04). Release notes + versioned GHCR images
  provide an auditable release record.

## Maintenance windows
- **OPS-GOV-02 (MEDIUM):** none defined. With a single-DB SPOF and unwired rolling
  deploy, maintenance/upgrade windows + tenant notification must be defined before
  production.

## Configuration governance
- Central frozen `Settings` + documented safe-default flags; **but** ~199/215 env
  reads bypass it (CFG-01) and `validate()` isn't invoked at startup (SEC-AUTH-02).
  Config changes are not gated by a review/approval workflow distinct from code
  (fold into OPS-GOV-01).

## Access reviews
- **OPS-GOV-03 (MAJOR):** no evidence of a periodic **access-review** process
  (who has admin/production/secret access, reviewed on a cadence). RBAC is enforced
  in-app (Phase 3) and audit records exist, but **operational access governance**
  (cloud IAM, secret access, on-call roster) is undocumented. Required for SOC2/HIPAA
  posture (Phase 3 COMPLIANCE_READINESS).

## On-call process
- **OPS-GOV-04 (MAJOR):** no on-call rotation / paging / escalation policy
  (= OPS-INC-01). The GA runbook has an "On-call" stub only.

## Audit reviews
- **Strong:** hash-chained tamper-evident audit + admin chain-verification endpoint
  enables **audit review**; every governed action emits an audit event. A **scheduled
  audit-review cadence** (who reviews, how often) is not documented (OPS-GOV-05,
  MEDIUM) — the capability exists; the process doesn't.

## Roll-up
| ID | Sev | Finding |
|---|---|---|
| OPS-GOV-03 | MAJOR | No periodic access-review process (IAM/secret/admin) |
| OPS-GOV-04 | MAJOR | No on-call/escalation process (= OPS-INC-01) |
| OPS-GOV-01 | MEDIUM | No operational change-management process (maint windows, CAB, emergency change) |
| OPS-GOV-02 | MEDIUM | No maintenance-window policy |
| OPS-GOV-05 | MEDIUM | No scheduled audit-review cadence (capability exists) |

**Positive:** code change-control is strong (PR + required gates + architecture
freeze), releases are versioned/auditable, and audit **capability** is
production-grade. The gaps are operational **processes** (access review, on-call,
maintenance windows), not missing platform capability.
