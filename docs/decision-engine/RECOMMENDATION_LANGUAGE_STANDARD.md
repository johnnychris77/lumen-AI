# Recommendation Language Standard

Single source of truth: `app/services/observation_taxonomy.py`.

## Preferred terms

probable, observed, visually consistent with, suspected, requires review,
recommended, baseline similarity, baseline deviation, image insufficient
(`observation_taxonomy.PREFERRED_TERMS`).

## Avoided terms

confirmed blood, definitely contaminated, sterile, safe for patient use,
clinically cleared, guaranteed clean, diagnosis, exact age of residue
(`observation_taxonomy.AVOIDED_TERMS`). Regression-tested in
`test_lumen_decision_engine.py::TestObservationLanguage::test_forbidden_terms_never_appear`
and `TestBaselineTerminology::test_baseline_score_not_called_cleanliness_or_sterility`.

## Legal posture

This wording standard reduces overstatement risk. It is not itself a legal
or regulatory clearance, and does not eliminate the need for legal,
clinical, and regulatory review before any customer-facing claim is made.
No FDA clearance or other regulatory approval is claimed anywhere in this
system's documentation or output.

## Recommendation action vocabulary

`continue_workflow`, `focused_technician_reinspect`,
`capture_additional_image`, `reclean_and_reinspect`,
`supervisor_attention_required`, `supervisor_approval_required`,
`repair_evaluation`, `manufacturer_evaluation`,
`hold_from_further_processing`, `remove_from_service_consideration`
(`app/services/lumen_decision_engine.py`, `ACTION_*` constants). These are
advisory and explainable — every recommendation returned by the Decision
Engine carries a `reason` and an `escalation_condition` string, never a
bare code.
