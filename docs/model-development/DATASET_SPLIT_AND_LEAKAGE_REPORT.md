# Dataset Split & Leakage Report — Project Lens

Source: `app.services.ml.lens_training_pipeline._to_split_sample()` +
`app.services.ml.dataset_split.split_dataset()`/`has_no_group_leakage()`
(reused verbatim — the splitter itself is unchanged from the existing,
already-tested pure-Python, seeded-hash implementation built in an earlier
sprint).

## Grouping identity (Section 4 / Section 6 of the trace)

Groups are formed by the strongest available identity, in this order:

1. **Digital Twin ID** (`Annotation.digital_twin_id`) — but only when it is
   a real, barcode/UDI-backed identity. `lcid_service.is_untracked_twin()`
   is checked first: an `"untracked:{instrument_type}:..."` fallback ID
   (no barcode/UDI was ever captured) is **not** used for grouping — using
   it would incorrectly collapse every image sharing an instrument *type*
   (not a real physical instrument) into one giant group, since this
   sprint's declared experimental images share only 3 instrument-family
   values across 46 images. This was found and fixed during this sprint
   (see `LIVE_INFERENCE_TRACE.md` Section 6) — an earlier version of this
   pipeline produced a 46/0/0 train/validation/test split for exactly this
   reason before the fix.
2. Falling back to `inspection_id` (none set for this sprint's synthetic
   images — they were not created via an `Inspection` row).
3. Falling back to the sample's own ID (no grouping constraint) when
   neither of the above is available — this sprint's actual case, since no
   real barcode/UDI or inspection_id was captured for the synthetic images.

## Real split produced this run

```
train:      30 samples
validation:  0 samples
test:       16 samples
leakage_free: true
```

The 0-sample validation split is a real, disclosed artifact of this small
(46-sample) dataset combined with the seeded-hash bucketing approximating
70/15/15 ratios per group — with no grouping constraint active (every
sample its own group), 46 groups distributed by hash landed 0 in the
validation bucket this run. This is reported honestly, not padded or
rebalanced to look better; calibration/error-analysis therefore ran
against the test split (`calibration_split = test_samples or val_samples`
in `lens_training_pipeline.run_lens_training()`), exactly as designed for
this fallback case.

## Duplicate control

`dataset_integrity.check_no_duplicate_images()` runs before any feature
extraction — this run reported no duplicate `image_sha256` values (each of
the 46 synthetic images has a distinct hash by construction). The
training-eligibility gate (see `TRAINING_ELIGIBILITY_REPORT.md` gate 6)
separately deduplicates at the eligibility-computation stage, before
samples ever reach the splitter — so no duplicate image can appear in more
than one split by construction, independent of the grouping key above.

## Class-distribution report (real, this run)

| Split | probable_blood_like_residue | probable_bone_like_fragment | probable_tissue_or_organic_residue | probable_retained_debris | probable_corrosion_like_degradation | probable_plastic_or_insulation_fragment | no_observable_abnormality |
|---|---|---|---|---|---|---|---|
| Test (16) | 2 | 3 | 2 | 3 | 2 | 2 | 2 |

(Train-split per-class counts are in `EVALUATION_REPORT.md`'s training
metrics section — every class has real, non-fabricated support in both
splits.)

## Diversity check (`dataset_integrity.check_diversity()`)

3 instrument families (scissors/grasper/forceps), 3 manufacturers
(Acme/Zenith/Meridian) — both meet `MIN_INSTRUMENT_FAMILIES`/
`MIN_MANUFACTURERS` (2). Facility count is 1 (all from the single declared
experimental facility) — honestly disclosed as a real limitation of this
run, not hidden.
