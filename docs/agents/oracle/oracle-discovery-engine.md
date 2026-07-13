# Oracle Discovery Engine

## Mission

Oracle is LumenAI's research and discovery specialist: it observes governed
enterprise data, proposes explainable research hypotheses, and tracks them
through a mandatory 8-stage human-gated validation pipeline
(`app/models/oracle_discovery.py`, `VALIDATION_STAGES`). Oracle never changes
a production rule, policy, or model automatically, and it never claims
causation -- every output is framed as a potential association or possible
contributing factor requiring human scientific and clinical review
(`DISCLAIMER`, `human_review_required=True` by default on every table).

## Architecture position

Oracle sits alongside the other specialists as a pure *discovery* layer. It
composes their already-computed judgments as raw material for hypotheses
rather than re-deriving anything:

| Signal source | Oracle table | Composed function |
|---|---|---|
| Tenant's own inspection/finding history | `OracleTrendObservation` | `oracle_trend_detection_service.detect_finding_rate_trend` (own two-window comparison) |
| Apollo governance-health digital twin | `OracleDigitalTwinInsight` (`source_service="apollo_quality_twin"`) | `apollo_quality_twin_service.twin_history` |
| Vulcan instrument failure progression | `OracleDigitalTwinInsight` (`source_service="vulcan_progression"`) | `vulcan_progression_service.compute_progression` / `findings_timeline` |
| Sentinel-X AI model health | `OracleModelObservation` | `sentinel_ai_health_service.compute_ai_health` |

Each composition stores the source function's own return value
(`underlying_snapshot_json` / `ai_health_snapshot_json`) verbatim rather than
recomputing it, so a reviewer can always trace an Oracle insight back to the
exact upstream computation that produced it.

## Discovery categories

Twelve categories span the brief's discovery surface area
(`DISCOVERY_CATEGORIES`): `process_pattern`, `instrument_reliability_trend`,
`education_effectiveness`, `equipment_utilization`,
`staffing_workload_correlation`, `policy_effectiveness`,
`cross_department_variation`, `seasonal_temporal_pattern`,
`emerging_risk_signal`, `ai_model_performance_drift`,
`digital_twin_divergence`, `knowledge_gap`.

## Naming disambiguation

See the full docstring in `app/models/oracle_discovery.py` for the three
namespace decisions made while building Oracle: why `"PILOT_STUDY"` is a data
value only (never a `Pilot*` class, avoiding collision with
`app/models/pilot.py`'s customer-deployment-pilot namespace), why
`OracleTrendObservation` is deliberately independent of Horizon's
network-wide `EmergingTrendAlert`, and why knowledge promotion always routes
through the existing `GovernanceApproval` table rather than writing
`KnowledgeArticle` directly.
