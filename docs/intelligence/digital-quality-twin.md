# Healthcare Digital Quality Twin — Architecture Documentation

## Overview

The Digital Quality Twin (DQT) is a unified state model of a healthcare facility's instrument
and process quality. It is **not** a patient digital twin and does not model individual patient
pathways, outcomes, or identifiable health information.

The DQT continuously ingests signals from nine operational quality data sources, synthesises
them into a versioned `QualityTwinState`, and surfaces scenario simulations, risk forecasts,
intervention models, and executive decision briefs — all gated behind human review.

---

## Governance Constraints

- **Human review required** on every output. No output drives autonomous operational decisions.
- **Association language only.** The system identifies potential associations between quality
  signals. It does NOT establish, imply, or claim causation.
- **No clinical claims.** The DQT does not diagnose patients, predict patient outcomes, or
  constitute clinical guidance.
- Every response includes a `human_review_required: true` flag and a `disclaimer` field.

---

## Data Ingestion Pipeline — 9 Input Sources

| # | Source | Signal Type |
|---|--------|-------------|
| 1 | SPD Operations | Instrument processing metrics, cycle counts, failure rates |
| 2 | Inspection Intelligence | Inspection pass/fail rates, defect patterns, tray quality |
| 3 | Patient Safety Intelligence | Near-miss correlations, safety event links, harm signal associations |
| 4 | Quality Events | Non-conformance reports, deviations, complaints |
| 5 | CAPAs | Corrective and preventive actions, effectiveness signals |
| 6 | Vendor Performance | Supplier scorecards, delivery quality, regulatory history |
| 7 | Recall Data | Active and historical device/instrument recalls, exposure estimates |
| 8 | Infection Prevention Signals | Environmental monitoring, HAI association signals |
| 9 | National Benchmarking | Peer facility percentile rankings, industry quality norms |

---

## State Representation — QualityTwinState

The `QualityTwinState` is a point-in-time snapshot of a facility's composite quality posture.

```
QualityTwinState
├── overall_quality_score          Float  0.0–1.0  (composite weighted score)
├── inspection_quality_score       Float  0.0–1.0
├── patient_safety_score           Float  0.0–1.0
├── vendor_performance_score       Float  0.0–1.0
├── recall_exposure_score          Float  0.0–1.0  (higher = more exposure)
├── infection_prevention_score     Float  0.0–1.0
├── capa_effectiveness_score       Float  0.0–1.0
├── benchmarking_percentile        Float  0–100
├── open_emerging_risks            Integer
├── open_investigations            Integer
├── pending_recommendations        Integer
├── active_recalls                 Integer
├── trend_direction                String  (improving/stable/declining)
├── trend_confidence               Float  0.0–1.0
├── data_source                    String  (live/simulated)
├── human_review_required          Boolean  always True
└── snapshot_date                  DateTime
```

---

## Scenario Simulation Engine

The scenario simulation engine models what-if interventions against the current twin state.
Each simulation:

1. Takes the current `QualityTwinState` as baseline
2. Applies a parameterised intervention (see Intervention Types below)
3. Projects `projected_quality_delta` and `projected_risk_reduction` over a configurable
   `projected_timeframe_days` horizon (default 90 days)
4. Returns a `confidence_score` and `association_reason` explaining the basis for the projection
5. **Does not execute** any operational change — output is advisory only

Simulations are stored in `ScenarioSimulation` with `status = "draft"` until a human reviewer
approves them.

---

## Risk Forecasting — 30 / 60 / 90 Day Projections

The DQT generates forward-looking quality risk projections at three horizons:

| Horizon | Purpose |
|---------|---------|
| 30 days | Near-term operational planning |
| 60 days | Mid-term quality programme adjustments |
| 90 days | Strategic supplier and CAPA investments |

Each `QualityForecast` contains:
- `projected_quality_score` — modelled quality score at horizon
- `projected_risk_level` — low / moderate / high / critical
- `risk_drivers` — JSON list of top contributing signal categories
- `recommended_interventions` — JSON list of suggested actions (advisory)
- `confidence_score` — statistical confidence in projection (0.0–1.0)
- `association_reason` — narrative basis for projection

Forecasts show slight quality deterioration without active interventions, reflecting the
association between inaction and declining quality signals observed in historical data.

---

## Intervention Modeling

Five intervention types are modelled:

| Intervention Type | Target | Typical Timeframe |
|-------------------|--------|------------------|
| `vendor_change` | Underperforming supplier | 60–90 days |
| `inspection_frequency_increase` | High-risk instrument trays | 30 days |
| `capa_closure` | Open corrective actions | 30–60 days |
| `recall_response` | Active device recalls | 14–30 days |
| `training_intervention` | SPD / inspection staff | 45–60 days |

Each `InterventionModel` provides:
- `baseline_quality_score` vs `projected_quality_score`
- `projected_improvement` (delta)
- `effort_estimate` (low/medium/high)
- `confidence_score`
- `association_reason` (no causation language)

---

## Executive Decision Support

Role-based `ExecutiveDecisionBrief` objects surface the most decision-relevant signals per
leadership role:

| Role | Focus |
|------|-------|
| `CEO` | Enterprise risk posture, board-level headline risk |
| `COO` | Operational throughput risk, vendor exposure |
| `CNO` | Patient safety signal associations, nursing quality |
| `CQO` | CAPA effectiveness, inspection quality, benchmarking |
| `quality_director` | Open investigations, emerging signals, recommendations |
| `market_director` | Vendor exposure, recall risk, competitive quality standing |

Each brief includes: `headline_risk`, `top_concerns`, `recommended_actions`,
`emerging_signals_count`, `quality_trend`, `vendor_exposure_summary`,
`recall_exposure_summary`, `patient_safety_summary`.

---

## ASCII Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   9 DATA SOURCE INGESTION LAYER                 │
│                                                                 │
│  SPD Ops │ Inspections │ Patient Safety │ Quality Events │ CAPA │
│  Vendor  │   Recalls   │ Infection Prev │  Benchmarking        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │  synthesize_twin │  (aggregates all 9 sources)
                   └────────┬────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │   QualityTwinState   │  (versioned snapshot)
                  └──────────┬───────────┘
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
    ┌──────────────┐ ┌────────────────┐ ┌──────────────────┐
    │ QualityFore- │ │ ScenarioSimul- │ │ InterventionModel│
    │ cast (30/60/ │ │ ation (what-if)│ │ (5 types)        │
    │ 90 days)     │ └───────┬────────┘ └────────┬─────────┘
    └──────┬───────┘         │                   │
           │                 └─────────┬─────────┘
           │                           ▼
           │                  ┌────────────────────┐
           └─────────────────►│ ExecutiveDecision- │
                              │ Brief (role-based) │
                              └────────┬───────────┘
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │  HUMAN REVIEW GATE      │
                          │  human_review_required  │
                          │  = True on ALL outputs  │
                          └────────────────────────┘
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/quality-twin/state` | Current twin state snapshot |
| GET | `/api/quality-twin/forecasts` | 30/60/90-day risk forecasts |
| POST | `/api/quality-twin/simulate` | Run what-if scenario simulation |
| GET | `/api/quality-twin/interventions` | List intervention models |
| POST | `/api/quality-twin/interventions` | Create intervention model |
| GET | `/api/quality-twin/executive-brief` | Role-based executive brief |
| POST | `/api/quality-twin/synthesize` | Trigger full twin synthesis |
| GET | `/api/quality-twin/dashboard` | Consolidated KPI dashboard |
| GET | `/api/quality-twin/scenarios` | List saved scenarios |
| PATCH | `/api/quality-twin/scenarios/{id}/approve` | Human-approve a scenario |

---

## Disclaimer

All Digital Quality Twin outputs are modelled projections for planning and decision support
only. All findings represent potential associations — they do not establish causation or predict
specific outcomes. Human review and approval are required before any operational decisions.
