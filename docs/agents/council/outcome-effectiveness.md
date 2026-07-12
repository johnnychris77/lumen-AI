# Project Council — Outcome Effectiveness Review

Section 14 of the sprint brief.

## Classification (`council_outcome_service.classify_outcome`)

| Inputs | Classification |
|---|---|
| `issue_resolved is None` | `insufficient_follow_up_data` |
| `unintended_consequence=True` | `unintended_consequence` |
| Resolved, did not recur | `effective` |
| Resolved, recurred | `partially_effective` |
| Not resolved, but risk decreased or operational performance improved | `partially_effective` |
| Otherwise | `ineffective` |

## Learning signal, never automatic rule rewriting

`record_outcome_review` sets `knowledge_update_recommended=True` whenever
the classification is `ineffective` or `unintended_consequence`, or
whenever `dissent_valid=True` was reported (a specialist's dissent turned
out to be correct). This is a **signal for a human to review** -- Council
never automatically rewrites a clinical rule, the Knowledge Graph, or a
specialist's scoring logic as a result. Any such change remains a
separate, explicit, human-triggered action elsewhere in the platform.

## Closing the loop

Every `CouncilOutcomeReview` links back to its `council_case_id`, so the
original recommendation, its dissent, and its eventual outcome are always
traceable in one place -- the leadership learning dataset the brief calls
for.
