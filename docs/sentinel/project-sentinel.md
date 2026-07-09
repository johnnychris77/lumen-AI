# Project Sentinel — Autonomous Clinical Intelligence Orchestration

LumenAI v3.0

> **Naming note**: this is a different "Project Sentinel" from the earlier
> LumenAI Inspect v2.5 module of the same codename (the Predictive
> Simulation & Clinical Scenario Engine, `app/models/simulation_engine.py`,
> route `/scenario-analysis`). The sprint spec reused the codename; this
> doc, and all of `docs/sentinel/`, refers only to the v3.0 enterprise
> monitoring layer described below.

## Mission

Transform LumenAI from a reactive inspection system into a proactive
Clinical Intelligence Platform — continuously monitoring inspections,
Digital Twins, the Knowledge Graph, workflow, quality, and enterprise
intelligence to identify risk before it reaches the operating room. **This
is not autonomous clinical decision-making.** Human validation remains
mandatory for every signal, watchlist entry, alert, and recommendation.

## Architecture

```
backend/app/models/sentinel_orchestration.py    — SentinelRiskSignal, ClinicalWatchlistEntry,
                                                    DigitalTwinFlag, SentinelAlert,
                                                    SentinelRecommendation, SentinelHealthSnapshot
backend/app/services/sentinel_engine_service.py            — Section 1 orchestrator
backend/app/services/sentinel_risk_monitor_service.py       — Section 2
backend/app/services/sentinel_watchlist_service.py          — Section 3
backend/app/services/sentinel_ai_health_service.py          — Section 4
backend/app/services/sentinel_digital_twin_monitor_service.py — Section 5
backend/app/services/sentinel_supervisor_intelligence_service.py — Section 6
backend/app/services/sentinel_dashboard_service.py          — Section 7
backend/app/services/sentinel_recommendation_service.py     — Section 8
backend/app/services/sentinel_alert_service.py              — Section 9
backend/app/routes/sentinel_orchestration.py    — /api/sentinel/*
frontend/src/components/SentinelDashboard.tsx
frontend/src/pages/SentinelPage.tsx             — route: /sentinel
```

## Reuse, not re-derivation

Sentinel is explicitly a monitoring *layer over* everything LumenAI already
computes — it composes existing engines rather than re-implementing their
math a second (or third, or fourth) time:

- Recurrence detection reuses `capa_suggestion_service`'s threshold/window
  idiom (count ≥ 3 in a 90-day window).
- AI health reuses `ml/pilot_validation.py`'s real confusion-matrix math
  (`clinical_metrics`, `confidence_calibration`) over `SupervisorReview` rows.
- Knowledge confidence reuses `knowledge_graph_service.learning_confidence`.
- Anatomy watchlisting reuses `anatomy_risk_service.anatomy_risk_dashboard`.
- Digital Twin tiering reuses `instrument_condition_service.
  instrument_condition_history`'s real condition trend/repair/corrosion data.
- The Enterprise Risk Score composes `quality_dashboard_service.
  executive_quality_score` as one weighted input.

See the sibling docs (`enterprise-monitoring.md`, `risk-monitoring.md`,
`watchlists.md`, `model-health.md`, `clinical-alerting.md`) for each
engine's specifics, and each doc's own notes on what's genuinely new vs.
reused.

## Definition of Done

LumenAI no longer waits for users to discover problems — it continuously
observes the enterprise, identifies emerging risk, explains why the risk
matters, and recommends evidence-based actions while preserving supervisor
authority. Every signal, alert, and recommendation in this module carries
`human_review_required: true` and traces back to real, named data — never
a fabricated causal claim or an unexplained number.
