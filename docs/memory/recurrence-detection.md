# Recurrence Detection (Project Insight, Section 3)

`app/services/recurrence_detection_service.py`.

## What it detects

Given one instrument's already-assembled condition history
(`instrument_condition_service.instrument_condition_history`), flags:

- **Recurring findings** — any finding type (contamination or damage) logged
  in 2 or more of this instrument's own inspections.
- **Recurring repairs** — `repair_count >= 2` (a `disposition ==
  "REMOVE FROM SERVICE"` inspection, the same repair signal
  `instrument_condition_service` already uses).
- **Recurring overrides** — 2 or more `SupervisorReview` rows for this
  instrument's inspections with a non-empty `override_action`.

Each becomes a `Recurring Issue Alert`:

```json
{"type": "recurring_finding", "finding_type": "blood", "occurrences": 3,
 "message": "Repeated blood identified in 3 of 6 inspections."}
```

## Constants reused elsewhere

`CONTAMINATION_TYPES` (`blood`, `bone`, `tissue`, `debris`,
`other_organic_residue`) and `DAMAGE_TYPES` (`corrosion`, `crack`,
`insulation_damage`, `rust`, `pitting`) are defined once here and imported by
`predictive_risk_engine.py`, `similar_instrument_search_service.py`, and
`learning_dashboard_service.py` — the same taxonomy every recurrence/risk/
similarity computation in v2.4 uses, so a finding type is never classified
differently by two different services.

## Threshold

Two-or-more occurrences (`_RECURRENCE_THRESHOLD = 2`) — a single finding
isn't a pattern; real repetition is what earns an alert. This is a real count
over real rows, not an inferred pattern or a statistical model.
