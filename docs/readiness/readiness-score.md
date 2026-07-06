# Readiness Score, Timeline, Risk Stratification & Dashboard (v1.6)

## Readiness Score
0-100, the same score the baseline-comparison scoring engine already computes
(`100 - risk_score`) — surfaced through `readiness_engine.compute_readiness()`
rather than recalculated. `None` when the inspection hasn't been scored yet
(no approved baseline, or still pending).

## Readiness Timeline (Deliverable 4)
`app/services/readiness_timeline_service.py::build_timeline()` returns eight
steps: Image Uploaded → Instrument Identified → Coverage Completed → AI
Findings → Clinical Reasoning → Supervisor Review → Disposition → Ready for
Packaging. Steps that happen synchronously within one `POST /api/inspections`
call share that submission's real timestamp rather than fabricating
individually-spaced fake times — only Supervisor Review has its own
independently-timed record. Exportable via `GET
/api/inspections/{id}/readiness-timeline` (JSON) and embedded in the PDF
readiness report.

## Instrument Risk Stratification (Deliverable 8)
`app/services/risk_stratification_service.py::stratify_risk()` is a
point-based rubric over already-computed signals (structural finding
severity, remove-from-service escalation, high-retention-zone involvement,
coverage completeness, baseline confidence) — not a separate model. Returns
`risk_tier` (Low/Moderate/High/Critical) alongside `reasons`, so the
classification is auditable rather than a black box.

## Readiness Dashboard (Deliverable 7)
`GET /api/clinical-readiness/dashboard` (route `/clinical-readiness`) rolls
up every inspection's readiness status and disposition: counts by status
(including Supervisor Pending), average readiness score, and disposition
trends — all derived live from `readiness_engine`/`disposition_engine`, no
separate aggregation logic.
