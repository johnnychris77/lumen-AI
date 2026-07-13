# AI Model Observatory

## Composition, not re-derivation

`oracle_model_observatory_service.record_observation` calls
`sentinel_ai_health_service.compute_ai_health(db, tenant_id)` and stores its
return dict verbatim in `ai_health_snapshot_json`. Oracle never recomputes
drift detection, confidence calibration, or supervisor-agreement metrics --
it only observes and frames Sentinel-X's own already-computed judgment for
research purposes.

## Observation types

- `drift_detected` -- when `health["drift_detected"]` is true; `summary`
  quotes `health["drift_detail"]`.
- `coverage_gap` -- when `coverage_quality_pct < 50`, flagging that low
  review coverage may limit how reliable the snapshot is.
- `routine_snapshot` -- neither condition holds; a routine health check
  with nothing to flag.

## Review and promotion

`mark_reviewed` records a human reviewer against an observation
(`reviewed`, `reviewed_by`). `promote_to_hypothesis` creates an
`OracleHypothesis` in the `ai_model_performance_drift` category, copying
the observation's `summary` and full `ai_health_snapshot_json` into
`statistical_summary`. An observation can only be promoted once.
