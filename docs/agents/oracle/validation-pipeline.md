# Validation Pipeline

## The 8 stages

`VALIDATION_STAGES` (`app/models/oracle_discovery.py`):

```
OBSERVATION -> HYPOTHESIS -> EVIDENCE_REVIEW -> SCIENTIFIC_VALIDATION ->
PILOT_STUDY -> CLINICAL_REVIEW -> GOVERNANCE_APPROVAL -> PRODUCTION_KNOWLEDGE
```

Plus a terminal `REJECTED` stage reachable from any non-terminal stage.
`TERMINAL_STAGES = {PRODUCTION_KNOWLEDGE, REJECTED}`.

## Oracle may not bypass any stage

`oracle_validation_pipeline_service.advance_stage` only ever moves a
hypothesis to the single next entry in `VALIDATION_STAGES` -- there is no
"skip ahead" parameter, and calling it on a terminal-stage hypothesis raises
`ValueError`. Every transition (forward or terminal) is recorded in
`OracleStageTransition`, an append-only audit trail.

## Closing out a hypothesis

`close_out_hypothesis` moves a hypothesis straight to `REJECTED` from any
non-terminal stage, with one of three outcomes:
`rejected` / `withdrawn` / `inconclusive` (`OUTCOME_REJECTED` /
`OUTCOME_WITHDRAWN` / `OUTCOME_INCONCLUSIVE`). A hypothesis never needs to
climb the full ladder to be closed -- evidence review, owner withdrawal, or
an inconclusive result can end it at any point, and a non-empty `reason` is
required.

## Promoting to production knowledge

Reaching `PRODUCTION_KNOWLEDGE` -- the only stage that authorizes a
discovery to influence real production behavior -- requires:

1. Manager-tier-or-above authorization
   (`ROLE_AUTHORITY_TIER[changed_by_role] >= TIER_PROMOTE_TO_PRODUCTION_KNOWLEDGE`,
   reusing Council's exact role-to-tier mapping, the same convention Steward
   established).
2. Non-empty `gate_check_notes` recording what was actually reviewed.

On promotion, `outcome` is set to `promoted_to_knowledge`.

## Stage history

`oracle_validation_pipeline_service.stage_history` returns every
`OracleStageTransition` for a hypothesis in chronological order -- the
route `GET /api/oracle/hypotheses/{id}` includes it alongside the
hypothesis record.
