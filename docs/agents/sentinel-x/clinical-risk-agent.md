# Project Sentinel-X — Clinical Risk Agent

LumenAI AI Specialist, Mission & Section 1.

## Naming disambiguation

**"Sentinel" already exists** as a major, unrelated system in this codebase
-- "Project Sentinel" v3.0 ("Autonomous Clinical Intelligence
Orchestration"): `app/models/sentinel_orchestration.py`
(`SentinelRiskSignal`, `ClinicalWatchlistEntry`, `DigitalTwinFlag`,
`SentinelAlert`, `SentinelRecommendation`, `SentinelHealthSnapshot`), routes
at `/api/sentinel`, frontend route `/sentinel`, and nine `sentinel_*.py`
services. Project Sentinel-X is a different, newer sprint and deliberately
uses a distinct `sentinelx_` file/model/route prefix (`/api/sentinelx`)
everywhere. It never touches or duplicates that system's tables. The
brief's own frontend route (`/risk`) does not collide with `/sentinel`.

## What Sentinel-X does

Continuously evaluates clinical, operational, and inspection risk before an
instrument proceeds through the pre-sterilization workflow — the patient-
safety intelligence layer of LumenAI. It does not replace human clinical
judgment. It prioritizes risk and explains why.

## Architecture

```
Inspection -> Vision AI -> Anatomy AI -> Knowledge Graph -> Digital Twin ->
Evidence Validation (Veritas) -> Process Intelligence (Aegis) ->
Instrument Reliability (Vulcan) -> Education Intelligence (Sage) ->
Clinical Risk Assessment -> Supervisor Review
```

## Deterministic, not an autonomous LLM

`sentinelx_risk_agent_service.run_risk_assessment` is a deterministic
Python orchestrator. There is no LLM/embedding API call anywhere.

## What is composed vs. genuinely new

Sentinel-X does not re-derive any specialist's own analysis. It calls:

- `vulcan_reliability_agent_service.run_reliability_assessment` — instrument
  reliability, progression, recurrence count, anatomy zone.
- `vulcan_aegis_integration_service.compute_process_variation_signal` —
  process variation.
- `veritas_evidence_agent_service.run_evidence_assessment` — evidence
  readiness (when an `inspection_id` is available).
- `instrument_condition_service.instrument_condition_history` — the real
  per-instrument Digital Twin condition trend (improving/stable/
  declining/insufficient_data). Note: `digital_twin_engine.py` tracks SPD
  workflow/throughput twins, a different concept — Sentinel-X does not read
  from there.
- `knowledge_graph_service.learning_confidence` — knowledge/clinical
  recommendation confidence, derived live from `SupervisorReview`.
- `InspectionFinding` (via `vulcan_progression_service.findings_timeline`) —
  the real per-finding log.

Genuinely new: three tables (`SentinelXRiskAssessment`,
`SentinelXPatientSafetyAlert`, `SentinelXSupervisorOverride`) and ten
service modules.

## Responsibilities (Section 1)

Evaluate contamination severity, anatomy-zone risk, recurrence, Digital
Twin condition, inspection confidence, evidence readiness, process
variation, repair history, and workflow status — then generate an
explainable risk assessment.

## API

```
POST /api/sentinelx/assess
GET  /api/sentinelx/assessments/{id}
```
