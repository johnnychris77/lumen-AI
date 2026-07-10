# Predictive Risk Engine (Project Insight, Section 4)

`app/services/predictive_risk_engine.py`.

⚠️ **Deterministic heuristic — not a validated predictive model.** Every
likelihood is derived only from this instrument's own recorded history
(condition trend, recurring finding counts, repair count, override count) —
never a claim of causation, and every response carries
`human_review_required: true`.

## Outputs

| Field | Derived from |
|---|---|
| `repeat_contamination_likelihood` | Recurring-finding count restricted to `CONTAMINATION_TYPES` |
| `repair_likelihood` | This instrument's own `repair_count` |
| `supervisor_escalation_likelihood` | Recurring-override count |
| `removal_from_service_likelihood` | `repair_count`, bumped by 1 when the condition trend is declining |
| `overall_risk_level` | The highest of the four above |

Each is one of `Low` / `Moderate` / `High` / `Critical`, from fixed count
thresholds (`_level_from_count`) — not a black-box score, so the reasoning
behind any level is always inspectable from the same numbers the technician
can see in Clinical Memory's `condition_history`/`recurring_issues`.

## Governance

`basis` always states plainly that this is "a potential association, not a
validated predictive model or a claim of causation" — matching the
platform-wide rule that no automated output here is self-executing or
diagnostic.
