# Clinical Rule Registry

`app/cios/rule_registry.py::CLINICAL_RULE_REGISTRY` — every rule listed
here is a **real rule already enforced somewhere in the codebase**. This
registry documents and versions rules that exist; it does not invent
hypothetical governance ahead of implementation. Each rule's `evidence`
field points at the exact function that implements it, so the registry
can never drift from what the code actually does.

## Schema

| Field | Meaning |
|---|---|
| `rule_id` | Stable identifier (`RULE-001`, …) |
| `name` | Short human-readable name |
| `purpose` | What the rule does and why |
| `evidence` | The file/function that implements it |
| `applies_to` | Which finding type(s) or scope the rule covers |
| `priority` | `critical` / `high` / `medium` |
| `version` | Rule version (bump when the underlying logic changes) |
| `approval_status` | `approved` for every rule currently live in production code |

## The ten registered rules

| ID | Name | Priority |
|---|---|---|
| RULE-001 | Structural defect escalation | critical |
| RULE-002 | Severe corrosion escalation | critical |
| RULE-003 | Residual contamination reprocessing | high |
| RULE-004 | High-retention zone escalation | high |
| RULE-005 | No-baseline supervisor gate | critical |
| RULE-006 | Baseline mismatch supervisor review | medium |
| RULE-007 | Repairable structural defect classification | medium |
| RULE-008 | Critical finding safety threshold | critical |
| RULE-009 | Incomplete zone coverage flag | medium |
| RULE-010 | Human final authority | critical |

See `app/cios/rule_registry.py` for full purpose/evidence text on each.

## What this enables

- **Explainability**: the Clinical Reasoning Agent's output and the
  Clinical Readiness Certificate can cite a specific rule ID rather than
  an unattributed "the system decided."
- **Future governance**: a rule can be versioned independently (e.g.
  RULE-004's high-retention zone list could be tightened in a `2.0`
  revision) with the change tracked here, and `approval_status` gives a
  future governance workflow (e.g. requiring a clinical lead's sign-off
  before a rule change ships) a place to attach to.
- **Audit**: `rules_applying_to(finding_type)` lets an auditor ask "which
  rules govern how LumenAI handles a crack finding?" and get a direct,
  accurate answer.

## API

`GET /api/cios/rule-registry` returns the full registry.
`get_rule(rule_id)` and `rules_applying_to(finding_type)` are the
in-process lookup helpers other CIOS modules (or a future rule-editor UI)
should use rather than re-filtering the list independently.

## Extending

Adding an eleventh rule requires it to already be enforced in code — write
the rule's actual logic first (in the appropriate service module), then
add its registry entry with `evidence` pointing at that real
implementation. A registry entry with no corresponding enforced logic
would misrepresent what LumenAI actually does, which is exactly what this
registry exists to prevent.
