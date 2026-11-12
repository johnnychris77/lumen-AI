# Stage 5 — Project Lens Scientific Vision-Model Plan

Status: **design / planning** (no code, no training, no deployment in this document).
Audience: Principal Software Architect + clinical/ML governance reviewers.
Scope: a source-backed technical implementation plan for evolving **Project Lens**
from its current pure-Python baseline to real, scientifically-validated vision
models — **without** weakening the Stage 4 provenance and model-governance
foundation, and **without** modifying the clinical defect-detection algorithms,
the manufacturer baseline comparison, Project Canvas, the Lumen Decision Engine,
the clinical taxonomy, or human-review controls.

> **Guardrails (binding on every Stage 5 work item).** Research-only experiments
> are strictly separated from clinical validation. No restricted/non-commercial
> dataset is downloaded or used for a commercial/clinical model. No production
> model is trained and no inference is deployed from this plan. No clinical
> accuracy is claimed anywhere without executed, governed evidence. Every claim
> below about an external model, dataset, or license is **to be re-verified**
> against the upstream source before any download or use (see §12).

---

## 1. Current state (grounded in the codebase)

Project Lens today is a deliberately dependency-light baseline:

| Concern | Where | What it is today |
|---|---|---|
| Model | `services/ml/lens_training_pipeline.py`, `training_execution.py:_feature_vector` | Pure-Python, Pillow-only hierarchical (Stage B abnormal / Stage C category) **one-vs-rest logistic regression** over hand-computed image features. No `torch`/`numpy`/`sklearn`/`cv2` are installed. |
| Taxonomy | `services/observation_taxonomy.py` | Exactly 10 observation categories, probability-language only. Rust/corrosion/pitting/discoloration **all collapse** into `probable_corrosion_like_degradation`; no localization, no pitting-specific class, no segmentation. |
| Dataset governance | `services/ml/dataset_registry.py`, `models/dataset_governance.py` | Governed per-image registry, immutable dataset versions, annotation lifecycle, double-blind review, `ImageLabel` with two-reviewer gold for critical classes (blood/crack/missing_component). |
| Provenance (Stage 4) | `services/ml/provenance_governance.py` | Fail-closed structured provenance; clinical only when verified `real_clinical` + authorized, evidenced approval tied to real `UserRoleAssignment` / `VeritasEvidenceProvenanceRecord` / `ConsentRecord`. |
| Leakage-safe split | `services/ml/dataset_split.py` | Union-find grouping over instrument / inspection / specimen / session / image-SHA; `grouping_reliable` signal gates clinical promotion. |
| Calibration & uncertainty | `services/ml/lens_calibration.py` | Temperature scaling + abstention threshold; abstains to `unknown_review_required`. |
| Serving & governance | `services/ml/live_inference_adapter.py`, `deployment_gates.py`, `candidate_promotion.py` | Actionable vs shadow serving separated (`HEALTH_SHADOW_ONLY` / `shadow_evaluate`); approval ladder experimental→pilot→validated; deployment not_deployed→shadow→deployed; models never auto-promoted. |
| Shadow validation | `services/ml/shadow_mode.py` + `shadow_*` | Silent prediction, reconcile-after-finalization, error-review queue, drift/safety monitors. |
| Audit | `services/enterprise_audit_service.py` | Hash-chained immutable audit for every governance action. |

**Implication for Stage 5.** The governance, data, split, calibration, shadow,
audit, and promotion scaffolding already exists and is strong. Stage 5 is
primarily a **model-capability** upgrade (deep vision models with localization,
severity, and uncertainty) that must plug into — not replace — that scaffolding,
and the pure-Python baseline is retained as a fallback and regression anchor.

---

## 2. Objectives and the six research priorities

Stage 5 adds **spatially-localized, severity-aware, uncertainty-quantified**
vision capability for the priority categories, mapped onto the existing taxonomy
(no taxonomy change required for the first increment):

| Priority | Existing taxonomy anchor | New capability needed |
|---|---|---|
| Rust & corrosion detection | `probable_corrosion_like_degradation` | Pixel-level corrosion segmentation + extent |
| Pitting localization | (currently folded into corrosion) | Localized pit detection; **candidate** new sub-category, taxonomy change gated by governance |
| Blood-like residue detection | `probable_blood_like_residue` | Residue segmentation + coverage severity |
| Bone/tissue-like particulate | `probable_bone_like_fragment`, `probable_tissue_or_organic_residue` | Particulate detection + localization |
| Abnormality segmentation & spatial localization | all contamination classes | Per-category masks + bounding regions, not just image-level labels |
| Category-specific severity evidence & uncertainty | `lens_calibration` (image-level only today) | Per-category severity scale + calibrated, ideally distribution-free, uncertainty |

Each is delivered first as a **research-only** experiment, then — only on governed
`real_clinical` data with reliable grouping — advanced through the existing
shadow→pilot→validated ladder.

---

## 3. Architecture

### 3.1 Two-track model program
- **Track R (research-only):** transfer-learning and anomaly-localization
  experiments on **non-clinical** data (synthetic/external/laboratory provenance
  classes). Produces infrastructure, recipes, and baselines. Never drives a
  technician-facing recommendation. Governed by provenance class
  `synthetic_experimental` / `external_nonclinical` / `laboratory_controlled`.
- **Track C (clinical validation):** the same architectures retrained/validated
  **only** on governed `real_clinical` + approved + reliably-grouped cohorts, then
  put through shadow validation. This is the only track that can reach `deployed`.

The provenance class on each `DatasetRegistryEntry` is the hard boundary between
the tracks (`services/ml/provenance_governance.py`); a Track-R artifact can never
be promoted to clinical serving because `clinical_promotion_eligible` requires
verified clinical provenance **and** reliable grouping.

### 3.2 Model stack (new, isolated dependency surface)
Introduce an **optional**, env-gated DL stack so the pure-Python baseline keeps
working where the stack is absent:
- **Backbone:** a self-supervised ViT (DINOv2, Apache-2.0) or a CNN
  (ConvNeXt/EfficientNet) as a frozen/fine-tuned feature extractor — strong for
  small labeled sets (see §5).
- **Heads:**
  - *Classification* head over the 10-category taxonomy (replaces the logistic
    Stage C when validated; the logistic model remains the fallback).
  - *Segmentation* head (U-Net / DeepLabv3+ / Mask2Former, or nnU-Net for a
    per-task medical-grade baseline) for localization and severity-by-extent.
  - *Unsupervised anomaly localization* (PatchCore/PaDiM via Anomalib) trained on
    **normal** instrument images to flag "abnormal region" without per-pixel
    labels — a pragmatic first step given annotation scarcity.
- **Serving:** export to **ONNX** and run CPU-side (or a single small GPU) behind
  the existing `live_inference_adapter` contract; the adapter's health states,
  shadow/actionable split, calibration, and abstention are unchanged.

### 3.3 Where it plugs in (no new engines)
- Training → the existing `run_lens_training` / `candidate_training` orchestration,
  extended to call the DL trainer when the stack is present; it keeps emitting the
  same run dict (`clinical_promotion_eligible`, `grouping_reliable`, calibration,
  error analysis) that governance already consumes.
- Serving → `live_inference_adapter.load_active_model` / `predict` already gate on
  review+approval+deployment and separate shadow from actionable; a DL model is
  just another `ModelRegistryEntry` artifact with a new `architecture` string and
  `preprocessing_version`.
- Decisioning → the Lumen Decision Engine and manufacturer baseline comparison are
  untouched; Lens output remains an **advisory observation** with
  `human_review_required: true`.

---

## 4. Pretrained models evaluated (re-verify licenses before use)

| Model | Role | License (to re-verify) | Notes |
|---|---|---|---|
| **DINOv2** (Meta) | Backbone / feature extractor for small-data transfer | Apache-2.0 (relicensed Aug 2023) | Repeatedly strong on small industrial defect sets with few labels. **DINOv3 uses a custom, non-Apache license — do not assume it carries over.** |
| **ConvNeXt / EfficientNet** (torchvision) | CNN backbone alternative / ensemble diversity | BSD-3 / Apache-2.0 | Well-understood fine-tuning; good ONNX export. |
| **SAM 2** (Meta) | **Annotation assist only** (interactive masks), not an in-product detector | Apache-2.0 (code + weights); SA-V data CC BY 4.0 | Benchmark mask quality on our own images first; SAM is less reliable out-of-the-box on medical/industrial close-ups. |
| **nnU-Net** | Per-task medical-grade segmentation baseline | Apache-2.0 | Trains a new model per task; strong reference baseline for segmentation. |
| **Anomalib** (Intel: PatchCore, PaDiM) | Unsupervised anomaly localization from mostly-normal images | Apache-2.0 | PatchCore/PaDiM localize defects without per-pixel labels; good first step under label scarcity. |

Backbone and library weights are **research infrastructure**; using them does not
make an output clinical. Clinical standing still requires Track-C provenance +
shadow validation.

---

## 5. Datasets evaluated (research-only vs usable; re-verify every license)

| Dataset | Content | License (to re-verify) | Permitted use here |
|---|---|---|---|
| **MVTec AD** | Industrial anomaly/defect, pixel masks | Academic / research-only (unverified for commercial) | **Track-R only**; never a basis for a clinical/commercial model |
| **NEU Surface Defect** | Steel surface defects, **bounding boxes** | Academic | Track-R classification experiments only |
| **Severstal Steel** | Steel defects, pixel masks | Kaggle competition terms | Track-R only **after** confirming competition reuse terms |
| **Roboflow "Corrosion Dataset v2"** | Corrosion/pitting imagery | CC BY 4.0 (commercial w/ attribution) | Candidate for corrosion/pitting pretraining; **verify annotations & provenance before use** |
| **AFM pitting-corrosion (MOST Wiedzy)** | Pitting micrographs | CC BY-**NC** (non-commercial) | **Research-only**; excluded from any commercial/clinical model |
| **HemoSet** | Blood **segmentation** (intraoperative field) | Academic (verify) | Weak transfer — surgical field, **not** instrument cleanliness; reference only |
| **Internal governed clinical images** | Real instrument inspection images | Governed via Stage 4 registry + consent | **Track-C only**, when `real_clinical` + approved + reliably grouped |

**Honest scarcity finding.** No public imaging dataset for *residual blood/protein
on reprocessed surgical instruments* was found (ProReveal is a commercial
fluorescence protein **test**, not a dataset). Blood-like/bone-like/tissue-like
and instrument-specific corrosion therefore depend primarily on **internal
governed clinical data** plus limited non-clinical transfer. This directly shapes
the annotation plan (§7) and the realistic timeline (§9).

---

## 6. Hardware & training infrastructure

- **Current environment:** CPU-only, no GPU, no DL frameworks installed. Suitable
  for pure-Python baseline + ONNX CPU inference, **not** for training ViT/U-Net.
- **Research training (Track R):** a single mid-range GPU (e.g. one L4/A10-class,
  24 GB) is sufficient for fine-tuning DINOv2/ConvNeXt and small U-Net/PatchCore
  jobs; larger segmentation runs benefit from one A100-class GPU. Use ephemeral,
  isolated training instances — **never** the production app environment.
- **Serving:** ONNX Runtime CPU for the first clinical increment (latency budget
  permitting) to avoid a GPU dependency in production; revisit GPU serving only if
  a validated model needs it.
- **Reproducibility:** keep the existing deterministic-seed + `config_hash` +
  `git_commit` discipline (`training_config.py`); pin framework versions; record
  the training instance type in the model card.
- **Dependency isolation:** the DL stack is an **optional extra** (separate
  requirements group) so the core API image stays slim and the pure-Python path
  keeps passing CI without `torch`.

---

## 7. Clinical annotation requirements

- **Tooling:** CVAT or Label Studio for masks/boxes; **SAM 2-assisted** mask
  proposals to speed labeling (benchmark SAM quality on our images first); MONAI
  Label is an option if 3D/volumetric ever applies.
- **Governance reuse:** annotations flow through the existing `ImageLabel` /
  double-blind review / annotation-lifecycle machinery. Keep the **two-reviewer +
  adjudication gold** rule for critical classes (blood/bone/crack/missing_component).
- **Label types:** per-category segmentation masks (for localization/severity) and
  image-level labels; store masks referencing `RetainedImage`/`DatasetRegistryEntry`
  by id (no duplicate bytes), consistent with current provenance.
- **Severity rubric:** define a per-category severity scale (e.g. extent/coverage
  bands) with written criteria and inter-rater agreement measured — severity is
  **evidence-based**, not a model guess.
- **Provenance at ingest:** every annotated image carries a structured provenance
  class; `real_clinical` stays `pending` until an authorized, evidenced approval.

---

## 8. Severity evidence & uncertainty quantification

- **Severity:** derive from segmentation (area/coverage/count of pits or residue
  regions) against the written rubric; report as category-specific evidence with
  the mask, never a bare number.
- **Uncertainty (layered):**
  1. Keep temperature-scaled calibration + abstention (`lens_calibration`).
  2. Add **deep ensembles** and/or MC-dropout for per-pixel/per-category
     uncertainty maps (research literature treats ensembles as a strong baseline).
  3. Add **conformal prediction** for *distribution-free* guarantees — e.g.
     controlling the false-positive or false-negative pixel proportion of a
     segmentation at a chosen risk level — which is the most defensible route to a
     governed uncertainty claim.
- **Abstention stays first-class:** low-confidence or out-of-distribution →
  `unknown_review_required`, never a fabricated confident finding.

---

## 9. Phased roadmap

1. **S5-0 Foundations (Track R):** add the optional DL dependency group; stand up
   an isolated training harness; wire ONNX export/inference behind the existing
   adapter contract; **no clinical data**. Exit: a DINOv2/ConvNeXt classifier
   reproduces the baseline's taxonomy labels on non-clinical data through the
   existing run-dict + governance.
2. **S5-1 Localization (Track R):** PatchCore/PaDiM anomaly localization + a U-Net
   segmentation prototype on licensed non-clinical corrosion/defect data. Exit:
   mask outputs + severity-by-extent, research-only.
3. **S5-2 Annotation program:** stand up CVAT/Label-Studio + SAM-assisted labeling;
   label a governed internal clinical pilot set with two-reviewer gold; measure
   inter-rater agreement and severity-rubric reliability.
4. **S5-3 Clinical candidate (Track C):** train/validate on governed `real_clinical`
   + approved + reliably-grouped cohorts; register as a `ModelRegistryEntry`
   candidate; **shadow mode only**.
5. **S5-4 Shadow validation:** run `shadow_evaluate` + `shadow_mode` reconciliation,
   drift/safety monitors, error-review queue; accumulate evidence for the
   deployment-gate checklist. Human-led promotion only; no auto-advance.
6. **S5-5 Uncertainty & severity hardening:** conformal guarantees + ensembles;
   finalize per-category severity evidence; model card + error analysis.

Taxonomy changes (e.g. a dedicated pitting sub-category) are a **governed decision**
taken no earlier than S5-2, with audit and clinical sign-off — not a code default.

---

## 10. Preservation & integration guarantees

- **Project Canvas, Project Lens, Lumen Decision Engine, clinical taxonomy, and
  human-review controls are preserved.** Lens output stays advisory with
  `human_review_required: true`; the Decision Engine and manufacturer baseline
  comparison are untouched.
- **Stage 4 controls are reused, not bypassed:** provenance gating, leakage-safe
  grouping, shadow/actionable separation, deployment gates, immutable audit, and
  never-auto-promote all apply to DL models exactly as to the baseline.
- **Fallback:** the pure-Python baseline remains the default where the DL stack is
  absent, and as a regression anchor.

---

## 11. Risks & open decisions

**Risks:** external dataset license/ethics (several are research-only or
non-commercial); scarcity of instrument-cleanliness clinical imagery; SAM/foundation
quality variance on close-up medical images; added serving complexity and latency;
over-trust of localized output (mitigated by abstention + human review + conformal
guarantees); dependency-surface growth (mitigated by the optional extra).

**Open decisions (need owner sign-off):** backbone choice (DINOv2 vs ConvNeXt) per
category; CPU-ONNX vs GPU serving; whether/when to add a pitting sub-category to the
taxonomy; severity rubric definitions; target risk levels for conformal guarantees;
training-instance provisioning and data-handling agreements for any external data.

**Non-goals restated:** no restricted-dataset downloads, no production training, no
inference deployment, and no clinical-accuracy claims without executed governed
evidence — all out of scope for this plan and for any single Stage 5 increment
until its gates are met.

---

## 12. Sources (re-verify before any download or use)

- SAM 2 — Apache-2.0 code+weights: https://github.com/facebookresearch/segment-anything-2 ; https://ai.meta.com/blog/segment-anything-2/
- DINOv2 Apache-2.0 relicense: https://ai.meta.com/blog/dinov2-facet-computer-vision-fairness-evaluation/ ; DINOv3 license caveat: https://github.com/facebookresearch/dinov3
- MVTec AD (research benchmark): https://openaccess.thecvf.com/content_CVPR_2019/papers/Bergmann_MVTec_AD_--_A_Comprehensive_Real-World_Dataset_for_Unsupervised_Anomaly_CVPR_2019_paper.pdf
- Defect-dataset review (NEU/Severstal/DAGM/Kolektor): https://arxiv.org/pdf/2305.13261
- Corrosion Dataset v2 (CC BY 4.0, verify): https://universe.roboflow.com/jnmp/corrosion-dataset-v2 ; AFM pitting CC BY-NC: https://mostwiedzy.pl/en/open-research-data/imaging-of-the-effects-of-pitting-corrosion-with-the-use-of-afm,528074439539950-0
- DINOv2 small-data defect transfer: https://arxiv.org/pdf/2506.03345 ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12300182/
- Anomalib / PatchCore / PaDiM: https://anomalib.readthedocs.io/ ; https://arxiv.org/pdf/2202.08341v1.pdf
- HemoSet blood segmentation: https://arxiv.org/abs/2403.16286
- Conformal segmentation uncertainty: https://arxiv.org/pdf/2410.03406 ; https://arxiv.org/html/2511.15406v1
- MONAI Label / AI-assisted annotation: https://arxiv.org/pdf/2203.12362
