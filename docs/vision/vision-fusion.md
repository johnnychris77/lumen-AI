# Cross-Image Reasoning & Evidence Fusion

`app/services/vision_session_engine.py`.

## Cross-Image Reasoning (Objective 6)

Every predicted finding the scoring engine produces already carries an
`instrument_zone` (see `app/services/instrument_zones.py`'s `zone_fields()`,
threaded into `baseline_comparison_scoring_service.analyze_inspection()`).
`cross_image_reasoning()` correlates each finding's zone with whichever
captured image tag shares that `anatomy_zone`, then reasons across the
whole set:

- A finding present in **even one** image is real for the whole instrument
  — a clean neighboring image never cancels it out. Example: Image 1 (no
  blood) + Image 2 (blood) → "Instrument contains retained contamination
  identified across captured images," matching the sprint's own example.
- Contamination and structural findings are tracked separately, so the
  overall result can name both when they co-occur.

## Evidence Fusion (Objective 7)

`evidence_fusion()` combines:

| Factor | Source |
|---|---|
| Image evidence | `cross_image_reasoning()`'s overall result |
| Baseline comparison | The inspection's resolved `baseline_source` (manufacturer/vendor/hospital) |
| Anatomy / coverage | The Coverage Engine's `quality` band for this session's captured zones |
| Confidence | Average of each predicted finding's confidence (when available) |
| Supervisor history | Agreement rate across this inspection's `SupervisorReview` rows |

into one recommendation (`PASS` / `SUPERVISOR REVIEW` / `REPROCESS`) and a
narrative sentence — never a second, independent AI decision. `PASS` still
always carries `human_review_required: true`, matching the platform-wide
governance rule that no recommendation here is self-executing.

## What this deliberately does not do

Evidence Fusion does not re-run `analyze_inspection()` or invent new
per-image confidence values — confidence isn't persisted per finding today
(see `docs/vision/inspection-session.md`), so the average is computed only
over values that are actually available, and is `null` rather than
fabricated when none are. This is the same "no fabrication" convention the
rest of the platform's scoring/anatomy/knowledge services follow.
