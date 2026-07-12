# Specialist Integrations

Steward composes existing specialists' services rather than re-deriving
their judgments.

## Council (Section 15)

`steward_council_integration_service.create_action_from_council_decision`
requires a recorded `CouncilHumanDecision` for the case -- it refuses to
create an action from a Council Case with no human decision yet.
`council_status_return` reports implementation status, completion-evidence
sufficiency, measured outcome, unintended consequences, and a closure
recommendation back to Council. **Council may reopen a case when
implementation fails or new evidence changes the decision; Steward only ever
recommends this (`recommend_reopen`), it never reopens a Council Case
itself.**

## Aegis (Section 16)

`steward_specialist_integration_service.get_aegis_process_outcome` wraps
`vulcan_aegis_integration_service.compute_process_variation_signal` as-is.
Aegis's finding stays **separately traceable** -- it is never merged into
Steward's own `GovernedActionOutcomeReview` record, only referenced.

## Vulcan (Section 17)

`get_vulcan_reliability_outcome` wraps
`vulcan_reliability_agent_service.run_reliability_assessment`.
`update_action_effectiveness_from_vulcan` writes a summary of that result
into the action's `actual_outcomes` field, satisfying "Vulcan repair outcome
updates action effectiveness."

## Sage (Section 18)

`check_sage_training_dependency_satisfied` reads
`sage_learning_plan_service.list_plans(..., completion_status="completed")`
for the given learner/group. **Steward never independently determines
competency** -- it only reads Sage's own completion status.

## Veritas (Section 19)

`steward_verification_service.check_veritas_evidence_sufficiency` wraps
`veritas_evidence_agent_service.run_evidence_assessment`. A result is
sufficient only when Veritas's `readiness_category` is `strong_evidence` or
`moderate_evidence` *and* it reports no open limitations; otherwise the
verification is recorded insufficient with Veritas's own reason.

## Sentinel-X (Section 20)

`steward_residual_risk_service` reads Sentinel-X's own already-persisted
`SentinelXRiskAssessment` rows (average `risk_score` for an instrument)
rather than recomputing risk from scratch, to populate `risk_after`.
Closure of a high-risk action requires a reviewed residual-risk row to
exist.

## Apollo and Phoenix (Section 21)

Apollo's CAPA/audit/policy/competency/effectiveness-review work and
Phoenix's improvement recommendations both flow into Steward purely through
`source_type` (`"capa"`, `"phoenix_improvement_recommendation"`) and
`source_id` -- Steward is the governed execution layer for approved work
from both, with no separate Apollo/Phoenix-specific service module needed.
