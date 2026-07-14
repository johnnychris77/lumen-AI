# Model Drift Monitoring

**Status:** New this pass (Shadow). **Code:**
`backend/app/services/ml/shadow_drift_monitor.py`, reusing
`backend/app/services/sentinel_ai_health_service.py::_detect_drift()`.

## Reused, not reimplemented

`sentinel_ai_health_service._detect_drift()` (Project Sentinel, v3.0)
already compares a trailing 30-day window of `SupervisorReview` rows
against the prior 30-day window — average AI confidence and supervisor
agreement rate — and flags drift when either shifts by more than 0.10, or
honestly reports "insufficient data" when either window has fewer than 10
reviews. Multiple other services already call this function directly
rather than re-deriving it (`pulse_alert_service`, `capa_suggestion_
service`, `oracle_model_observatory_service`). `shadow_drift_monitor.
assess_drift()` does the same — it is the **fourth** consumer of this
detector, not a fifth reimplementation.

## What Shadow adds

Everything `_detect_drift()` does not already report, computed over this
candidate model's own `ShadowPrediction` rows:

| Field | Meaning |
|---|---|
| `prediction_distribution` | Count of each predicted label |
| `instrument_mix` | Count of each instrument family seen |
| `facility_variation` | Count of predictions per facility |
| `image_quality_trend` | Count of each image-quality tier seen |

These are genuinely new — they are about *this* candidate model's own
shadow-prediction mix, which `_detect_drift()` has no reason to know
about (it operates on `SupervisorReview`, the deployed placeholder
engine's feedback store).

## Alerting

`drift_detected`/`drift_detail` are surfaced via
`GET /api/shadow-validation/drift` exactly as `_detect_drift()` returns
them — no threshold is re-tuned or duplicated for Shadow. The same
alerting surface `pulse_alert_service.ALERT_AI_CONFIDENCE_DROP` already
uses continues to be the single source of truth for "is this specific
kind of drift happening."

## Promotion gate

`candidate_promotion.evaluate_validated_candidate_checklist()`'s
`model_drift_acceptable` item is `not drift_detected` — a model with
active, unexplained drift cannot advance to Validated Candidate. See
`MODEL_PROMOTION_POLICY.md` (Genesis) for the full ladder and
`READINESS_CRITERIA.md` for how this fits alongside the other three new
gate items.
