# Training Eligibility Report — Project Lens

Source: `app.services.ml.training_eligibility_service.compute_training_eligibility()`.

## Real production state today

This environment's real, non-test database (`backend/dev.db`) contained
**zero real-facility ACTIVE Ground Truth annotations** at the start of this
sprint (the one pre-existing Annotation row is itself test/demo residue,
not a real clinical image) — consistent with `docs/general-availability/
KNOWN_LIMITATIONS.md`'s standing disclosure that no real facility pilot has
ever run. `compute_training_eligibility()` therefore reports honestly:
`total_active_ground_truth_annotations: 0` when run against a genuinely
empty tenant.

## The one declared experimental run

Per `FIRST_MODEL_SCOPE.md`, this sprint's real numbers below come from
`app.services.ml.experimental_dataset_generator.generate_experimental_dataset()`
— synthetic, class-correlated images pushed through the REAL governed
pipeline (real ingestion, real independent primary+secondary review with
genuine agreement, real Ground Truth promotion via
`annotation_ground_truth_service.promote_to_ground_truth()`). Every entry
is tagged `facility = "LumenAI Synthetic Experimental Lab (Project Lens
declared experimental run)"`.

```
total_active_ground_truth_annotations: 46
total_eligible_samples: 46
excluded_counts: {}                 # nothing excluded — all 46 passed every structural gate
label_counts:
  probable_blood_like_residue:              7
  probable_tissue_or_organic_residue:       7
  probable_retained_debris:                 8
  probable_corrosion_like_degradation:      5
  probable_bone_like_fragment:              6
  probable_plastic_or_insulation_fragment:  6
  no_observable_abnormality:                7
eligible_classes (>= 3 samples, MIN_SAMPLES_PER_CLASS):
  probable_blood_like_residue, probable_bone_like_fragment,
  probable_tissue_or_organic_residue, probable_retained_debris,
  probable_corrosion_like_degradation, probable_plastic_or_insulation_fragment,
  no_observable_abnormality
excluded_classes (insufficient evidence -> NOT_EVALUATED_BY_CURRENT_MODEL):
  probable_lint_or_fiber, probable_unknown_foreign_material
data_provenance: synthetic_experimental
```

## Eligibility gates applied (all real, all enforced)

1. `Annotation.ground_truth_status == "ACTIVE"` — structurally requires
   primary+secondary review agreement or completed clinical adjudication
   (`annotation_ground_truth_service.is_eligible_for_ground_truth()`).
   This alone rules out AI-only predictions, unreviewed images, and
   unresolved disagreements — there is no separate flag to check for
   these; they cannot reach `ACTIVE` status at all.
2. The linked `DatasetRegistryEntry` (joined via the shared
   `retained_image_id`, mirroring the Project Canvas Dataset Release
   Builder's bridge pattern) must not be `ARCHIVED`.
3. `usage_rights` must be non-blank (rights-restricted images excluded).
4. `image_quality` must not be `Reject`.
5. `phi_verification` must be `"verified"`.
6. Duplicate `image_sha256` values are deduplicated (first occurrence
   wins, rest excluded as `"duplicate"`).
7. Real `RetainedImage.image_bytes` must exist (excluded as
   `"no_retained_image_bytes"` otherwise — a genuine data-availability
   gate, not assumed).
8. The annotation's `primary_observation` must resolve (via
   `observation_taxonomy.canonical_observation_category()`) to a real
   taxonomy category, and not be a Stage-A/B routing outcome
   (`insufficient_image_quality`) — excluded as
   `"unrecognized_or_non_trainable_category"` otherwise.

## What is never trained from

- AI-only predictions (structurally impossible to reach `ACTIVE` without
  human review, per gate 1).
- Test fixtures (this report only reads real `Annotation`/
  `DatasetRegistryEntry`/`RetainedImage` rows for the given tenant).
- Seeded demonstration data (`backend/scripts/seed_pilot_data.py`'s output
  is never routed through `Annotation.ground_truth_status`).
- Unresolved reviewer disagreements, rejected-quality images,
  rights-restricted images, or PHI-unverified images (gates 2-5 above).
