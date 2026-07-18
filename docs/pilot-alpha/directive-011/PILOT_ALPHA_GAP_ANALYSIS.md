# LPA-DIR-011 — Pilot Alpha Gap Analysis

**Purpose:** identify gaps observed during controlled technical validation.
Classification: **Critical** (blocks a data-acquiring pilot), **Major** (must close
before Pilot Beta), **Minor** (cleanup), **Future** (enhancement).

## Gaps

| ID | Gap | Type | Class | Owner | Mitigation |
|---|---|---|---|---|---|
| G-01 | Physical lab not built; image acquisition validated only on seeded fixtures | Technical/Operational | **Critical** | Lab Lead | Stand up + qualify lab (Directive 010 C-1); then re-run AT-01/02 with real acquisition |
| G-02 | No Directive-009-governed, readiness-certified candidate model; model path validated on seeded data only | Technical/AI | **Critical** | Chief AI | Certify a dataset (C-2) + run first governed experiment; keep decision-support-only |
| G-03 | High-priority governance gates documented, not all enforced in code (GT-gating, SoD, dataset immutability, first-class experiment) | Technical | **Major** | CTO | Implement Directive 006–009 enforcement (C-3) |
| G-04 | CI/CD disabled; no automated merge gating (0 checks on PRs) | Operational | **Major** | CTO | Activate CI (suite + ruff + build) (C-4) |
| G-05 | Bundle-level manifest-hash sealing not yet implemented (per-artifact checksums present) | Technical | **Major** | CTO | Seal dataset/evidence manifest hash (Directive 008 migration) |
| G-06 | Directive 005 (Acquisition & Metadata) deliverables not consolidated on `main` | Documentation | **Major** | PMO | Locate/restate 005 doc set (C-5) |
| G-07 | Directive 009 documentation on open PR at review time | Documentation | **Minor** | PMO | Merge PR #106 (C-6) |
| G-08 | `app.audit.log_audit_event` deprecated shim still called by some routes | Technical | **Minor** | CTO | Migrate callers to `enterprise_audit_service.record_enterprise_audit_event` |
| G-09 | Digital Twin is an identity anchor, not a governed aggregate record | Technical | **Future** | CTO | Add aggregate twin record (Directive 007 migration) |
| G-10 | Production-scale performance (latency/throughput/resource) not characterized | Operational | **Future** | CTO | Load-test in production-representative environment |
| G-11 | Operators not yet trained for acquisition/review | Operational | **Major** | Lab Lead | Train per SOPs (Directive 010 C-7) |

## Summary by class

* **Critical (2):** G-01 physical lab, G-02 governed model — both are *execution
  prerequisites* for a data-acquiring pilot, consistent with Directive 010's GO
  WITH CONDITIONS. Neither is a software defect.
* **Major (5):** governance-in-code (G-03), CI (G-04), manifest sealing (G-05),
  Directive 005 consolidation (G-06), operator training (G-11).
* **Minor (2):** Directive 009 merge (G-07), audit shim migration (G-08).
* **Future (2):** aggregate twin (G-09), scale performance (G-10).

## No critical *defects*

The controlled validation produced **130/130 integration passes with zero critical
software failures**. The Critical-class gaps are absences of physical execution and
a governed model — tracked with mitigation plans — not defects in the integrated
system, satisfying the directive's acceptance criterion that critical items are
documented with mitigation plans.
