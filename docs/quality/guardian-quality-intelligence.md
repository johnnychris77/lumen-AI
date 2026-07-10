# LumenAI Quality — Closed-Loop Quality Intelligence

Codename: Project Guardian · LumenAI Quality v2.9

> **Naming note**: this file is deliberately named
> `guardian-quality-intelligence.md`, not `quality-intelligence.md` — that
> filename is already taken by the existing v1.5 per-tenant quality
> dashboard (`docs/quality/quality-intelligence.md`, backed by
> `quality_intelligence.py`/`quality_dashboard_service.py`), which is itself
> already disambiguated from the P21 `quality_intelligence_service.py`
> network dashboard. This is the third distinct "quality intelligence"
> surface in the codebase; giving it a fourth identical filename would only
> compound the collision. See that existing file for how the disambiguation
> pattern was set.

## What Project Guardian actually is

The closed loop the sprint's mission diagram describes:

```
OR -> Quality Event -> Clinical Classification -> Digital Twin -> Inspection ->
Technician -> Tray -> Knowledge Graph -> Root Cause Analysis -> CAPA ->
Competency -> Continuous Improvement
```

Concretely, in this codebase:

1. **Quality Event** (`quality_event_service.py`) — intake + classification.
2. **Clinical Classification** — the deterministic keyword classifier
   (`classify_narrative`), output governed by the SPD Quality Taxonomy.
3. **Correlation** (`event_correlation_service.py`) — attempts to link the
   event to a `SurgicalCase`, `VendorTray`, `Inspection`, technician,
   supervisor, digital-twin instrument identity, and manufacturer baseline.
   Shift/washer/inspection-session correlation is recorded honestly as
   untracked — see `operational-risk-engine.md`'s sibling doc pattern in
   OR Connect for the same honesty principle applied there.
4. **Root Cause Analysis** (`rca_engine_service.py`) — an AI-drafted RCA a
   supervisor edits and approves; approval calls the existing, deliberately
   human-only `root_cause_service.assign_root_cause`.
5. **CAPA** (`capa_recommendation_service.py` + `capa_lifecycle_service.py`)
   — typed recommendations that, once accepted, materialize into the
   existing CAPA store (extended, not duplicated) with a real
   Open→Assigned→In Progress→Verified→Closed lifecycle.
6. **Competency** (`competency_intelligence_service.py`) — coaching/team/
   department opportunities derived from the existing `CompetencyEvent` log.
7. **Continuous Improvement** — via `quality_command_center_service.py`'s
   `apply_learning_loop`, which updates Clinical Memory for confirmed,
   significant events; Knowledge Graph, Reasoning Engine, Education Library,
   and Trend Analytics are all computed live from underlying data and
   reflect a confirmed event automatically, without a separate write.

## What this is not

Not a re-implementation of the existing v1.5 or P21 quality dashboards —
`command-center-summary` calls into `root_cause_trends`,
`capa_lifecycle_service.lifecycle_summary`, `first_pass_yield_service`, and
`competency_service.technician_quality_dashboard` rather than re-deriving
any of their logic.
