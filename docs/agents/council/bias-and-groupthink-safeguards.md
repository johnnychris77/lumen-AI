# Project Council — Bias and Groupthink Safeguards

Sections 16 & 17 of the sprint brief.

## Safeguards implemented

- **Independent first-pass assessments** -- every resolver in
  `council_specialist_assessment_service.py` reads only the case's
  evidence package and that specialist's own real store, never another
  specialist's Council assessment.
- **Mandatory evidence citation** -- every assessment carries
  `evidence_used`, sourced directly from the specialist's real service
  output, never fabricated.
- **Dissent preservation** -- `CouncilSpecialistAssessment` rows are
  immutable; a revision creates a new row (`is_revision=True`,
  `supersedes_assessment_id`) rather than overwriting the original.
  Dissent records are never deleted or hidden (see
  `dissent-registry.md`).
- **No majority override of unresolved safety concern** -- `SAFETY_
  DISSENT` in `council_consensus_service.classify_consensus` fires
  regardless of how large the majority is, whenever a safety/evidence
  specialist (Sentinel-X, Veritas) dissents with `urgency="urgent"`.
- **Uncertainty disclosure** -- `confidence` and `evidence_limitations`
  are first-class fields on every assessment, never optional.
- **Alternative explanation requirement** -- every assessor is expected
  to populate `alternative_explanation` where a real one exists (e.g.
  Vulcan's probable-cause taxonomy).
- **Human final authority** -- see `human-decision-authority.md`; no
  Council output is final until a human decision is recorded.
- **Outcome review** -- see `outcome-effectiveness.md`.
- **Agent performance monitoring** -- see Section 17 below.
- **Configurable recusal** -- a team's optional specialist list lets an
  organization exclude a specialist it judges out of scope for a given
  team's decisions, while `SAFETY_VETO_SPECIALISTS` can never be dropped
  from a required list once required.

**Consensus is not evidence.** The Consensus Engine only ever describes
*agreement*, never correctness -- nothing in this codebase computes
"truth" from how many specialists happen to agree.

## Specialist Performance Review (Section 17)

`council_performance_service.specialist_performance_summary` computes,
per specialist, entirely from already-persisted Council tables:

- `total_assessments`, `confidence_distribution`, `abstention_count`
- `agreement_rate` -- how often the specialist's recommended action
  matched the case's eventual recommendation
- `dissent_count` / `dissent_accuracy` -- how often the specialist's
  dissent was later confirmed valid by an outcome review

This is aggregate and **non-punitive** reporting only. Critically,
nothing in this module feeds back into `council_consensus_service.
classify_consensus` -- a specialist's historical performance can never
automatically suppress its current safety or evidence dissent. The
module's own `note` field states this explicitly.
