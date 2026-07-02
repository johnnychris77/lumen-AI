# Model Training Pipeline (Phase 17)

Repeatable path from validated inspection data to a *safely* deployed,
anatomy-aware model. Training itself is not executed yet — there is no labeled
dataset — so the pipeline prepares and validates everything around training and
records an honest `not_started` registry entry. No metrics are fabricated.

## Lifecycle

```
Data → Labels → Training → Evaluation → Registry → Shadow Mode → Pilot → Validation → Deployment
```

## Stages (code)

| Step | Module |
|---|---|
| Image + label ingestion | `app.models.retained_image` (opt-in, EXIF-stripped) |
| Dataset split (70/15/15) | `app.services.ml.dataset_split` |
| Model task definitions | `app.services.ml.model_tasks` |
| Feature store | `app.services.ml.feature_store` |
| Training-run preparation | `app.services.ml.training_pipeline` |
| Evaluation metrics | `app.services.ml.evaluation` |
| Model registry | `app.models.model_registry` |
| Deployment gates | `app.services.ml.deployment_gates` |
| Shadow mode | `app.services.ml.shadow_mode`, `app.models.shadow_prediction` |

## Model tasks

- **Instrument Family Classifier** — rigid scope, flexible endoscope, drill bit,
  Kerrison/rongeur, scissors, needle holder, laparoscopic, general forceps, unknown.
- **Anatomy Zone Classifier** — o-ring area, serration, groove, hinge, box lock,
  drill-bit flute, threaded region, lumen, scope port, cutting edge, insulation
  edge, handle seam, unknown.
- **Finding Classifier** — blood, bone, tissue, organic residue, debris, rust,
  corrosion, discoloration, crack, pitting, insulation damage, missing component,
  wear, none. *(safety-critical)*
- **Severity Classifier** — none, trace, minor, moderate, visible, severe, heavy.
  *(safety-critical)*
- **Clinical Disposition Classifier** — pass, monitor, supervisor_review,
  reprocess, remove_from_service. *(safety-critical)*

## Dataset split

70% train / 15% validation / 15% test, deterministic (seeded), stratified by
instrument family, anatomy zone, finding, severity, manufacturer, and image
quality. Leakage prevention groups all images from one inspection (and its
baseline/inspection pair) into a single split; `group_by_serial` additionally
keeps one instrument's whole history out of validation/test. See
`inspection-coverage-rules.md` sibling doc `model-registry.md` for downstream.

## Training data requirements

Real training needs: labeled zones + findings + severities per image, sufficient
per-class support (esp. the safety-critical findings), manufacturer/model
diversity, and supervisor-validated ground truth (the `SupervisorReview`
zone/family/finding corrections are the seed label set).

## Honesty

- No fabricated model, artifact, or metric until a real model is trained.
- CV features (color/texture/edge/blur/lighting/similarity) are stored as null
  until a vision model exists — see `feature_store.py`.
- `human_review_required: true` on every model view.
