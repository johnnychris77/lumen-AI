# LPR-DIR-028 — Pilot Entry Evidence Tracker (Workstream 6)

Objective evidence required to close each Pilot Entry Gate. **Status reflects reality on
IRC-1 (`5c22345`) today.** A gate closes only when its evidence is produced, verified, and
recorded here — **planning documents do not change status.**

**Status legend:** `NOT STARTED` · `IN PROGRESS` · `COMPLETE`

## Evidence items

| # | Gate / item | Required objective evidence | WP | Status |
|---|---|---|---|---|
| E-01 | Managed DB (SCAL-01) | Managed-DB connection proof + `alembic upgrade head` transcript | WP-01 | **NOT STARTED** |
| E-02 | Secrets + TLS | Secrets injected from store (no literals) + valid TLS cert + signed/unsigned webhook test | WP-06 | **NOT STARTED** |
| E-03 | Real deploy (OPS-DEP-01) | Green deploy run → healthy instance + smoke test 200 | WP-03 | **NOT STARTED** |
| E-04 | Rollback drill (OPS-DEP-02) | Deploy A→B→A transcript + post-rollback smoke green + MTTR | WP-04 | **NOT STARTED** |
| E-05 | Backup + DR drill | Restore-to-clean transcript + measured RTO/RPO on pilot-class env | WP-05 | **NOT STARTED** |
| E-06 | Alerting + on-call (OPS-INC-01) | Synthetic alert delivered + acknowledged + signed on-call schedule | WP-02 | **NOT STARTED** |
| E-07 | Monitoring live | Dashboard showing live latency/error/DB/safety metrics | WP-02/03 | **NOT STARTED** |
| E-08 | Logging aggregation | A known request traced across aggregated logs | WP-03 | **NOT STARTED** |
| E-09 | Pilot site | Signed site agreement + scope | WP-07 | **NOT STARTED** |
| E-10 | Clinical sponsor | Sponsor appointment letter | WP-07 | **NOT STARTED** |
| E-11 | Equipment qualification | Qualification record (settings captured) | WP-07 | **NOT STARTED** |
| E-12 | Image acquisition SOP | Capture SOP + sample acquisitions passing validation (no PHI) | WP-07 | **NOT STARTED** |
| E-13 | Site baselines | Activated qualified baseline set + review sign-off | WP-07 | **NOT STARTED** |
| E-14 | Digital Twins initialized | Populated twins linked to in-scope instruments | WP-07 | **NOT STARTED** |
| E-15 | Operator competency | Competency sign-offs per operator | WP-07 | **NOT STARTED** |
| E-16 | Escalation SOP | Site clinical escalation SOP acknowledged | WP-07 | **NOT STARTED** |
| E-17 | Data agreement | Signed data agreement (no PHI in images/metadata) | WP-07 | **NOT STARTED** |
| E-18 | CTO approval | Signed approval + evidence refs | WP-08 | **NOT STARTED** |
| E-19 | CISO approval | Signed approval + evidence refs | WP-08 | **NOT STARTED** |
| E-20 | Quality approval | Signed approval + evidence refs | WP-08 | **NOT STARTED** |
| E-21 | Clinical approval | Signed approval + evidence refs | WP-08 | **NOT STARTED** |
| E-22 | Operations approval | Signed approval + evidence refs | WP-08 | **NOT STARTED** |
| E-23 | Executive Sponsor approval | Signed pilot authorization + protocol | WP-08 | **NOT STARTED** |

## Roll-up
- **COMPLETE: 0 / 23.**
- **IN PROGRESS: 0.**
- **NOT STARTED: 23.**

## Reference: already-present software controls (NOT pilot-gating evidence)
These exist in IRC-1 and were verified in LPR-DIR-027, but they are **software-control
presence**, not operational/clinical pilot evidence, so they do not appear as closable gate
items above: mandatory human review (`human_review_required: True`), unknown handling,
hash-chained audit, governed evidence storage, double-blind annotation, model registry +
promotion gates, digital-twin engine, baseline library.

## Honest bottom line
**Zero pilot-entry evidence items are COMPLETE.** No gate is closed. This tracker is the
single source of truth for closure and must be updated only with verified, recorded evidence.
