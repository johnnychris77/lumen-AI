# Readiness Score Model

How `app/services/pre_sterilization_command_center_service.py` turns raw
`Inspection` rows into a readiness state and score. Every number here is
computed from real rows — nothing is fabricated, and a rate is `null`
rather than a misleading `0.0` when there's no data yet.

## Readiness states

Six states, all sub-classifications of the frozen five-value Clinical
Decision Engine outcome
(`docs/architecture/lumenai-clinical-intelligence-architecture.md` Layer
7) — no new engine value was introduced:

| State | Derived from | Blocks packaging? |
|---|---|---|
| `READY_FOR_PACKAGING` | `PASS` / `MONITOR` outcome | No |
| `REQUIRES_RECLEANING` | `REPROCESS` outcome | Yes |
| `REQUIRES_SUPERVISOR_REVIEW` | `SUPERVISOR REVIEW` outcome, or `supervisor_review_required` | Yes |
| `REQUIRES_REPAIR` | `REMOVE FROM SERVICE` outcome **and** the detected issue is a repairable structural defect (crack, corrosion, insulation damage) | Yes |
| `REMOVED_FROM_SERVICE` | `REMOVE FROM SERVICE` outcome and the issue is not repairable (contamination escalated, or unrepairable structural failure) | Yes |
| `PENDING_ANALYSIS` | `score_status != "scored"` — analysis hasn't completed | Yes (nothing to read yet) |

`REQUIRES_REPAIR` vs. `REMOVED_FROM_SERVICE` is exactly the
repair/remove-from-service split flagged as a future decision in the
Phase 19.5 architecture roadmap — implemented here as a computed
`repair_candidate` sub-field on the existing outcome, per that document's
own guidance, rather than as a sixth engine-level value.

## Classification logic (`classify_readiness`)

1. **Primary path — the persisted `recommended_action` sentence.** The
   scoring engine (`app/services/baseline_comparison_scoring_service.py`)
   always writes a deterministic sentence starting with one of "Pass —",
   "Monitor —", "Supervisor review ... —", "Reprocess —", or "Remove from
   service —". The classifier prefix-matches (case-insensitive) on this
   text — it's the same information a human reading the record would use.
2. **Fallback path — no `recommended_action`.** Manual/no-image entries
   never run the scoring engine, so `recommended_action` is `None`. In
   that case the classifier falls back to `detected_issue` +
   `supervisor_review_required` + `risk_score`:
   - flagged for supervisor review → `REQUIRES_SUPERVISOR_REVIEW`
   - no issue and no stain detected → `READY_FOR_PACKAGING`
   - a repairable issue with `risk_score >= 70` → `REQUIRES_REPAIR`,
     otherwise `REQUIRES_SUPERVISOR_REVIEW`
   - a contamination issue, or `stain_detected` → `REQUIRES_RECLEANING`
   - anything else → `REQUIRES_SUPERVISOR_REVIEW` (fail safe to a human,
     never fail safe to "ready")
3. **Unscored.** `score_status != "scored"` always wins first — an
   inspection that hasn't finished analysis is never reported as ready.

## Readiness score

```
readiness_score = 100 - risk_score   (only when score_status == "scored")
```

The same inverse-of-risk convention already used elsewhere in the platform
(e.g. `ai_score` in `app/routes/ai_clinical_review.py`). `None` when not
yet scored — never a fabricated number.

## Confirmed vs. unconfirmed

A finding is "confirmed" (has had human eyes on it) when any of:
- `qa_review_status` is `approved` or `overridden` (the separate QA review
  flow, `app/routes/qa_review.py`), or
- `status` is `reviewed` or `closed`, or
- a `SupervisorReview` row exists for the inspection
  (`app/models/supervisor_review.py`).

The High-Risk Findings Queue (Module 5) and Supervisor Review Queue
(Module 6) only surface **unconfirmed** items — a confirmed finding has
already had its human decision and isn't a queue item anymore, even if its
underlying state is still e.g. `REQUIRES_RECLEANING`.

## Aggregation rules

- **Tray Readiness (Module 2):** weakest link. A tray's state is the
  most-blocking state among its instruments' current (latest-inspection)
  states, using the severity ordering
  `READY_FOR_PACKAGING < PENDING_ANALYSIS < REQUIRES_SUPERVISOR_REVIEW <
  REQUIRES_RECLEANING < REQUIRES_REPAIR < REMOVED_FROM_SERVICE`. A tray is
  never reported ready if any instrument in it isn't.
- **Instrument Readiness (Module 3):** grouped by
  `instrument_barcode`/`instrument_udi` when present; falls back to a
  per-inspection key (`untracked:{type}:{id}`) when neither was captured —
  we don't claim re-identification we didn't actually perform. The most
  recent inspection for that identity is its current state.
- **Facility Readiness (Module 4):** grouped by `facility_name` (falling
  back to `site_name`). Trend compares the readiness rate of the older
  half of that facility's inspections (by `created_at`) to the newer half
  — `improving` / `declining` / `stable` / `insufficient_data` when either
  half is empty.

## Honesty constraints

- Zero cases → rates are `null`, not `0.0`.
- Zone coverage (Module 7) reports `not_assessed` (not a 0% score) when a
  technician never tagged zones — a `None` in `inspected_zones_json`.
- The anatomy-zone failure trend surfaced in the Executive Risk Dashboard
  (Module 10) comes directly from Phase 18's supervisor-adjudicated ground
  truth (`app/services/pilot_validation_service.py::compute_zone_performance`)
  — not a re-derived estimate, so the same zone-miss numbers are consistent
  across the pilot validation dashboard and this command center.
