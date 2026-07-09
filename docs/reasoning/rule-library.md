# SPD Rule Library (Project Cortex, Section 5)

`app/services/spd_rule_library.py`, `GET /api/decision-rules/library`.

The first genuinely new rule abstraction in the platform. Everything that
looked like a "rule" before this (`_integrity_status()`, `evidence_strength()`
in `baseline_comparison_scoring_service.py`, the legacy
`_INSTRUMENT_ZONE_RULES` table in `instrument_zones.py`) was an inline Python
conditional with no explicit ID, evidence binding, or audit trail. Rules here
are declarative `SPDRule` dataclasses matched against the evidence bundle
`decision_reasoning_service.gather_evidence()` produces, so every match can
be reported as "rule X fired because evidence Y was present" — never a
silent threshold buried in scoring code.

## Shape

Each rule: `id`, `title`, `description`, evidence conditions
(`finding_types`, `zone_keywords`, `requires_high_risk_zone`,
`requires_repeat_finding`, `min_repeat_occurrences`), `severity`, `spd_risk`,
`recommendation` (list of concrete actions).

Zone matching is substring-based against the instrument's own declared zone
name (e.g. "jaw serrations", "o-ring area", "hinge/joint", "cutting flutes")
since the same anatomical concept is spelled slightly differently across the
anatomy library's 112 families — the same tolerant-matching approach the
legacy zone table already uses.

## The library

| Rule | Evidence | SPD Risk | Recommendation |
|---|---|---|---|
| Blood in serrations | `blood` + zone contains "serration" | High | Focused manual reclean of the serrations, supervisor review |
| Corrosion in O-ring | `corrosion`/`rust` + zone contains "o-ring" | High | Remove from service pending repair evaluation, supervisor review |
| Repeated debris | `debris`, repeat finding, 2+ occurrences | Moderate | Focused reclean, technician retraining note, repeat inspection |
| Crack in hinge | `crack` + zone contains "hinge" | Critical | Remove from service immediately, no reprocessing — escalate for repair |
| Missing insulation | `insulation_damage` | Critical | Remove from service immediately, escalate to biomedical engineering |
| Bone in drill flute | `bone` + zone contains "flute" | High | Focused reclean of the flute, borescope re-inspection |
| Blood in a high-risk serrated jaw, previously seen | `blood` + zone contains "serration" + high-risk zone + repeat finding | Critical | Focused reclean, supervisor review, repeat inspection (the sprint's own worked composite example) |

`evaluate_rules(evidence) -> list[dict]` returns every rule that matches —
composition (Section 3), not a single winner.
