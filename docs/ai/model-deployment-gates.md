# Model Deployment Gates (Phase 17)

What each approval stage may do, and what a human must satisfy to advance a
model. Source: `app.services.ml.deployment_gates`. Models are **never
auto-promoted**.

## Capabilities by stage

| Stage | Drive clinical rec? | Advisory? | Shadow? | Usable for new inspection? | Disclaimer |
|---|---|---|---|---|---|
| **experimental** | ✗ | ✗ | ✓ | ✗ | required |
| **pilot** | ✗ | ✓ | ✓ | ✓ | required |
| **validated** | ✓ (override allowed) | ✓ | ✓ | ✓ | required |
| **deprecated** | ✗ | ✗ | ✗ | ✗ | required |

- **Experimental** — shadow mode only; cannot drive or advise a recommendation.
- **Pilot** — advisory only, with a visible human-review disclaimer; cannot decide.
- **Validated** — may support a workflow decision; **supervisor override always
  allowed**.
- **Deprecated** — retired; cannot be used for new inspections or shadow runs.

## Human-in-the-loop promotion (§7)

To leave **experimental → pilot**, all of:
- `supervisor_validation`
- `minimum_sample_size` (≥ 200 validation samples)
- `false_negative_review`
- `edge_case_review`
- `limitations_documented`

To reach **validated**, additionally:
- `shadow_mode_completed`
- `safety_false_negative_within_threshold`

Rules enforced by `evaluate_promotion`:
- Advance **one stage at a time** (no skipping experimental→validated).
- Every requirement must be checked **and** an approver recorded, or the API
  returns **409** with the unmet list.
- Deprecation is always allowed (retiring a model is safe) but still records who
  did it.

## Why server-side

The gate lives in the backend so a model's stage — not a client flag — decides
whether it can influence a recommendation. A deprecated model is refused even for
shadow runs.
