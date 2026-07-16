# LCID Label Guide

## Canonical taxonomy

The dataset's label vocabulary is the same Observation Doctrine taxonomy
already built for the Lumen Decision Engine
(`backend/app/services/observation_taxonomy.py`,
`docs/clinical/LUMENAI_OBSERVATION_DOCTRINE.md`) — this dataset does not run
a second, competing label set:

`probable_blood_like_residue`, `probable_tissue_or_organic_residue`,
`probable_bone_like_fragment`, `probable_retained_debris`,
`probable_corrosion_like_degradation`, `probable_lint_or_fiber`,
`probable_plastic_or_insulation_fragment`,
`probable_unknown_foreign_material`, `no_observable_abnormality`,
`insufficient_image_quality`.

## Naming note

This sprint's own brief used two slightly different spellings —
`probable_bone_fragment` and `probable_plastic_fragment` — for two of the
above categories. Rather than run a second taxonomy,
`observation_taxonomy.LCID_SPEC_ALIASES` maps those spellings onto the
canonical names above; `canonical_observation_category()` resolves either
spelling. Annotation tools should accept both but always persist the
canonical name.

## Secondary appearance attributes

Visual-description-only, never a laboratory conclusion (Section 1 of the
Observation Doctrine): red, dark red, red-brown, dark brown,
dried-appearing, crusted, smeared, particulate, fibrous, adherent.

## Validity enforcement

`app.services.ml.dataset_validation_service.validate_registry()` flags any
`current_label` outside this taxonomy (plus the empty/`unlabeled`
placeholders) as an `invalid_labels` finding — see `docs/lcid/DATASET_SPECIFICATION.md`.
