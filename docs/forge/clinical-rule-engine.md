# Project Forge — Clinical Rule Engine & No-Code Rule Builder

LumenAI OS v4.1 — Sections 2 & 3

## Why this is genuinely new code, not a duplicate

`app/automation_engine.py::_matches` already exists in this codebase and
is used by real call sites — but it is a **flat AND-of-fields matcher
only**. Every rule/escalation/validation/prioritization engine in this
codebase was checked before writing `forge_rule_engine.py`; none
implement nested boolean (AND/OR/NOT) conditions. `automation_engine.py`
is left completely untouched — Forge's rule engine is a new, separate
module rather than a retrofit that could change how existing
`AutomationRule` call sites behave.

## Condition tree shape

A leaf condition:

```json
{"field": "finding", "operator": "eq", "value": "blood"}
```

A boolean node (arbitrarily nestable):

```json
{"op": "and", "conditions": [
  {"field": "instrument_family", "operator": "eq", "value": "kerrison"},
  {"op": "and", "conditions": [
    {"field": "finding", "operator": "eq", "value": "blood"},
    {"field": "inspection_zone", "operator": "eq", "value": "serration"}
  ]}
]}
```

`forge_rule_engine.evaluate_condition(condition, context)` recurses
through `and`/`or`/`not` nodes down to leaves, evaluated against a real
execution context (`forge_execution_service.build_context`, built from
an actual `Inspection`/`InspectionFinding` row — never a fabricated
field). A field missing from the context fails closed (never matches),
rather than being guessed.

## Supported condition fields (Section 3)

`app/models/workflow_forge.py::CONDITION_FIELDS` — the sixteen fields
the sprint names: instrument family, manufacturer, model, inspection
zone, finding, severity, coverage %, confidence, technician role,
supervisor decision, digital twin health, facility, department,
procedure, time, shift.

## Operators

- Boolean: `and`, `or`, `not` (`RULE_OPERATORS`).
- Leaf: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`
  (`LEAF_OPERATORS`).

## Rule lifecycle

A `WorkflowRule` starts `approval_status = "pending"`; only an approved
rule is evaluated by `forge_rule_engine.evaluate_all_rules` (the batch
path a Conditional Branch node or workflow execution would use) — a
pending or rejected rule is never silently applied. Rules are versioned
with the same `supersedes_id` pattern as workflows (see
`docs/forge/workflow-versioning.md`).

## Actions

Every rule carries an ordered `actions` list (`[{"type": ..., "params":
{...}}]`), evaluated by `forge_action_service.execute_action` when the
rule matches during a workflow's Conditional Branch node — e.g. the
sprint's own example (Kerrison + Blood + Serration → Require Supervisor
Review, Recommend Reclean, Capture Knowledge Note, Update Digital Twin)
is expressed as four action entries.

## Endpoints

```
POST /api/forge/workflow-rules
GET  /api/forge/workflow-rules
GET  /api/forge/workflow-rules/{id}
POST /api/forge/workflow-rules/{id}/approve
POST /api/forge/workflow-rules/{id}/evaluate   — evaluate one rule against a supplied context, for testing
```
