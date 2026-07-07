# Clinical Decision Support — v1.4 additions

## Clinical Decision Summary
`spd_mentor.clinical_decision_summary` gives the concise, plain-language
summary a supervisor scans first:

```
{
  "instrument": "Rigid Scope",
  "inspection_coverage": 95,
  "findings": "Blood indicators detected within the O-ring region.",
  "risk": "High",
  "recommendation": "Reclean and repeat inspection before packaging.",
  "supervisor_review": "Recommended"
}
```

`supervisor_review` is `"Recommended"` whenever the overall disposition is
`SUPERVISOR REVIEW`, `REPROCESS`, or `REMOVE FROM SERVICE`, and `"Not
required"` for `PASS`/`MONITOR` — derived from the same disposition already
computed by the Phase 13 Explainable AI Clinical Decision Support payload, not
a separate judgment.

## Corrective Action Recommendations
`spd_mentor.corrective_actions` gives one structured, ordered step chain per
actionable finding (severity index ≥ 1), e.g.:

- **Blood** → Reclean → Brush serrations manually → Flush the lumen → Repeat
  visual inspection → Supervisor verification.
- **Rust / Corrosion** → Remove from service → Evaluate for repair → Inspect
  surrounding anatomy → Document corrosion.
- **Crack** → Remove from service immediately → Notify supervisor → Repair
  evaluation.

Full chains for all twelve categories live in
`spd_mentor_engine.CORRECTIVE_ACTION_CHAINS` and are reused by the Educational
Knowledge Library so the two never drift apart.

## AI Confidence Coaching
`spd_mentor.confidence_coaching` returns `null` when confidence and coverage
are both adequate. Otherwise:

```
{
  "message": "Confidence is limited because image quality and inspection coverage are incomplete.",
  "suggestions": ["Capture additional images.", "Capture missing anatomy zones.", "Improve lighting.", "Request supervisor review."]
}
```

Triggered when confidence < 70%, required-zone coverage < 75%, or zones were
never tagged at all (`inspection_coverage.assessed == false`).
