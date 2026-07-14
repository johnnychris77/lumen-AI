# The Lumen Decision Engine

## Architectural separation (Section 10)

> Do not place hospital policy thresholds inside the vision-model code.
> The vision model observes. The baseline service compares. The policy
> engine resolves organizational rules. The Decision Engine recommends.

This is enforced as real module separation, not just a convention:

| Layer | Module | Responsibility |
|---|---|---|
| Vision model | `app/ai/inference.py` (`LumenAIModel`) | Produces a raw finding/confidence. No policy or threshold logic — verified by `test_lumen_decision_engine.py::TestArchitecturalSeparation`, which asserts the module's source contains no reference to `BaselineDecisionPolicy`, `policy_resolution_service`, or `lumen_decision_engine`. |
| Baseline comparison | `app/services/baseline_comparison_scoring_service.py` (`analyze_inspection`, `resolve_baseline`) | Compares the current instrument against the resolved approved baseline; computes `baseline_match_score`/`baseline_deviation_score`. Unchanged by this work — the Decision Engine consumes its output rather than duplicating it. |
| Policy engine | `app/services/policy_resolution_service.py`, `app/services/baseline_decision_policy_service.py` | Resolves the single most-specific active+approved `BaselineDecisionPolicy` for an inspection's context. |
| Decision Engine | `app/services/lumen_decision_engine.py` | The only place an observation, a resolved policy, and a recommendation are combined into the Result Contract. |

## Inputs

Per inspection: the existing `analyze_inspection()` output (model
observation/confidence, model version, image quality status, instrument
type, baseline similarity/deviation/source/version, predicted findings with
anatomy zone and risk), plus the request's `instrument_type`, `department`,
and `facility_name` used to resolve the applicable policy.

## Outputs — the Result Contract

```json
{
  "inspection_id": 123,
  "observation": {"category": "probable_blood_like_residue", "display_label": "Probable blood-like organic residue", "confidence": 0.91, "status": "model_observation"},
  "assessment": {"image_quality": "acceptable", "instrument_family": "drill_bit", "anatomy_zone": "drill-bit flute", "anatomy_zone_risk": "high", "baseline_similarity": 0.87, "baseline_deviation": 0.13, "baseline_source": "manufacturer", "baseline_version": "v2", "digital_twin_trend": "not_available"},
  "policy": {"policy_id": "policy-abc123", "policy_version": "2.3", "scope": "facility", "minimum_baseline_similarity": 0.90},
  "recommendation": {"action": "reclean_and_reinspect", "supervisor_required": false, "reason": "...", "escalation_condition": "..."},
  "limitations": ["The observation is visual and has not been laboratory confirmed.", "..."],
  "human_decision_required": true
}
```

Field names were adapted to this repository's existing conventions
(`snake_case`, `*_status`/`*_required` suffixes already used throughout
`baseline_comparison_scoring_service.py`) rather than introduced fresh.

## Persistence and immutability (Section 16)

Persisted once, at inspection-submission time, as a `LumenDecisionRecord`
row (`app/models/lumen_decision_engine.py`). The `observation_*`,
`assessment_*`, and `policy_*` columns are the original AI output and are
never rewritten. A later human decision is recorded in separate
`technician_*`/`supervisor_*`/`override_reason`/`final_human_decision`
columns via `lumen_decision_engine.record_human_followthrough()` — see
`test_lumen_decision_engine.py::TestImmutabilityAndAuditability`.

## Where it's wired in

`app/routes/inspections.py::create_inspection()` calls
`lumen_decision_engine.build_decision()` immediately after
`analyze_inspection()` succeeds, and returns the result as
`response["decision"]`. `GET /api/inspections/{id}/decision` fetches the
persisted record afterward without recomputing it.
