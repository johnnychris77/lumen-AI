# AI Health Monitor & Enterprise Risk Score

LumenAI v3.0 · Project Sentinel

## AI Health — reused math, one new real drift detector

`sentinel_ai_health_service.compute_ai_health` reads real `SupervisorReview`
rows through `ml/pilot_validation.py`'s existing, real confusion-matrix
functions (`clinical_metrics`, `confidence_calibration`) rather than a
fourth reimplementation — the same functions the pilot validation report
uses. It also reads `Inspection.coverage_quality`/`baseline_status` for
coverage/baseline quality percentages, and `knowledge_graph_service.
learning_confidence` for Knowledge Graph confidence.

**Model drift is genuinely new** — and deliberately real, unlike
`RWEMetricSnapshot.psi_score` (`app/models/validation.py`), which is still
seeded-random pending real population. `_detect_drift` compares average AI
confidence and supervisor agreement rate between the trailing 30-day
window and the 30 days before that; a shift of 10 percentage points or
more in either flags `drift_detected: true` with the specific shift named
in `drift_detail`. With fewer than 10 reviews in either window, it reports
"insufficient reviews to assess drift" rather than fabricating a result.

## Enterprise Risk Score

`sentinel_dashboard_service._compute_enterprise_risk_score` is a 0-100
composite where **higher means more risk** — the opposite convention from
the existing `quality_dashboard_service.executive_quality_score` (where
higher means better quality). This is deliberate, not an accident, and
documented so the two scores are never confused:

| Factor | Weight | Source |
|---|---:|---|
| Quality risk (`100 - executive_quality_score`) | 50% | Composes the existing real quality score |
| Watchlist pressure | 20% | Active watchlist entry count |
| Alert pressure | 20% | Open high/critical Enterprise Alert count |
| Drift risk | 10% | 100 if model drift detected, else 0 |

Like `executive_quality_score`, any factor with no underlying data is
excluded and the remaining weights re-normalized — never defaulted to a
fabricated value. It is **not** a re-derivation of `QualityTwinState.
overall_quality_score` (`digital_quality_twin_service.py`) — that score is
currently a seeded-mock placeholder pending real multi-source wiring; this
one reads only real data.

Every computation persists a `SentinelHealthSnapshot` row, so both the
risk score and Knowledge Graph confidence/sample size trend over time
(`GET /api/sentinel/dashboard`'s `knowledge_growth` series) without
re-deriving history on each read.

## Endpoint

- `GET /api/sentinel/ai-health` — leadership roles only
