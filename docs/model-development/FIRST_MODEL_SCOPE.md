# First Model Scope — Project Lens

## Hierarchical design

**Stage A — Image quality gate** (`sufficient_for_evaluation` /
`insufficient_image_quality`). Not a trained classifier: reuses the
already-real, pixel-computed `app.services.ml.image_quality.assess_image_bytes()`
(edge-variance blur estimate, mean-brightness exposure estimate, minimum
resolution/aspect-ratio checks). Its existing `Excellent/Good/Marginal/Poor/
Reject` grade maps directly: `Reject`/`Poor` → `insufficient_image_quality`;
`Excellent`/`Good`/`Marginal` → `sufficient_for_evaluation`. No new model is
trained for this stage — it is a deterministic, already-validated rule over
real pixels, which is the architecturally honest choice (a learned quality
classifier would need its own labeled "is this image evaluable" dataset,
which does not exist).

**Stage B — Abnormality detector** (`observable_abnormality` /
`no_observable_abnormality`). A binary one-vs-rest logistic-regression head
trained on the same feature vector as Stage C (Section "Architecture"
below), over images that pass Stage A.

**Stage C — Supported probable observation category.** A multiclass
one-vs-rest logistic-regression head, trained only on images Stage B
classified as `observable_abnormality`, over whichever categories from the
approved taxonomy (`app.services.observation_taxonomy.OBSERVATION_TAXONOMY`)
have sufficient governed evidence (see below). Every other taxonomy
category is reported as `NOT_EVALUATED_BY_CURRENT_MODEL` — never scored.

Abstention (Section 2's requirement) is a routing outcome layered on top of
all three stages, not a fourth ground-truth class:

- `insufficient_image_quality` — Stage A rejected the image.
- `confidence_below_threshold` — Stage B/C's calibrated confidence fell
  below the calibration-derived (or, when uncomputable, a disclosed
  default) threshold.
- `unknown_review_required` — reserved for the case where Stage C's top
  score is ambiguous across multiple categories, or the ground-truth
  category present in training data was itself
  `probable_unknown_foreign_material` (an unknown-finding routing outcome
  per the Lumen Decision Engine's own doctrine, not a material identity a
  vision model should be trained to assert with confidence).

## Preferred classes and the real evidence check

Per Section 2, before training we count real, eligible ACTIVE Ground Truth
images per category (full counts and methodology are in
`TRAINING_ELIGIBILITY_REPORT.md`, produced by
`app.services.ml.training_eligibility_service.compute_training_eligibility()`).
**No preferred class is force-included** — a category is only added to
Stage C's trained scope when its real eligible count meets
`MIN_SAMPLES_PER_CLASS` (3, the same threshold `candidate_training.py`
already uses elsewhere in this codebase, for consistency). Every excluded
category is reported as `NOT_EVALUATED_BY_CURRENT_MODEL` in the model's
registry entry, model card, and every result contract — never silently
dropped or fabricated as a zero probability.

## The honest data-provenance finding

This environment's real, production-facing database
(`backend/dev.db`) contains **zero real-facility ACTIVE Ground Truth
annotations** at the time of this sprint — the single Annotation row
present is itself a leftover of prior test/demo activity, not a real
clinical image. This is consistent with `docs/general-availability/
KNOWN_LIMITATIONS.md`'s existing, standing disclosure that "no real
facility pilot has ever been run." Per Section 3's explicit governance
rule ("Do not train from: ... seeded demonstration data" / "not ...
synthetic demo records **unless a separately declared experimental
run**"), this sprint proceeds as exactly that: **one declared,
clearly-labeled experimental run**, using synthetic-but-class-correlated
images pushed through the REAL governed pipeline (real ingestion, real
independent primary+secondary review, real Ground Truth promotion) — see
`app.services.ml.experimental_dataset_generator` and
`TRAINING_ELIGIBILITY_REPORT.md` for the full disclosure. Every entry
produced this way is tagged `facility = "LumenAI Synthetic Experimental
Lab (Project Lens declared experimental run)"` so it can never be confused
with, or silently counted toward, a real clinical dataset. The resulting
model is registered with `candidate_stage = "Experimental"` and
`approval_status = "experimental"` throughout — it is never marked
`"Candidate"`, since that stage (per this codebase's own
`candidate_promotion.py` ladder) is reserved for a model trained on real,
governed clinical evidence, which this run explicitly is not.

This means Project Lens's real, durable deliverable this sprint is **the
full pipeline itself** — eligibility computation, leakage-safe splitting,
hierarchical training, calibration, error analysis, artifact export,
registry, the live inference adapter, and the honest, safe unavailable
states — proven correct and reproducible end-to-end against the one
declared experimental dataset. The moment real governed ACTIVE Ground
Truth images exist (a real pilot per `docs/advisory-pilot/`), the same
pipeline runs unchanged against them and can then genuinely reach
`"Candidate"`.
