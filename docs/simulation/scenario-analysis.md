# Scenario Analysis — Decision Scenario Builder & Risk Projection

Codename: Project Sentinel · LumenAI Inspect v2.5

## The four scenarios

For every inspection, `POST /api/scenario-analysis/{inspection_id}/generate`
evaluates the same four dispositions:

| Key | Label | Likely consequence |
|---|---|---|
| `reclean` | Scenario A — Reclean | Instrument returns to decontamination for a repeat clean, then repeats inspection before packaging. |
| `supervisor_override` | Scenario B — Supervisor Override | A supervisor reviews the AI finding directly and confirms, modifies, or escalates the disposition. |
| `repair_evaluation` | Scenario C — Repair Evaluation | Instrument is pulled from the tray and routed to repair evaluation before it can re-enter service. |
| `remove_from_service` | Scenario D — Remove From Service | Instrument is permanently removed from circulation and does not return to the tray. |

Exactly one scenario is marked `is_recommended: true` per run — the one
matching the AI's actual recommended disposition
(`disposition_engine.recommend_disposition`). The other three are always
generated and returned as alternatives, each with its own rationale, so a
reviewer can see what was considered and rejected, not just the final
answer.

## Risk projection fields

Each `ScenarioProjection` carries:

- `quality_risk` (0-1) — projected risk to inspection/cleaning quality if this path is taken
- `operational_impact` (0-1) — disruption to the SPD workflow
- `repeat_inspection_probability` (0-1) — likelihood the instrument needs another inspection soon
- `repair_likelihood` (0-1) — likelihood repair work is ultimately needed
- `supervisor_workload_impact` (0-1) — added supervisor review burden
- `confidence_level` (0-1) — confidence in this specific projection, reduced when inspection coverage is incomplete

These are heuristic projections seeded from the inspection's real
`risk_score` and `coverage_pct` — not measurements of a real future event.

## Reasoning and evidence

`SimulationRun.reasoning` restates the AI's grounded disposition
explanation plus a count of similar historical cases. `SimulationRun.evidence`
is the `explain_inspection` "why" chain (finding → zone → clinical
significance → SPD rule → recommendation) for this specific inspection —
the same explainability graph used by the Knowledge Graph Explorer
(`docs/knowledge-graph/`), reused here rather than re-derived.

## Endpoints

- `POST /api/scenario-analysis/{inspection_id}/generate` — generate and persist a run
- `GET /api/scenario-analysis/{inspection_id}` — fetch the latest run

Both require an authenticated user with one of `admin`, `spd_manager`,
`operator`, `viewer`. Every `generate` call is recorded to the audit log
(`scenario_analysis.generate`).
