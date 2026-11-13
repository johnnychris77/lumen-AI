# Stage 5D — Real Instrument & Borescope Validation (research-only)

Status: **research-only.** No clinical inference, technician recommendation,
patient-facing workflow, model promotion, manufacturer intelligence, or clinical
disposition is changed. Extends Stage 5C (PR #165). Reuses — does not duplicate —
Project Canvas, Project Lens, the Lumen Decision Engine, LCID, and all Stage 4–5C
governance.

> **Honesty clause.** This stage achieves genuine *model execution* and builds the
> *validation infrastructure*. It does **not** constitute scientific or clinical
> validation. The executed numbers are shapes / latency / memory on **synthetic
> non-clinical tensors** with a **locally-generated random-init backbone**. No
> accuracy, sensitivity, specificity, Dice, or clinical performance is measured or
> implied. **No real instrument or borescope data exists.**

---

## 1. Implemented code vs executed experiments vs scientific validation

| Layer | Status |
|---|---|
| **Implemented code (tested)** | Stage 5C hardening (safe loader, grouped leakage, reviewer-auth linkage, tenant-scoped artifacts), baseline-independence, the genuine real-model smoke script, and all evaluation/calibration code. Full backend suite **3966 passed / 8 skipped**; Ruff clean. |
| **Executed real-model experiments** | **PaDiM and PatchCore genuinely executed** (Anomalib 1.1.3, real torch) — fit + score, real anomaly maps — on synthetic non-clinical inputs with a locally-generated backbone. Evidence: `real_model_smoke_result.json`. |
| **Scientific validation evidence** | **None.** No real data, no reviewed ground truth, no lab evidence, no sealed-cohort evaluation. |
| **Clinical validation evidence** | **None.** Requires institutional approval + a separate governed pathway. |

Passing code tests and a successful execution smoke do **not** make Stage 5D
scientifically or clinically validated.

## 2. Stage 5C integration weaknesses corrected (§2)

Each finding has a regression test in `backend/tests/test_stage5d_hardening.py`.

1. **Checkpoint architecture / tensor / dimension verification** —
   `backbone_loader.verify_state_dict_against_module` checks tensor names and shapes;
   coverage is computed and reported.
2. **Unsafe deserialization** — `safe_torch_load` uses `weights_only=True`; a
   pickled object graph is refused (`UnsafeCheckpointError`).
3. **Reject uninitialized / partial backbones** — `load_verified_backbone` refuses
   missing-key / low-coverage / shape-mismatch loads **unless** an explicit,
   documented `CompatibilityPolicy` authorizes it (which may flag
   `scientifically_valid=False`). `_build_model` now uses this path.
4. **Implicit downloads prevented** — `pre_trained=False` + `set_offline_environment`
   (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, torch-hub download disabled).
5. **Specimen/session/batch separation across fit, calibration AND test** — grouped
   fit/calibration split (a specimen never straddles fit and calibration) +
   three-way identity separation (batch separates train from the sealed test set).
6. **Authenticated reviewer authorization + image/specimen matching** —
   `link_observation` now requires a `ReviewerAuthorization` (authenticated,
   `scientific_reviewer` role, identity matching the evidence verifier) **and** the
   anomaly's image-hash/specimen to match the evidence (`LinkageAuthorizationError`).
7. **Tenant authorization on artifact retrieval** — `ResearchArtifactStore.resolve`/
   `exists` require a `requesting_tenant_id`; cross-tenant reads denied; the stored
   payload's tenant is re-verified (`TenantAccessError`).

## 3. Genuine PaDiM / PatchCore execution (§3)

Isolated research venv (`.venv-research`, never CI/prod), pinned in
`research-env.lock.txt`. Key versions: **torch 2.15.0+cu132, torchvision 0.29.2,
numpy 1.26.4, anomalib 1.1.3, timm 1.0.31, lightning 2.6.6** (CPU; no GPU present).

**Reproducibility finding:** anomalib 1.1.3 pulls `imgaug 0.4.0`, which uses
`np.sctypes` (removed in NumPy 2.0), while torch/pandas/opencv resolved against
NumPy 2. A single reproducible environment required pinning a **numpy-1.26-consistent
set** (numpy 1.26.4 + pandas 2.1.4 + opencv-python-headless 4.9 + scikit-image 0.22 +
scikit-learn + open-clip-torch). A `rich` progress-bar incompatibility in the coreset
sampler was worked around (UI only — algorithm unchanged). `download.pytorch.org` is
blocked by the environment's network policy, so torch was installed from PyPI.

Executed (script: `backend/research/scripts/stage5d_real_model_smoke.py`; evidence:
`real_model_smoke_result.json`):

| Model | Fit | Score (anomaly map) | Notes |
|---|---|---|---|
| **PaDiM** | 8 normals → embedding (8,100,64,64), ~1.3 s | (1,1,256,256), ~54 ms, all-finite | real Anomalib PaDiM, multivariate-Gaussian fit |
| **PatchCore** | 8 normals → coreset memory bank (627,384), ~0.37 s | (1,1,224,224) | real Anomalib PatchCore, kNN memory bank |

- Backbone: **locally generated, random-init** (SHA-256 `e4cf3c49…`), **no
  ImageNet/DINOv2/third-party-rights weights**; loaded through the governed, safe,
  verified path at coverage 1.0 under a policy with `scientifically_valid=False`.
- Peak RSS ~1.56 GB; CPU only; deterministic (`torch.manual_seed(0)`).
- **This is execution proof only.** Inputs are synthetic tensors; nothing here is a
  model-performance or clinical-accuracy claim, and the stub is never presented as
  PaDiM/PatchCore.

**Not executed (BLOCKED):** real PaDiM/PatchCore on the governed
`resnet18_imagenet` backbone — it remains unapproved / rights-not-cleared, so the
Stage 5C `PadimLocalizer`/`PatchCoreLocalizer` still raise `CheckpointNotApprovedError`
(correct, fail-closed).

## 4–7. Dataset, ground-truth, evaluation, baseline independence

- **§4 Dataset program** → `DATASET_ACQUISITION_SPEC.md` (external + borescope;
  clean refs; corrosion/pitting; blood/bone/tissue with independent reference; hard
  negatives; Canvas/LCID governance; research-only specimens never return to clinic;
  no "absence ⇒ normal"; no hospital data without authorization).
- **§5 Ground truth** → `GROUND_TRUTH_PROTOCOL.md` (predefined protocol, two blind
  qualified reviewers, adjudication, image + spatial labels, lab evidence where
  necessary, four separated layers, no identity-from-appearance).
- **§6 Evaluation** → `EVALUATION_PROTOCOL.md` + working code in
  `anomaly_experiment.py` (predefined endpoints, fit/calibration/validation/sealed
  split, grouped leakage control incl. batch, calibrate without test outcomes,
  per-modality metrics with CIs, abstention, no fabricated denominators).
- **§7 Baseline independence** → `baseline_independence.py` (standalone anomaly
  detection needs no manufacturer baseline; baseline is advisory enrichment that
  never overwrites an anomaly or authorizes release).

## 8. Clinical safety & deployment (§8)

- All experiments are research-only; `app/` imports nothing from `research/`
  (asserted in `test_stage5d_safety_and_baseline.py`).
- Production clinical inference is unchanged — the live adapter still honestly
  reports `ai_unavailable` with no fabricated observation.
- Anomaly localization alone is **never** confirmed blood / corrosion / pitting /
  sterility; `ScientificObservation` carries no clinical disposition and no
  confirmed diagnosis.
- A pilot or shadow evaluation requires **separate institutional approval** and the
  existing governance gates — out of scope here.

## 9. Clinical-validation readiness assessment

**Ready (infrastructure):** governed ingestion/annotation/evidence contracts;
leakage-safe grouped split + frozen-threshold calibration + CI metrics; safe,
verified, governed model loading; genuine real-model execution path proven on CPU;
baseline-independent capability; research/production isolation.

**Not ready (no evidence yet) — required before any clinical-validation claim:**

1. **Institutional/ethics:** data-use agreements, IRB/ethics determinations, and
   authorization for any facility/clinical-adjacent data.
2. **Laboratory:** qualified partner(s) + methods for the independent reference
   measurements (EDS/XRD/microscopy/assay/composition) that define ground truth.
3. **Data:** governed external-camera and borescope cohorts across all classes +
   hard negatives, with per-specimen identity metadata.
4. **Ground truth:** signed annotation protocol, two blind qualified reviewers,
   adjudication, recorded inter-reviewer agreement, lab-confirmed identities.
5. **Approved backbone:** rights-cleared, SHA-256-recorded pretrained weights (the
   execution smoke used a locally-generated, non-scientific backbone).
6. **Statistical/clinical sign-off:** predefined endpoints, powered cohort sizes,
   and sealed-test criteria approved before unblinding.
7. **Hardware:** suitable CPU/GPU for full-cohort fit/score + latency/memory at scale.

**Bottom line:** Stage 5D demonstrates genuine research-model execution and a
reproducible, independently-reviewable validation pathway. It is **readiness
infrastructure**, not executed scientific or clinical validation, and it is **not**
scientifically validated by its passing code tests.
