# Supervisor Escalation Model

Exception-based, not blanket. Implemented in
`app/services/lumen_decision_engine.py::_build_completed_contract()`.

## Supervisor review MAY be required for

- An unknown/unclassifiable finding (a signal outside the model's
  validated taxonomy) — always, unconditionally.
- A probable finding at a critical/high SPD risk tier.
- Insufficient image quality / no approved baseline / analysis failure.
- Baseline similarity below the organization's approved review threshold.
- A condition remaining after recleaning (tracked via
  `escalation_condition` text on the record; enforced operationally, not
  yet a separate automated re-check — see Known Limitations below).
- Probable structural damage or progressive corrosion-like degradation.
- A policy-defined high-risk anatomy zone or repair/manufacturer
  evaluation.

## Routine cases that do NOT require supervisor approval

- No actionable abnormality observed, evidence quality sufficient, and the
  applicable policy's pass threshold is met → `continue_workflow`.
- Probable contamination identified and the applicable policy does not
  require supervisor approval for the initial recleaning decision →
  `reclean_and_reinspect` with `supervisor_required: false`. This is the
  worked example from Section 4: a 96% baseline similarity with a probable
  blood-like observation still recommends recleaning, but does not by
  itself require a supervisor for that first recleaning attempt.

## Known limitation

"Condition remains after recleaning" is currently expressed only as the
`escalation_condition` string on the Result Contract — there is no
automated hook yet that re-evaluates a inspection specifically because a
prior recleaning didn't resolve a finding. That would require this
inspection and its predecessor to be recognized as the same physical
instrument occurrence (via the existing barcode/UDI identity matching
already used by `readiness_engine.has_repair_history`) and is left as a
follow-up rather than fabricated here.
