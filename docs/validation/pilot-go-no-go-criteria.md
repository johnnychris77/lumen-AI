# Pilot Go / No-Go Criteria — Phase 18

## Purpose

Defines the readiness gate LumenAI must clear before a pilot deployment can
expand beyond its initial validation cohort. Computed by
`evaluate_go_no_go()` in `app/services/pilot_validation_service.py` and
exposed at `GET /api/pilot-validation/go-no-go`.

This is an **operational readiness signal**, not a regulatory or clinical
determination — see the disclaimers on every report payload.

## GO Criteria (all must hold)

| Criterion | Threshold |
|---|---|
| No unresolved critical safety issues | Zero critical (blood/tissue/organic-residue/crack/missing-component) false negatives without a recorded final disposition. |
| Acceptable critical false-negative rate | Every critical finding type's false-negative rate ≤ **5%** (`CRITICAL_FN_RATE_THRESHOLD`). |
| Supervisor agreement above threshold | Overall supervisor agreement rate ≥ **85%** (`SUPERVISOR_AGREEMENT_THRESHOLD`). |
| Documented limitations | The validation report's `limitations` section is populated and current. |
| Sufficient data | At least one adjudicated pilot case exists (an empty dataset cannot support a GO decision). |

## NO-GO Triggers (any one blocks expansion)

- Repeated missed critical findings — an unresolved critical false negative
  is present.
- High false-negative rate — any critical finding type exceeds the 5%
  threshold.
- Poor image quality without mitigation — reflected by a persistently high
  `inconclusive_cases` count that isn't trending down between reviews.
- Unreliable zone assignment — a persistently high `missing_required_zones`
  count in the safety queue, or override rates on zone assignment that
  exceed what's expected for pilot-stage (non-CV-localized) zone logic.

## Decision Output

```json
{
  "decision": "GO" | "NO-GO",
  "reasons": ["..."],
  "criteria": {
    "critical_false_negative_rate_ok": true,
    "critical_false_negative_threshold": 0.05,
    "supervisor_agreement_rate": 0.91,
    "supervisor_agreement_threshold": 0.85,
    "supervisor_agreement_ok": true,
    "unresolved_critical_safety_issues": 0
  },
  "human_review_required": true
}
```

A `NO-GO` decision always includes the specific `reasons` that blocked it,
so the pilot team knows exactly what to remediate before the next review.

## Review Cadence

The go/no-go decision should be re-evaluated:
- After every batch of new supervisor reviews is submitted.
- Before any decision to expand the pilot to additional sites or instrument
  families.
- Whenever a critical false negative is reported through the safety review
  queue.

## Escalation

Any `NO-GO` decision, or any critical missed finding, should be routed to
the Quality/Safety Reviewer role defined in
`docs/validation/pilot-validation-protocol.md` before further pilot
expansion is discussed.
