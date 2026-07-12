# Project Council — Consensus Engine & Decision Journal Integration

Sections 5 & 13 of the sprint brief.

## Classification (`council_consensus_service.classify_consensus`)

Given the latest (post-revision) assessment per required specialist:

1. **Missing required specialist** -> `INSUFFICIENT_EVIDENCE`.
2. **Evidence-blocked** -- any specialist with `confidence="low"`, an
   empty `recommended_action`, and non-empty `evidence_limitations` ->
   `INSUFFICIENT_EVIDENCE` (Council cannot make a supported
   recommendation).
3. **All positions match** -> `UNANIMOUS`.
4. Otherwise, bucket by normalized `recommended_action` text and find the
   majority position:
   - If any dissenter is a safety/evidence specialist
     (`SAFETY_VETO_SPECIALISTS` -- Sentinel-X, Veritas) with
     `urgency="urgent"` -> **`SAFETY_DISSENT`, regardless of majority
     size**. A simple majority never overrides unresolved safety
     dissent.
   - Majority >= 80% -> `STRONG_CONSENSUS`.
   - Majority < 60% -> `SPLIT_DECISION`.
   - Otherwise -> `CONDITIONAL_CONSENSUS`.

Consensus is never treated as evidence -- classification only describes
*agreement*, never *correctness*. Every dissenting assessment is recorded
via `council_dissent_service.record_dissent_records` regardless of the
final classification, so dissent is never hidden from the final report.

## Decision Journal Integration (Section 13)

Rather than building a second, parallel decision-journal schema, Council
composes a real `MaestroRecommendation` row (`council_decision_journal_
service._ensure_maestro_recommendation`) representing its synthesized
recommendation -- subject, rationale (citing consensus status,
participating specialists, and dissent), confidence, and the specialists
consulted -- then records the human decision through Maestro's own
`maestro_decision_journal_service.record_decision`. This writes into the
same leadership learning dataset Maestro's Leadership Workspace already
reads from, rather than a second, disconnected one.
