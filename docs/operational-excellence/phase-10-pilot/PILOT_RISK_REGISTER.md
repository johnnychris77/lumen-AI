# LPR-DIR-021 — Pilot Risk Register (Phase 10)

## Framing

Because no pilot ran, there are **no observed pilot incidents.** This register records
(a) the **execution-blocking preconditions** that prevent a pilot today, and (b) the
**anticipated pilot risks + mitigations** to manage when a pilot does run. Observed-
issue fields are **NOT AVAILABLE — pilot not executed**.

## A. Observed pilot issues

**NONE — no pilot executed.** (An incident log requires real operations.)

## B. Execution-blocking preconditions (must close before Day 1)

| ID | Blocker | Severity | Mitigation / action |
|---|---|---|---|
| PB-01 | **SEC-C-01** webhook fail-open → cross-tenant injection | **CRITICAL** | Fail-closed verification + startup secret validation (V1.1 Sprint 0) |
| PB-02 | No production load test (PERF-07) | HIGH | Run representative load test on managed env |
| PB-03 | Single Postgres SPOF + single worker (SCAL-01) | HIGH | HA Postgres + multi-worker before real load |
| PB-04 | In-process scheduler duplication (RES-01) | HIGH | Leader election |
| PB-05 | No incident response + no alerting (OPS-INC-01) | HIGH | IR runbook + on-call + alert rules |
| PB-06 | Deploy stub + no rollback drill (OPS-DEP-01/02) | HIGH | Real deploy automation + executed rollback drill |
| PB-07 | No site / users / managed env / real equipment | HIGH (operational) | Site agreement, training + competency, provisioning, equipment validation |
| PB-08 | No governed trained model; only Experimental/synthetic | HIGH | Keep AI observe-only; do not represent as clinical AI |

## C. Anticipated pilot risks (manage during pilot)

| ID | Risk | Impact | Mitigation |
|---|---|---|---|
| PR-01 | Operator over-trust in AI advisory | Wrong disposition | Advisory-only UI; mandatory human review; training emphasizes "not a trained model" |
| PR-02 | PHI accidentally in image/metadata | Privacy breach | No-PHI rule + metadata validation + review |
| PR-03 | Poor real-image quality vs. synthetic | Unusable evidence | Image-quality assessment gate; capture retraining |
| PR-04 | Annotation inconsistency between reviewers | Weak Ground Truth | Double-blind review + adjudication; agreement metric |
| PR-05 | Workflow doesn't fit real SPD tempo | Low adoption | Observe deviations (Form set); iterate before scale |
| PR-06 | Audit gap during real ops | Loss of traceability | Hash-chained audit + 100% completeness target + weekly Form E |
| PR-07 | Contamination-safety edge case | Patient-safety exposure | Fail-closed decision states + supervisor escalation (already in code) |

## Determination

The dominant risk today is **executing a pilot before the preconditions close.** No
pilot incidents exist to report. The blocker list (Section B) is the honest gate; the
anticipated-risk list (Section C) is the management plan for when the pilot runs.
