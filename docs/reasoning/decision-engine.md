# Clinical Decision Reasoning Engine (Project Cortex, Sections 2/3/4/6/8)

`app/services/decision_reasoning_service.py`, `GET /api/inspections/{id}/decision`.

## Mission

"What conclusion should an experienced SPD supervisor reach using ALL
available evidence?" — not "what does this image contain?" Recommendations
here emerge from composing multiple real evidence sources through explicit
rules, not from re-running or re-weighting the vision/scoring model.

## Evidence gathering (`gather_evidence`) — Sections 3 & 6

One evidence bundle per inspection, assembled from data that already exists
— nothing here is a second, independent AI decision:

| Field | Source |
|---|---|
| `finding_type`, `zone`, `vision_confidence` | The inspection's own highest-severity `InspectionFinding` row |
| `high_risk_zone` | `instrument_zones.is_high_retention` + `instrument_anatomy.anatomy_profile`'s declared `high_risk_zones` |
| `repeat_finding`, `repeat_occurrences` | v2.4 Clinical Memory (`clinical_memory_service.get_clinical_memory`) when the instrument is re-identified (barcode/UDI); falls back to `prioritization_engine.has_repeat_findings` for untracked instruments |
| `clinical_memory` | The full v2.4 Clinical Memory context (condition history, recurring issues, predictive risk, health forecast, similar instruments) |
| `knowledge_articles` | `knowledge_repository_service.list_articles(instrument=, finding=)` |
| `supervisor_notes` | This inspection's own `SupervisorReview.rationale` rows |
| `digital_twin` | Best-effort tenant/facility SPD workflow snapshot (`digital_twin_engine.get_twin_state`) — ambient operational context, omitted (not fabricated) when it can't be resolved |

## Explainable Decision Tree (`build_explainable_decision`) — Sections 2 & 4

```
evidence -> reasoning_path -> applied_rules -> clinical_rationale -> final_recommendation
```

- `reasoning_path` — human-readable steps naming which evidence source
  contributed and why (Finding, Anatomy, Clinical Memory, Repeat Finding,
  Digital Twin, Knowledge Articles, Supervisor Notes — only the steps with
  real data present).
- `applied_rules` — every `SPD_RULE_LIBRARY` rule (see
  `docs/reasoning/rule-library.md`) **and** every active supervisor-authored
  rule (see `docs/reasoning/explainable-reasoning.md`) whose conditions the
  evidence bundle satisfies — never a single hidden winner-take-all rule.
- `final_recommendation` — the highest-SPD-risk applied rule's own
  recommendation, with `driven_by_rule` naming exactly which rule produced
  it. No applied rules → "Routine processing" with `driven_by_rule: null`,
  never a fabricated recommendation.

## Recommendation Confidence (`compute_recommendation_confidence`) — Section 8

Three numbers, reported separately, never collapsed into one:

- **Vision confidence** — the scoring engine's own per-finding confidence
  (persisted on `InspectionFinding.confidence`, v2.3).
- **Reasoning confidence** — how many independent evidence sources
  corroborate the decision (Clinical Memory present, knowledge articles
  found, supervisor notes on record, at least one rule matched) — a simple,
  inspectable count-based heuristic, not a statistical model.
- **Overall clinical confidence** — the average of the two when vision
  confidence is available, otherwise just reasoning confidence.
