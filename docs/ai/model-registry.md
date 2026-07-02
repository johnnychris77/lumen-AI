# Model Registry (Phase 17)

Source of truth for every trained model version and the gate that governs it.
Table: `app.models.model_registry.ModelRegistryEntry`. API: `/api/model-pipeline/models`.

## Fields

| Field | Meaning |
|---|---|
| `model_id` | Stable identifier for a model line |
| `model_version` | Version string within that line |
| `model_type` | Task key (`finding`, `anatomy_zone`, …) |
| `dataset_version` | Deterministic fingerprint of the training data |
| `training_date` | When training completed (empty until real training) |
| `training_status` | `not_started` \| `training` \| `trained` \| `failed` |
| `evaluation_metrics` | JSON metrics (empty `{}` until a real evaluation) |
| `known_limitations` | Free-text limitations (required before promotion) |
| `approval_status` | `experimental` \| `pilot` \| `validated` \| `deprecated` |
| `approved_by` | The human who promoted it |
| `release_notes` | Change notes |

## Rules

- A model is **always created as `experimental`** — the API hard-defaults it and
  never trusts a client-supplied status.
- Every model view carries its stage `capabilities` and `human_review_required: true`.
- Promotion is a separate, human-gated action (`/promote`) — see
  `model-deployment-gates.md`.
- Registration and promotion are audit-logged.

## Tenancy

Registry rows are tenant-scoped; a tenant only sees and promotes its own models.
