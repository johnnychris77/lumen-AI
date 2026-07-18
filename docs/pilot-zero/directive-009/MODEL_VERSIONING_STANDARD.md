# LPZ-DIR-009 — Model Versioning Standard

**Purpose:** define how candidate models are versioned so every model is
reproducible, comparable, and rollback-safe. **No model version is overwritten;**
historical versions remain retrievable.

## Required version fields

| Field | Meaning | System mapping |
|---|---|---|
| **Major Version** | Substantive change (architecture, dataset, task) | `model_version` (major.minor.patch) |
| **Minor Version** | Non-substantive improvement (retrain, tuning) | `model_version` |
| **Patch Version** | Fix (packaging, metadata, card) | `model_version` |
| **Parent Model** | The version this derives from | parent linkage |
| **Training Dataset Version** | Frozen dataset trained on | `dataset_version_id` |
| **Ground Truth Version** | GT version underlying the data | dataset lineage |
| **Evaluation Version** | The evaluation protocol/run applied | evaluation link |
| **Approval History** | Approvals across versions | approval records |
| **Retirement Status** | Active / retired | `candidate_stage` / status |
| **Rollback Reference** | The version to roll back to | rollback pointer (`MODEL_ROLLBACK_STANDARD.md`) |

## Semantics

* **Major** — changed architecture, changed training dataset version, changed task
  definition, or any change that alters what the model does. Requires full
  re-validation and re-approval.
* **Minor** — retrain on the same dataset version with tuning, or a methodology
  refinement that does not change the task. Requires re-evaluation.
* **Patch** — packaging, metadata, or model-card corrections with no change to
  weights/behavior. Attributable; no re-training.

## Rules

1. **Immutable versions.** A released version is frozen (artifact + checksum);
   changes create a new version.
2. **Append-only history.** Prior versions are retained and retrievable; nothing is
   overwritten or deleted.
3. **Parent linkage.** Each version (after the first) references its parent,
   forming an unbroken lineage.
4. **Pinned data lineage.** Each version pins its training dataset version and
   Ground Truth version, so it is interpretable against exact evidence.
5. **Evaluation pinned.** Each version records the evaluation protocol/run applied
   to it (`MODEL_EVALUATION_STANDARD.md`).
6. **Rollback ready.** Each version records a rollback reference to a known-good
   prior version (`MODEL_ROLLBACK_STANDARD.md`).
7. **Reason required.** Every new version records why it was created.

## Lineage example

```
MODEL vision-quality
  v1.0.0  dataset=DS7v2  GT=…  eval=E12  approver=A  reason="initial candidate"
  v1.1.0  dataset=DS7v2  GT=…  eval=E15  approver=B  reason="retrain + tuning"   parent=v1.0.0
  v2.0.0  dataset=DS9v1  GT=…  eval=E20  approver=B  reason="new dataset version" parent=v1.1.0
          (v1.x retained, retrievable — rollback_reference=v1.1.0)
```

## Governance note (existing system)

`ModelRegistryEntry.model_version` versions models today, with `dataset_version_id`
and `artifact_checksum` supporting reproducibility, and the candidate-stage ladder
tracking status. Governance additions recorded for a future authorized change:
formalize major/minor/patch semantics, add explicit **parent** and **rollback
reference** pointers and an **evaluation version** link, and require a version
reason. No code is changed under this directive.
