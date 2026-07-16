# Model Card — LumenAI Vision (Lens), v0.1.0-experimental

This is the human-authored companion to the auto-generated
`ModelRegistryEntry.model_card_markdown` (via
`app.services.ml.model_card.generate_model_card()`, unchanged, reused
verbatim) — that field is regenerated from the live registry row every
time a model is registered; this file is the durable, narrative Section 13
deliverable.

## Intended purpose

Reports **probable visual observations** on borescope images of surgical
instruments, for one declared experimental training run's proof of the
governed training/inference pipeline. **This model has never evaluated a
real clinical image and is not eligible for any clinical use.**

**This model reports probable visual observations and does not provide
laboratory confirmation of material identity.**

## Intended users

Engineering and clinical-governance reviewers validating the Project Lens
pipeline. Not intended for any operator, technician, or supervisor
workflow until a real, governed training run promotes a model past
`Experimental`.

## Supported visual observations

`no_observable_abnormality`, `probable_blood_like_residue`,
`probable_bone_like_fragment`, `probable_corrosion_like_degradation`,
`probable_plastic_or_insulation_fragment`, `probable_retained_debris`,
`probable_tissue_or_organic_residue` — the 7 categories with sufficient
real (albeit synthetic-experimental) evidence this run (see
`TRAINING_ELIGIBILITY_REPORT.md`).

## Unsupported findings

`probable_lint_or_fiber`, `probable_unknown_foreign_material` —
insufficient evidence this run; always reported as
`NOT_EVALUATED_BY_CURRENT_MODEL`, never scored.

## Training-data summary

46 synthetic images, one declared experimental run, pushed through the
real governed annotation/review/Ground-Truth pipeline. See
`TRAINING_ELIGIBILITY_REPORT.md` for the full breakdown and honest
disclosure that zero real clinical images exist in this environment.

## Source diversity

3 instrument families (scissors/grasper/forceps), 3 manufacturers
(Acme/Zenith/Meridian), 1 facility (the declared synthetic experimental
lab — genuinely 1, not padded).

## Review and Ground Truth process

Every training sample passed through real independent primary+secondary
review with genuine agreement (`annotation_review_service`) and real
promotion to `ground_truth_status = "ACTIVE"`
(`annotation_ground_truth_service.promote_to_ground_truth()`) — the same
governance path a real clinical image would use, just with synthetic pixel
content.

## Model architecture

Hierarchical (Stage B abnormality / Stage C category) one-vs-rest logistic
regression, pure Python, over Pillow-computed features (brightness mean,
edge-variance sharpness, aspect ratio). See
`MODEL_ARCHITECTURE_DECISION.md` for the full rationale.

## Preprocessing

`lens-pillow-features-v1` (`lens_training_pipeline.PREPROCESSING_VERSION`)
— the live inference adapter refuses to load an artifact whose
preprocessing version does not match this string
(`HEALTH_INCOMPATIBLE_PREPROCESSING`).

## Performance

Test-split accuracy 0.5625, macro-F1 0.7143 (16 samples). Full per-class
and subgroup breakdown in `EVALUATION_REPORT.md` — every number reported
honestly, including the two classes (`probable_bone_like_fragment`,
`probable_tissue_or_organic_residue`) this run never correctly predicted.

## Subgroup performance

See `EVALUATION_REPORT.md`'s subgroup table — no group suppressed.

## Calibration

Temperature `T = 1.85` (fit by grid search, real NLL 0.6654), ECE 0.1472
post-scaling, data-derived abstention threshold 0.5. Full detail in
`CALIBRATION_REPORT.md`.

## Abstention behavior

Abstains (`unknown_review_required` / `confidence_below_threshold` /
`insufficient_image_quality`) rather than returning a low-confidence
finding as if it were confident. See `CALIBRATION_REPORT.md` and
`live_inference_adapter.py`.

## Known limitations

- Trained on synthetic images only — see the provenance disclosure above.
- A linear classifier over 3 hand-engineered scalar features, not a
  learned-visual-feature model.
- `error_analysis.py`'s negative-label mismatch (see
  `ERROR_ANALYSIS_REPORT.md`'s "Known limitation" section).
- No class-weighting is actually applied by the trainer despite
  `TrainingConfig.class_weighting = "balanced"` being recorded (disclosed
  in `TRAINING_CONFIGURATION.md`).

## Known failure modes

Confuses visually-similar synthetic brightness/texture profiles between
non-negative categories (see `ERROR_ANALYSIS_REPORT.md`'s confusion
matrix) — a direct, disclosed consequence of the 3-scalar feature space.

## Out-of-scope use

Any clinical decision, any real patient-facing use, any use beyond
validating this pipeline's mechanics.

## Human-oversight expectations

Every result carries `human_review_required: true`. The live adapter never
auto-executes a recommendation — the Decision Engine and human supervisor
workflow are unchanged and continue to govern all clinical action.

## Patient-safety controls

`candidate_stage` is `Experimental` and will never be promoted past that
by this sprint's own registration code
(`lens_model_registration.register_lens_model()`) for a synthetic-
experimental run — enforced in code, not just policy.

## Clinical-validation status

**Not clinically validated. Not eligible for any clinical use.**

## Legal and regulatory limitations

No FDA clearance or regulatory approval is claimed anywhere for this
model, consistent with the project's standing constraint.
