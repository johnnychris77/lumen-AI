# Stage 5B — Scientific Anomaly Localization (research-only)

Status: **research-only**. No clinical model trained or served, no clinical
decisioning changed, no model promoted, no rust/blood/pitting classification, no
clinical-accuracy claim. Extends Stage 5A (PR #163); reuses — does not duplicate —
Project Canvas, Project Lens, governance, dataset registries, and clinical
decisioning.

## What this delivers

A governed, research-only anomaly-**localization** capability that identifies
*where* suspicious visual features occur, without assigning a diagnosis.

### Localizers (`research/lens_vision/anomaly_localization.py`)
One interface (`fit(normal_images)` → `score(image) → (heatmap, image_score)`),
three providers:
- **`StubLocalizer`** — deterministic, Pillow-only, per-pixel diagonal-Gaussian
  model fit on verified-normal images. Produces a **genuine pixel-level anomaly
  map at the input resolution** (spatial alignment preserved). Explicitly **not**
  Anomalib PaDiM — an engineering smoke device, not science.
- **`PadimLocalizer` / `PatchCoreLocalizer`** — the real Anomalib backends
  (Apache-2.0). Construction requires torch **and** an explicitly approved,
  rights-cleared, **SHA-256-verified** backbone checkpoint (`resnet18_imagenet`),
  and refuses otherwise. **No weight is ever auto-downloaded.** PatchCore uses the
  same governed interface with a controlled coreset sampling ratio.

### Research-only spatial output contract (`anomaly_contract.py`)
`AnomalyResult` records: source image + provenance, model architecture +
checkpoint + digest, research run + version, image-level score, heatmap reference
+ shape, proposed region coordinates, `calibration_status="uncalibrated"`,
`uncertainty_status="unknown"` (never fabricated 0), grouping/validation
limitations, and the constants `research_only=True`,
`clinical_promotion_eligible=False`, `confirmed_diagnosis=None`,
`human_review_required=True`. `AnomalyRegion.to_clinical_label()` raises.

### Governed experiment + evaluation (`anomaly_experiment.py`)
Predefined protocol: provenance gate → **verified-normal-only fit** (any
non-`verified_normal` image raises `NormalOnlyViolation`) → **leakage check**
(train/held-out may not share instrument/specimen/session/image identity →
`LeakageError`) → score → region proposals → metrics **only where valid labels/
masks exist**:
- image-level **AUROC / average precision** when held-out carries both classes;
- pixel-level **Dice / IoU** only when valid reference masks exist;
- per-image **latency**; missing-data is reported, never fabricated.
`compare_localizers` runs PaDiM vs PatchCore on identical authorized data and
records a **blocked** status + reason for any model that can't be constructed —
never fabricated performance.

### Governance reused (Stage 4 + Stage 5A)
Tenant ownership, provenance class + approval, specific research/training usage
rights, consent + PHI, source + checkpoint licensing, active retention, image
integrity, ground-truth eligibility, and grouped-leakage prevention all come from
the Stage 5A governed loader (`data_loader` / `governance`) and the production
splitter. Real clinical data stays out of this track unless separately authorized.
No external dataset (MVTec/WPI/DefectAtlas/…) is downloaded or used.

## Executed results (this environment: no torch/Anomalib)

Real PaDiM/PatchCore are **blocked** here (no torch/Anomalib; `resnet18_imagenet`
unapproved). The deterministic **stub** path runs end-to-end on synthetic
fixtures — a **technical test, not model performance**:

- `pytest tests/test_stage5b_anomaly_localization.py` → **15 passed, 1 skipped**
  (the skip is the torch/anomalib-gated path).
- Full backend suite → **3938 passed, 4 skipped**; Ruff (`app tests research`) → clean.
- Synthetic technical-test experiment (stub, 10 normal / 9 held-out):
  image-level AUROC **1.0**, AP **1.0** (flagged synthetic); pixel-level mean Dice
  **0.667**, IoU **0.667** (9 masked images); per-image latency **~3.5 ms** (CPU).
  Normal images score ~1.6–7.4 vs anomalous ~4284 — clean separation by construction.
- `compare_localizers` → PaDiM and PatchCore both **blocked**
  (`CheckpointNotApprovedError: 'resnet18_imagenet' not approved`).

Example research-only output (anomalous synthetic image): a 64×64 heatmap, an
image-level score, a bounding-box region, `calibration_status="uncalibrated"`,
`uncertainty_status="unknown"`, `confirmed_diagnosis=None`,
`clinical_promotion_eligible=False`, `human_review_required=True`.

## Licensing & dataset-rights assessment
- **ResNet-18 backbone:** torchvision/BSD-3 weights, ImageNet terms to verify;
  registered **BLOCKED** pending approval + recorded digest.
- **Anomalib:** Apache-2.0; isolated optional dep (`requirements-research.txt`),
  never installed by CI/production; **verify the installed API version** (0.x vs
  1.x differ) before use.
- **Datasets:** none downloaded. Synthetic fixtures only; real/external data
  require verified rights and governed ingestion.

## Blockers (why the real benchmark did not run)
1. PyTorch + Anomalib not installed in this environment (production isolation).
2. No approved, rights-cleared, hash-verified `resnet18_imagenet` checkpoint.
3. No governed set of verified-normal instrument images (or permitted external
   stainless-steel data) cleared for research use.
No fabricated model performance is reported for the blocked paths.

## Resource / latency
Stub CPU localization ~3.5 ms/image (64×64). Real PaDiM/PatchCore memory and
latency are measured once the isolated environment + approved backbone exist
(PaDiM: low memory; PatchCore: memory-bank size × coreset ratio).

## Stage 5C readiness & scientific-labeling requirements
To proceed to Stage 5C (calibration + scientific labeling):
1. Provision an isolated torch+Anomalib research environment; pin and record the
   Anomalib API version.
2. Approve + rights-clear the `resnet18_imagenet` backbone and record its SHA-256.
3. Assemble a **governed, independently-verified verified-normal** image set
   (and a held-out set with **validated spatial masks** for pixel metrics).
4. Predefine the evaluation protocol and thresholds before viewing held-out results.
5. Calibrate anomaly scores (scores remain **uncalibrated** until then); add
   per-subgroup reporting (instrument family, lighting, anatomy zone) where
   sample sizes permit, with confidence intervals and uncertainty limits.
6. Keep outputs research-only: no mapping of anomaly regions to clinical classes,
   no entry into technician recommendations, the Lumen Decision Engine,
   deployment, or OEM intelligence, until a separate, governed Stage 5C review.
