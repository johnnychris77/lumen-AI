# Clinical Service Readiness Engine (v1.6)

## What it does
Answers: is this instrument suitable to proceed through the remainder of the
reprocessing workflow after clinical inspection?

Built as a thin vocabulary layer over the existing pre-sterilization
readiness classification (`pre_sterilization_command_center_service.classify_readiness`,
introduced by an earlier phase) rather than re-deriving disposition logic a
third time. `app/services/readiness_engine.py::compute_readiness()` maps that
classification onto v1.6's spec vocabulary and adds the repair-history signal
the spec asks for.

## Inputs
- Inspection findings and severity (`predicted_findings` from the AI analysis)
- Coverage score (`Inspection.coverage_pct`)
- Baseline match (`baseline_status`, `baseline_source`)
- Instrument condition / damage assessment (`detected_issue`, `risk_level`)
- Supervisor review (`SupervisorReview` rows for this inspection)
- Repair history (`has_repair_history()` — a prior REMOVE FROM SERVICE
  disposition on the same physical instrument, identified by barcode/UDI)

## Output
- `readiness_score`: 0-100 (the same `100 - risk_score` the scoring engine
  already computes — never a separate fabricated number)
- `status`: one of **Ready**, **Ready with Supervisor Approval**, **Requires
  Recleaning**, **Requires Repair**, **Remove From Service**, plus two honest
  additions beyond the spec's five — **Pending Supervisor Review** and
  **Pending Analysis** — for inspections that haven't finished the workflow
  yet. Collapsing an unfinished inspection into one of the five outcomes
  would misrepresent it as complete.

## Instrument identity
Grouped by `instrument_barcode`/`instrument_udi` when captured; falls back to
an explicit `untracked:{type}:{inspection_id}` key rather than claiming a
re-identification that was never actually performed.
