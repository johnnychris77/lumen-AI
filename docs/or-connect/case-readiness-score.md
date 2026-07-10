# Case Readiness Score

Codename: Project Symphony · LumenAI OR Connect v2.8

## Endpoint

`GET /api/or-connect/cases/{case_id}/readiness-score`

Computes and persists a `CaseReadinessScoreRecord` snapshot (0-100) each
time it's called, so trend reporting (`decision-comparison`-style, see
the Executive OR Coordination Dashboard) never has to re-derive history.

## Weighted factors

| Factor | Weight | Signal |
|---|---:|---|
| Instrument readiness | 25 | Fraction of linked inspections whose `readiness_engine.compute_readiness` status is Ready/Ready with Supervisor Approval |
| Vendor tray arrival | 15 | Fraction of vendor-supplied trays received or returned |
| Inspection completion | 15 | Fraction of linked inspections with `score_status` scored |
| Coverage completion | 10 | Average `Inspection.coverage_pct` across linked inspections |
| Baseline verification | 10 | Fraction of linked inspections with an approved baseline |
| Repair completion | 10 | Fraction of linked repair requests returned/replaced |
| Supervisor approvals | 10 | The case's explicit `supervisor_approved` flag, or fraction of linked inspections with a recorded `SupervisorReview` |
| Required specialty equipment | 5 | Fraction of hospital-owned trays received or returned |

A factor with nothing required yet (e.g. no vendor trays on a case that
doesn't need any) scores 1.0 — it isn't blocking, not "failing."

## Rationale

Every factor scoring below 100% is named explicitly in the response's
`rationale` field (e.g. *"vendor tray arrival is incomplete (50%, worth 15
pts)."*), so a reviewer sees exactly which real signal is dragging the
score down — never a black-box number.

## Governance

Every readiness score response carries `human_review_required: true` and
the OR Connect disclaimer: it is decision support for planning the case,
not an autonomous go/no-go determination.
