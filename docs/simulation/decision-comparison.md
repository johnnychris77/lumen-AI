# Decision Comparison Dashboard

Codename: Project Sentinel · LumenAI Inspect v2.5

## Route

`/scenario-analysis` (`frontend/src/pages/ScenarioAnalysisPage.tsx`, rendering
`frontend/src/components/ScenarioAnalysisDashboard.tsx`).

## Layout

Five tabs:

1. **Recommendation** — enter an inspection ID and generate a run. Shows
   the reasoning summary, all four scenario cards (recommended one
   highlighted), the evidence chain, and — for `admin`/`spd_manager` — a
   form to record the actual outcome once known (Outcome Learning).
2. **Workflow Impact** — for the currently loaded run, projects effects on
   the inspection queue, OR readiness, repair backlog, and technician/
   supervisor workload (Section 4).
3. **Instrument Health** — look up a physical instrument by barcode and see
   its health trend, corrosion/damage progression, and expected remaining
   service life (Section 5).
4. **Educational Mode** — compare "what if we reclean / repair / remove
   from service" narratives for an instrument type + finding type, backed
   by real historical `ClinicalCase` outcomes (Section 6).
5. **Analytics** — enterprise-wide: most common recommended scenarios,
   prediction accuracy, most effective recommendation, override outcomes,
   and repair outcomes (Section 9). Restricted to `admin`/`spd_manager`.

## Workflow Impact Analysis (Section 4)

`GET /api/scenario-analysis/{inspection_id}/workflow-impact` requires a
scenario run to already exist for that inspection (404 otherwise — the
workflow impact is always relative to a specific recommended scenario, not
a generic estimate). Returns:

- `inspection_queue_impact_hours`
- `or_readiness_impact` (`none` / `minor_delay` / `significant_delay`)
- `repair_backlog_impact`, `technician_workload_impact`,
  `supervisor_workload_impact`, `instrument_availability_impact` (all 0-1)
- `narrative` — a one-line plain-language summary

## Enterprise Scenario Analytics (Section 9)

`GET /api/scenario-analysis/analytics` (leadership roles only) aggregates:

- `most_common_scenarios` — count of runs recommending each scenario key
- `most_effective_recommendation` — the scenario recommended most often
- `prediction_accuracy` / `prediction_sample_size` — from recorded
  `ScenarioOutcome` rows (Outcome Learning)
- `override_outcomes` — distribution of `DispositionOverride.action` values
- `repair_outcomes` — count of outcomes that actually resolved to repair

## Governance

Every response on this surface carries `human_review_required: true` and
the fixed disclaimer:

> Simulation output represents potential associations projected from
> historical inspection patterns for planning purposes only. It does not
> establish causation, predict a specific outcome, or constitute a clinical
> decision. Human review and approval are required before any operational
> or clinical action is taken.

This mirrors the governance pattern already established by the P22
Digital Quality Twin (`docs/quality/` — `ScenarioSimulation`,
`QualityForecast`, `InterventionModel`) rather than introducing a new one.
