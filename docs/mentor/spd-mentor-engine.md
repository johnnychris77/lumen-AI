# SPD Mentor Engine (v1.4)

## What it does
Turns an inspection analysis into active SPD education: interprets findings,
explains contamination/damage/anatomy risk, suggests structured corrective
action, and references SPD best practice — without ever replacing supervisor
judgment.

Implemented in `backend/app/services/spd_mentor_engine.py`, composed on top of
the existing Phase 13/14/15 infrastructure (`clinical_mentor.py`,
`instrument_anatomy.py`, `instrument_zones.py`, `inspection_coverage.py`)
rather than duplicating it.

## Where it runs
`build_spd_mentor(result, overall, training_mode=False)` is called from
`build_clinical_decision()` in `baseline_comparison_scoring_service.py` and
attached to every analysis under `clinical_decision.spd_mentor`. It can also be
re-derived for a past inspection via `GET /api/inspections/{id}/mentor`.

## Payload shape
```
spd_mentor: {
  disclaimer: str,
  corrective_actions: [{finding, steps: [...]}],
  anatomy_coaching: [str, ...],
  confidence_coaching: {message, suggestions} | null,
  clinical_decision_summary: {instrument, inspection_coverage, findings, risk, recommendation, supervisor_review},
  education_cards: [{finding, clinical_significance, recommended_practice, reference}],
  training_mode: bool,
  expanded_explanations?: {...}   # only when training_mode is true
}
```

## Disclaimer
Every payload carries `MENTOR_DISCLAIMER`: this guidance is AI-generated
educational support and does not replace supervisor judgment or the
manufacturer's IFU. It is never omitted.

## Never claims
Consistent with project-wide governance rules, the engine never claims
causation or regulatory clearance — corrective-action language is imperative
("Reclean the instrument") but the overall recommendation stays advisory
("Supervisor review: Recommended"), and every actionable output remains
subject to `human_review_required: true` on the parent analysis.
