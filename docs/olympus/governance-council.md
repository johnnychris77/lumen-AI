# Project Olympus — Network Governance Council

LumenAI OS v5.1, Section 9.

## Genuinely new — one generic case model, not six tables

Beacon's `AdvisoryBoardMeeting`/`AdvisoryBoardActionItem`/
`AdvisoryBoardRecommendation` triplet (`industry_collaboration.py`, v3.5)
already covers meeting-based product-roadmap governance for one industry
board; Vanguard's governance is internal, single-org executive
governance. Neither covers cross-organization case work.
`NetworkGovernanceCase` is a single model with a `case_type`
discriminator covering all six governance functions the brief names:

* `participation_review`
* `contribution_review`
* `dispute`
* `version_approval`
* `ethics_review`
* `clinical_oversight`

## Optional link to a Beacon meeting

`meeting_id` is a nullable FK to Beacon's `AdvisoryBoardMeeting` — a case
*may* be discussed at a Council meeting, but most cases (e.g. a single
contribution review) never need one, so the link is optional rather than
required.

## Every decision is audited

`file_case` and `decide_case` both call
`enterprise_audit_service.record_enterprise_audit_event` directly for a
tamper-evident record of every governance action.

```
POST /api/olympus/governance/cases
POST /api/olympus/governance/cases/{id}/decide
GET  /api/olympus/governance/cases/{id}
GET  /api/olympus/governance/cases?case_type=dispute&status=open
GET  /api/olympus/governance/summary
```

A case's terminal states are `resolved` or `dismissed`; deciding a case
already in either state is rejected rather than silently overwritten.
