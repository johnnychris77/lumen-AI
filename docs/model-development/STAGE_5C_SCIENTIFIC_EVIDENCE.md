# Stage 5C — Scientific Evidence & Real Model Integration (research-only)

Status: **research-only**. No clinical inference changed, no model promoted, no
research output deployed, no manufacturer intelligence enabled. Extends Stage 5B
(PR #164). Reuses — does not duplicate — Project Canvas, Project Lens, LCID, the
laboratory evidence protocol, model governance, the clinical taxonomy, and
human-review mechanisms.

> **Honesty clause.** Passing code tests does **not** make Stage 5C scientifically
> validated. Real PaDiM/PatchCore execution is a genuine implementation that is
> **BLOCKED** in this environment (no torch/Anomalib, no approved backbone). The
> measured numbers below are **synthetic technical-test** results, not model or
> clinical performance.

## 1. Real PaDiM / PatchCore (implemented; BLOCKED here)
`anomaly_localization.py` now contains the **genuine** Anomalib-backed
implementation (`_AnomalibLocalizer` → `PadimLocalizer` / `PatchCoreLocalizer`),
pinned to the **Anomalib 1.1.x** API:
- Construction is fail-closed: an approved, rights-cleared, **SHA-256-verified**
  backbone checkpoint (`resnet18_imagenet`) **and** torch + Anomalib are required.
- Backbone weights are loaded from the **verified local file**; Anomalib's own
  pretrained download is disabled (`pre_trained=False`) — **no auto-download**.
- `fit` trains PaDiM/PatchCore on the normal split only; `score` returns a
  pixel anomaly map interpolated to the input resolution.
These paths run only in an isolated research environment. Here, `resnet18_imagenet`
is unapproved → construction raises `CheckpointNotApprovedError` (reported BLOCKED,
never a stub masquerading as PaDiM). The deterministic `StubLocalizer` remains an
explicitly-labelled engineering device for CPU smoke tests.

## 2. Scientific evidence contract (`scientific_evidence.py`)
`LaboratoryEvidence` captures: image id/hash, instrument/specimen id, imaging
session; material type + instrument anatomy; source laboratory, study, reference
method; independently-verified material identity / physical condition; measurement
value + units + **uncertainty** (number, `"unknown"`, or `None` — never a fabricated
0); mask/spatial-annotation ref; reviewer id, verification status, approval
evidence; data rights, retention, provenance; and explicit limitations +
unresolved ambiguities.

**Four layers stay strictly separate:** (1) AI-detected anomaly, (2) human visual
interpretation, (3) laboratory-confirmed identity, (4) clinical disposition —
the last is **never produced here**. `link_observation` defaults the AI↔material
relationship to **indeterminate**; a confirmed material identity is recorded
**only** from verified lab evidence linked by an authorized reviewer, never from
the AI anomaly. `infer_identity_from_rgb` **raises** — no oxidation-colour staging
or biological-age-from-RGB inference.

**Category-appropriate requirements** (`validate_evidence`): corrosion → material
characterization (EDS/XRD/…) + affected-area measurement + units + uncertainty;
pitting → microscopy/profilometry + pit geometry; blood-like → documented soil
identity + lab confirmation (protein/hemoglobin assay); bone/tissue → composition
/independently-verified particle identity; verified-normal/confounding →
independent review/reference standard.

## 3. Calibration & validated evaluation (`calibration.py`, `anomaly_experiment.py`)
The previous per-image thresholding is replaced: thresholds are frozen on a
**dedicated calibration set of normal images** (image- and pixel-level, at the
`1 − target_fpr` quantile) **before** held-out evaluation. The experiment splits
verified-normals into a fit set and a disjoint calibration set (or takes an
explicit calibration set), freezes the threshold, then evaluates held-out data.
Metrics: **AUROC (+ bootstrap CI), average precision; precision/recall/FNR,
sensitivity/specificity at the frozen threshold (+ Wilson CIs); Dice/IoU where
valid reference masks exist; per-subgroup AUROC where sample sizes permit;
abstention rate; latency.** Leakage across instrument/specimen/session/image-hash
**and laboratory batch** is rejected. Severity is never inferred from scores.

## 4. Research-artifact integrity (`artifact_store.py`, `scientific_annotation.py`)
- Heatmaps are persisted to a **tenant-scoped, access-controlled** store; a
  heatmap reference is returned **only** when the artifact is stored and
  resolvable — otherwise no reference (no dangling refs).
- Malformed masks/heatmaps and non-finite values are rejected before evaluation
  (`validate_mask`, `validate_heatmap`, `sanitize_score`).
- Spatial annotations reuse the existing Project Canvas annotation model (no
  second DB, no new taxonomy); `verify_mask_alignment` / `verify_bbox` check
  dimensions/orientation/coordinates/version; `relate_region_to_reference` keeps
  an **indeterminate** relationship whenever lab evidence can't be reliably
  connected to a visible region.
- A directly-supplied research dataset must pass the **same** usage-rights /
  provenance / consent / tenant checks (`enforce_supplied_dataset_governance`) —
  it cannot bypass Project Canvas governance; cross-tenant mixing is refused.

## Distinguishing implemented vs executed vs validated
- **Implemented code (tested):** scientific evidence contract + category rules,
  4-layer separation, calibration/frozen-threshold evaluation with CIs,
  artifact-integrity store, annotation alignment, supplied-dataset governance,
  non-finite guards, and the real Anomalib PaDiM/PatchCore adapters.
- **Executed real-model experiments:** **none** — real PaDiM/PatchCore are
  BLOCKED (no torch/Anomalib, no approved backbone, no governed verified-normal
  instrument data). Only the deterministic stub ran.
- **Scientific validation evidence:** **none yet** — the measured numbers are a
  synthetic technical test, not scientific validation.

## Executed results (this environment: no torch/Anomalib)
- `pytest tests/test_stage5c_scientific_evidence.py` → **17 passed, 1 skipped**
  (skip = torch/anomalib-gated). `tests/test_stage5b_anomaly_localization.py` →
  **15 passed, 1 skipped**. Full backend suite → **3955 passed, 5 skipped**;
  Ruff (`app tests research`) → clean.
- Synthetic technical test (stub; 12 normal → 8 fit / 4 calibration; 11 held-out):
  frozen image/pixel thresholds; image-level AUROC **1.0** (synthetic), pixel mean
  Dice **0.59**, IoU **0.59**; abstention 0; latency **~3.6 ms/image**. Real
  PaDiM/PatchCore **BLOCKED** (`resnet18_imagenet` unapproved).

## Outstanding operational blockers
1. Isolated torch + Anomalib 1.1.x environment (pin + record the exact version).
2. Approved, rights-cleared, SHA-256-recorded `resnet18_imagenet` backbone.
3. Governed, independently-verified **verified-normal** instrument images + a
   held-out set with **validated spatial masks** and **laboratory evidence**.
4. Suitable CPU/GPU for real PaDiM/PatchCore fit/score + latency/memory capture.

## Stage 5D readiness & scientific-labeling requirements
1. Provision the isolated environment + approve the backbone (blockers 1–2).
2. Ingest governed laboratory evidence via the Stage 5C contract; require
   category-appropriate reviewed evidence; keep the four layers separate.
3. Predefine the full evaluation protocol + frozen thresholds; run real PaDiM then
   PatchCore; report metrics with CIs and per-subgroup breakdowns **and** their
   limitations; never infer severity from scores.
4. Score calibration remains a Stage 5D step; outputs stay research-only — no
   mapping of anomaly regions to clinical classes, no entry into technician
   recommendations, the Lumen Decision Engine, deployment, or OEM intelligence,
   until a separate governed review. Stage 5C is **not** scientifically validated
   by its passing code tests.
