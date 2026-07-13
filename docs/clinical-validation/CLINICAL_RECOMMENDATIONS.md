# LumenAI — Clinical Recommendations

Objective 5 review. Two real, distinct recommendation vocabularies exist — the brief's example list is a rough blend of both, and this review reports each precisely rather than presenting a merged, invented composite.

## Vocabulary A — the Disposition Engine (`app/services/disposition_engine.py`)

7 values, each returned with a **required, grounded `explanation` string** (never a bare label):

`Proceed to Packaging` · `Reclean` · `Repeat Inspection` · `Supervisor Review Required` · `Repair Evaluation` · `Manufacturer Evaluation` · `Remove From Service`

Every brief example maps onto this vocabulary except **"increase inspection frequency," which does not exist anywhere in the codebase** — there is no service, field, or route that produces this recommendation. The closest real mechanism is Sentinel-X's escalation logic, which raises risk score / triggers supervisor review rather than adjusting inspection cadence. **This should not be described as a supported LumenAI recommendation until it is actually implemented.**

## Vocabulary B — `Inspection.disposition` (`baseline_comparison_scoring_service.py::_overall_result`)

A coarser, dashboard-facing 5-value vocabulary: `PASS` / `MONITOR` / `SUPERVISOR REVIEW` / `REPROCESS` / `REMOVE FROM SERVICE`. This is what drives pass-rate/reclean-rate reporting across `quality_dashboard_service.py`, `sentinel_dashboard_service.py`, `atlas_dashboard_service.py`, and several other consumers — it is a rollup view, not the source recommendation logic.

## Vocabulary C — the supervisor's own action vocabulary (`app/models/disposition_override.py::DISPOSITION_ACTIONS`)

7 values a human supervisor selects when acting on an AI recommendation: `approve`, `modify`, `escalate`, `reclean`, `repair`, `remove_from_service`, `manufacturer_review`. This is the human-decision vocabulary, distinct from what the AI recommended.

## Confidence thresholds — exact numbers found in code

No single universal "if confidence < X, require supervisor review" rule exists. Instead, several independent, real thresholds gate different things:

| Threshold | Location | Effect |
|---|---|---|
| 0.50 | `data_quality_guardrails_service.py` | Below this, flags "AI confidence is only X% — image quality may be insufficient" |
| 0.50 | `sentinelx_risk_scoring_service.py` / `sentinelx_risk_taxonomy_service.py` | Sentinel-X *knowledge* confidence (not image confidence) below this adds risk points |
| 0.60 | `escalation_engine.py` | The actual escalation trigger — contributes to `escalated=True` alongside other signals (critical risk tier, no approved baseline, ≥2 repeated overrides, emergency/trauma priority, repeat repair history) |
| 0.70 | `spd_mentor_engine.py`, `phoenix_recommendation_engine.py`, `capa_suggestion_service.py`, `sentinel_risk_monitor_service.py` | Confidence-coaching suggestions, review flags, and CAPA-suggestion logic all key off this same value independently |
| 0.75 | `sentinelx_risk_agent_service.py` | Labels Sentinel-X confidence "high" vs. "moderate" — a label, not a gate |
| 85% / 65-84% | `baseline_comparison_scoring_service.py::evidence_strength()` | Star-rating label ("Strong"/"Moderate" match), not a gating rule |

The escalation engine's 0.60 threshold is the closest thing to a real, enforced "low confidence forces review" rule — but it is one signal among several, not a standalone gate.

## Evidence requirement — Veritas's readiness gate

`VeritasEvidenceReadinessAssessment.readiness_category()`: `strong_evidence` (score ≥90) / `moderate_evidence` (≥75) / `limited_evidence` (≥50) / `insufficient_evidence` (<50). The score is built from real, itemized penalties (baseline-match quality, baseline governance status, image quality, anatomy coverage, identity confidence, conflicts) — never an unexplained number.

`_recommend_gate()` is the actual sufficiency gate: `insufficient_evidence` → `GATE_ANALYSIS_BLOCKED` ("do not issue a final AI conclusion from this inspection as-is"); `limited_evidence`/`moderate_evidence` → `GATE_PROCEED_WITH_LIMITATIONS`. Per the model's own docstring: *"Veritas does not independently approve an instrument — `recommended_gate` is always advisory; only a supervisor-gated action can set `final_gate_override`."*

## Required human review

`human_review_required` defaults to `True` on **35 distinct model files** across the codebase — this is not incidental; it is the field-level enforcement of a stated, repeated design principle (quoted verbatim from three separate specialist disclaimers):

- Maestro: *"It never replaces human leadership — every recommendation is explainable, evidence-based, auditable, role-aware, and subject to human approval."*
- Sentinel-X: *"It does not replace human clinical judgment — it prioritizes risk and explains why... subject to human review."*
- Veritas: *"Veritas does not independently approve an instrument."*

**Every disposition-override action except a plain `approve` requires a non-empty reason**, enforced in `disposition_workspace_service.py` (not merely documented — a real `ValueError`/HTTP 422 on violation):
```python
_REASON_REQUIRED_ACTIONS = {a for a in DISPOSITION_ACTIONS if a != "approve"}
if action in _REASON_REQUIRED_ACTIONS and not reason.strip():
    raise ReasonRequiredError(...)
```

**Root-cause categorization is deliberately human-only, confirmed by direct code inspection** (`app/models/root_cause.py`): *"never inferred automatically, since guessing 'why' a finding occurred without a human judgment would be a fabricated causal claim."* An AI-suggested root-cause draft (`RCADraft`) is only ever a suggestion a supervisor approves or rejects — it "never writes a `RootCauseAssignment` itself."

## LumenAI never makes an irreversible decision autonomously — verified enforcement

`app/services/steward_action_service.py::transition_status` hard-blocks (raises `ValueError`, not a soft warning) any attempt to move a governed action to `APPROVED`/`CLOSED`/`CANCELLED` unless the acting user's role resolves to a tier at or above the action's required tier via `ROLE_AUTHORITY_TIER` — a dict containing only real human tenant roles (`viewer`/`operator`/`spd_manager`/`admin`), never a system or agent identity. `TERMINAL_STATUSES` additionally prevents any further mutation of a closed/cancelled action — a new action must be created and linked, the closed record is never reopened. No automated or agent-triggered path to an irreversible state exists anywhere in the codebase.

## Limitations (cross-referenced)

See [AI_LIMITATIONS.md](./AI_LIMITATIONS.md) for the full limitations catalog, and [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md) for why the finding categories a recommendation is based on are themselves inconsistently defined across the codebase.
