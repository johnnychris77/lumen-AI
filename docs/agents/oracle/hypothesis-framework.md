# Hypothesis Framework

## The Research Registry record

`OracleHypothesis` (`app/models/oracle_discovery.py`) is the durable record
for one research hypothesis: `hypothesis_code` (e.g. `ORC-00001`,
`oracle_hypothesis_service.create_hypothesis`), `discovery_category`,
`title`, `observation_summary`, `hypothesis_statement`,
`supporting_literature`, `related_instruments`, `related_anatomy`,
`digital_twin_refs`, `knowledge_links`, `evidence`,
`statistical_summary`, `sample_size`, `confidence_level`, `current_stage`,
`research_owner`, `outcome`, `outcome_summary`, `rejected_reason`.

## Confidence is graded, never binary

`CONFIDENCE_LEVELS = [exploratory, emerging, moderate, strong]`. A
hypothesis is created at `exploratory` and only ever re-graded through
`oracle_hypothesis_service.set_confidence_level`, which records the change
as an auditable event (`OracleStageTransition` with `from_stage ==
to_stage`) -- confidence never silently drifts.

## Evidence is append-only

`oracle_hypothesis_service.add_evidence` appends `{evidence_type, summary,
submitted_by, recorded_at}` to `evidence_json`; prior entries are never
edited or removed, so a hypothesis's full evidentiary history stays
reconstructable. Discussion comments recorded via
`oracle_collaboration_service.add_discussion_comment` use the same
append-only evidence list with `evidence_type="discussion_comment"`.

## Framing constraint

`hypothesis_statement` and `outcome_summary` must always read as a
potential association or possible contributing factor, never a causal
claim (repository `CLAUDE.md`: "Never claim causation"). This is enforced
by convention at the point every caller writes these fields, not by
runtime validation of free text -- the UI's hypothesis-creation form labels
the field accordingly ("potential association only -- never causal").

## Research collaboration

`oracle_collaboration_service.reassign_research_owner` changes
`research_owner` and records the change via the same `OracleStageTransition`
trail the validation pipeline uses, so ownership history lives alongside
pipeline history rather than in a separate log.
