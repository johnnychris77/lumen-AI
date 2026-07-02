# Shadow-Mode Validation (Phase 17)

Measure a model's real performance **before** it can influence care. Source:
`app.services.ml.shadow_mode`, `app.models.shadow_prediction`. API:
`/api/model-pipeline/shadow-predictions`.

## Behavior

- The model runs **silently** on an inspection; its prediction is **stored**.
- Users **never see** the shadow prediction as a clinical recommendation — the
  API response exposes only that a shadow ran (`clinical_recommendation_shown:
  false`) and omits the predicted label.
- When the human final decision is recorded, the shadow prediction is
  **reconciled** against it (`agreed_with_human`).
- Aggregated agreement (`/shadow-predictions/performance`) is computed **only**
  over reconciled rows — real evidence, never projected.

## Invariant

A `ShadowPrediction` row always has `shadow_mode = true`. The public view is the
contract that keeps a shadow model from affecting a recommendation. Only
`experimental`, `pilot`, and `validated` models may run shadow; a `deprecated`
model is refused (409).

## Promotion gate

`shadow_mode_completed` is a required checklist item for **validated** promotion:
a model must have demonstrated agreement in shadow before it can support a
workflow decision.
