# Project Council — Council Case Schema

Section 3 of the sprint brief.

## `CouncilCase` (`app/models/council_leadership.py`)

The typed record a leadership team convenes around. Key fields:

- `case_type` -- one of the 12 named types (`CASE_TYPES`): high-risk
  inspection, recurring contamination, recurring instrument failure,
  repair recurrence, process variation, education need, CAPA escalation,
  workflow bottleneck, enterprise trend, model performance issue,
  evidence conflict, innovation proposal.
- `inspection_ids_json` / `instrument_ids_json` / `digital_twin_refs_json`
  / `evidence_package_json` -- the shared evidence package every
  specialist reads from.
- `risk_level`, `urgency`, `requested_decision`, `facility_id`.
- `team_key` / `participating_specialists_json` -- assigned at case
  open time from the Leadership Team Registry.
- `consensus_status` -- one of the six Consensus Engine outcomes
  (Section 5), set after `convene()`.
- `recommended_action` -- the majority position's action text (empty
  until convened, or when consensus is `INSUFFICIENT_EVIDENCE`).
- `required_human_approver` / `required_approval_tier` -- the highest
  authority tier any assessing specialist flagged as necessary (Section
  8).
- `status` -- `open` -> `awaiting_evidence` or `awaiting_decision` (after
  `convene()`) -> `resolved` (after a human decision is finalized).
- `human_review_required` -- always `True`.

## Related tables

- **`CouncilSpecialistAssessment`** (Section 4) -- one immutable row per
  specialist per case; `is_revision`/`supersedes_assessment_id` preserve
  the full history if a specialist revises its conclusion.
- **`CouncilDissentRecord`** (Section 6) -- one row per specialist not in
  the consensus majority.
- **`CouncilDecisionOption`** (Section 7) -- one row per distinct
  recommended action across all assessments, with tradeoffs.
- **`CouncilHumanDecision`** (Section 8) -- the final, role-gated human
  decision.
- **`CouncilMeetingNotes`** (Section 12) -- structured meeting-mode
  records; `recorded_by` is required (human-authored only).
- **`CouncilOutcomeReview`** (Section 14) -- the effectiveness review
  that closes the learning loop.

Specialist performance (Section 17) is deliberately **not** a table --
`council_performance_service.specialist_performance_summary` computes it
on the fly from the tables above, so it can never drift from the
underlying assessment/dissent/outcome history.
