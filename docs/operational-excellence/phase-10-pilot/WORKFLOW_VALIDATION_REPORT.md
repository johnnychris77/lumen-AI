# LPR-DIR-021 — Workflow Validation Report (Phase 10)

## Two kinds of "validation" — kept strictly separate

1. **Software workflow validation (real, done):** the governed pipeline is
   implemented and **regression-tested end-to-end** on SQLite + PostgreSQL.
2. **Real-world pilot workflow validation (NOT DONE):** requires operators executing
   the workflow at a site — **no pilot ran**, so there are **no real-world timings,
   deviations, or operator-observed behaviors** to report. These are marked NOT
   AVAILABLE, not fabricated.

## Workflow-by-workflow status

| Workflow | Software state (real) | Pilot observation |
|---|---|---|
| **Inspection** | State machine `UNLABELED→…→APPROVED`; RBAC-guarded; honest result contract; contamination fail-closed; image-identity verification | **NOT AVAILABLE (no pilot)** |
| **Annotation** | `Annotation`/`AnnotationVersion`/`AnnotationReview`; primary + double-blind secondary + adjudication; immutable versions | **NOT AVAILABLE** |
| **Evidence generation** | Checksummed, authorization-gated evidence; hash-chained audit | **NOT AVAILABLE** |
| **Digital Twin** | `digital_twin_id`/LCID per instrument; baseline linkage; timeline | **NOT AVAILABLE** |
| **Reporting** | Report generation + export; honest disclosure fields | **NOT AVAILABLE** |

## Deviations

**NONE OBSERVED — no pilot executed.** A deviation log requires real workflow
execution. The capture instrument exists (`docs/clinical-pilot/
PILOT_OBSERVATION_FORMS.md`) and is ready to record deviations when a pilot runs.

## What software validation *does* establish

The Pilot Alpha integration subset (PR #108) passed **130/130** on a fresh DB across
inspection closure, annotation DB, baseline library, dataset registry/eligibility,
candidate-model train→register→promote, audit-chain verification + immutability, and
evidence authorization. This proves the **software workflow is internally coherent and
regression-safe** — it does **not** substitute for real-world workflow validation.

## Determination

Software workflow: **validated (tested).** Real-world pilot workflow: **NOT VALIDATED —
pilot not executed.** No deviations can be reported because no real workflow ran.
