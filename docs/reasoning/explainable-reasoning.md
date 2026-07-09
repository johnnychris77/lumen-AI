# Supervisor Rule Builder (Project Cortex, Section 7)

`app/models/clinical_decision_rule.py`, `app/services/supervisor_rule_service.py`,
`POST/GET /api/decision-rules`.

## What it is — and isn't

A governed, versioned, **supervisor-editable** clinical decision rule table
— organization rules, local best practices, escalation thresholds, education
rules. Distinct from:

- **`SPD_RULE_LIBRARY`** (`docs/reasoning/rule-library.md`) — curated,
  code-shipped, immutable. Ships with the platform; only a code change
  updates it.
- **`OrganizationStandard`** (`app/models/knowledge.py`) — a free-text
  policy/compliance reference document (title + description), with no
  condition/action structure or execution semantics. Not a decision rule.
- **`AutomationRule`** (`app/models/automation_rule.py`) — workflow/
  notification automation (e.g. "when X inspection event happens, send Y
  notification"). Unrelated to clinical reasoning; do not wire clinical
  logic through it.

`ClinicalDecisionRule` is the only persisted, supervisor-authored table that
feeds the Explainable Decision Tree's `applied_rules` alongside the static
library.

## Governance: versioned, never mutated in place

`update_rule()` never edits a row — it calls `create_rule()` to insert a new
row at `version + 1`, then sets the old row's `is_active = False` and
`superseded_by_id` to the new row's id. The full history of what a rule used
to say is always reconstructable; `list_rules(active_only=True)` (the
default) only ever returns the current version of each rule.

## Roles

Read: `admin`, `spd_manager`, `supervisor`, `operator`, `viewer`. Author
(create/update/deactivate): `admin`, `spd_manager`, `supervisor` — the same
role set that already authors `SupervisorReview` overrides.

## Matching

`evaluate_supervisor_rules(db, tenant_id, evidence)` uses the same
condition semantics as `SPDRule.matches()` (finding type, zone-keyword
substring, high-risk-zone flag, repeat-finding flag, minimum repeat count) —
a supervisor-authored rule and a library rule are evaluated identically and
reported identically in `applied_rules`, distinguished only by `source`.
