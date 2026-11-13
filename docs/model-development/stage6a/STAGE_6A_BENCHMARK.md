# Stage 6A — Real Evidence Acquisition & Scientific Model Benchmark

Status: **research-only.** No production clinical inference, technician recommendation,
Lumen Decision Engine, clinical serving, manufacturer intelligence, model promotion, or
clinical disposition is changed. Extends Stage 5D (PR #166). Reuses — does not duplicate
— Project Canvas, Project Lens, LCID, Stage 4 governance, and the Stage 5A–5D research
infrastructure.

> **Honesty clause.** This stage delivers real-data **acquisition readiness** and runs
> the real models through the **governed benchmark harness**, but produces **no real
> scientific performance**: no authorized real surgical-instrument/borescope images and
> no public-rights-cleared pretrained checkpoint exist here. The executed numbers verify
> the governed pipeline runs and is deterministic on **synthetic non-clinical inputs**
> with a **locally-generated research-execution backbone** (`scientifically_valid=
> False`). Synthetic execution is never reported as scientific or clinical performance.

---

## 1. Implemented vs executed vs scientifically validated

| Layer | Status |
|---|---|
| **Implemented code (tested)** | Cohort-readiness validator + machine-readable report; operator checkpoint approval with SHA-256; genuinely-executable governed PaDiM/PatchCore localizers; governed benchmark harness. System-python targeted suites green; Ruff clean. |
| **Executed experiments** | Real Anomalib PaDiM + PatchCore run **through the governed localizer interface** (`run_anomaly_experiment`), deterministic, backbone coverage 1.0 — on **synthetic** inputs with a locally-generated backbone. |
| **Scientific evidence** | **None.** No authorized real cohort, no reviewed ground truth, no lab evidence. Real benchmark **BLOCKED**. |
| **Clinical evidence** | **None** (separate governed pathway; Stage 6B). |

## 2. Real-data acquisition readiness (§2)

`research/lens_vision/cohort_readiness.py` (builds on `DATASET_ACQUISITION_SPEC.md`, no
new registry):

- `validate_image_readiness` checks each manifest image against the full contract:
  instrument/specimen ids (+ manufacturer/model where known), modality
  (external-camera | borescope), anatomy zone, imaging session, device, lighting;
  image SHA-256 + research-authorized provenance; institutional authorization, data
  rights, retention; independently-reviewed label + reviewer; laboratory evidence for
  abnormal classes; approved masks for spatial regions; and fit/calibration/validation/
  sealed-test group identifiers.
- **Unlabeled images can never be used as verified-normal training examples**; clinical
  provenance is rejected without explicit approval.
- `generate_cohort_readiness_report` emits a **machine-readable** report: per-image and
  per-modality readiness, aggregated missing-evidence, **cross-split leakage detection**,
  and `ready_for_benchmark`. It contains **no** accuracy/performance numbers (enforced
  by test).

## 3. Approved-checkpoint execution (§3)

- Licensing verification: `CHECKPOINT_LICENSING.md`. `resnet18_imagenet` stays **BLOCKED**
  (`approved=False`, `rights_cleared=False`) — ImageNet weight terms must be verified by
  a human; LumenAI never auto-downloads them.
- `register_operator_approved_checkpoint` lets an operator approve a placed backbone with
  a recorded, fail-closed **SHA-256**; rights clearance is the operator's explicit
  assertion.
- The Stage 5C `PadimLocalizer`/`PatchCoreLocalizer` are now **genuinely executable**
  (manual embedding-accumulation fit; robust PaDiM/PatchCore score; float32 inputs;
  seeded determinism), loading the backbone only through the safe, **coverage-verified**
  governed path — not solely the low-level smoke script.

## 4. Governed benchmark execution (this environment)

Full-stack research venv — torch 2.15.0+cu132, numpy 1.26.4, anomalib 1.1.3, CPU
(`research-env.lock.txt`, Stage 5D). Evidence: `governed_benchmark_result.json`.

| Model | Through governed localizer | Backbone coverage | Fit / Calib | Frozen threshold | Deterministic |
|---|---|---|---|---|---|
| **PaDiM** | ✅ `run_anomaly_experiment` | 1.0 | 7 / 3 | ✅ | ✅ |
| **PatchCore** | ✅ `run_anomaly_experiment` | 1.0 | 7 / 3 | ✅ | ✅ |

Backbone: locally-generated, random-init (SHA-256 `68a421e7…` / `764bce02…`),
`scientifically_valid=False`. **Synthetic inputs → not scientific performance.**

**Real-image benchmark: BLOCKED** — no authorized, independently-reviewed real cohort is
present. The harness, leakage controls, frozen-threshold calibration, PaDiM-vs-PatchCore
comparison, and metric computation (AUROC/sensitivity/specificity/precision/FNR + Dice/
IoU with masks, CIs, abstention, hard-negative and subgroup handling) are in place and
tested on synthetic fixtures (`anomaly_experiment.py`), and will produce scientific
numbers **only** when an authorized, reviewed cohort is supplied.

## 5. Scientific evidence review (§5)

`SCIENTIFIC_EVIDENCE_REVIEW.md`: the four separated layers, the per-category measurement
availability matrix, and the forbidden inferences (biological identity, pit depth,
oxidation age, cleanliness, sterility are never inferred from an anomaly score).

## 6. Governance & validation safeguards (§6)

Preserved and tested: cross-tenant authorization, clinical/research provenance
separation, data-use permissions, checkpoint governance (operator approval + SHA),
image integrity, and independent ground-truth review. Research models do not enter
technician recommendations, the Lumen Decision Engine, clinical serving, or manufacturer
intelligence; **no automatic Candidate promotion** (`clinical_promotion_eligible=False`
on every output; `app/` imports nothing from `research/`).

## 7. Outstanding institutional & laboratory requirements

1. Institutional authorization / data-use agreements / IRB determinations for authorized
   real images; **no unauthorized hospital images**.
2. Qualified laboratory partner(s) + reference methods per category (EDS/XRD/microscopy/
   profilometry/assay/composition).
3. Independently-reviewed labels + adjudication + recorded inter-reviewer agreement.
4. Human-verified, licensed (public-rights) pretrained backbone + recorded SHA-256, or a
   permissively-licensed alternative.
5. Suitable CPU/GPU for full-cohort fit/score at scale.

## 8. Stage 6B — prospective clinical-validation readiness recommendation

Stage 6A establishes the *research* benchmark pathway. **Stage 6B (prospective clinical
validation) must NOT begin until** all of §7 is satisfied **and**, additionally:

1. A **real-image research benchmark has actually been run** on authorized, reviewed data
   (external-camera and borescope cohorts evaluated separately), with pre-registered
   endpoints, frozen thresholds, leakage controls, and reported metrics + CIs — i.e. the
   BLOCKED items above are cleared and the numbers exist.
2. A **statistical and clinical reviewer** approve the benchmark results, cohort sizes,
   and the intended-use definition.
3. A **separate institutional approval** (IRB/ethics) and governance review authorize a
   **prospective, shadow (non-interventional)** clinical evaluation — research outputs
   remain non-actionable; no technician recommendation, Decision Engine entry, clinical
   serving, promotion, or manufacturer intelligence.
4. A pre-registered **clinical** protocol defines prospective endpoints, safety
   monitoring (missed-finding / out-of-scope), abstention, and stopping rules.

**Recommendation:** proceed to assemble the authorized dataset and run the real-image
benchmark (Stage 6A→6B bridge) under institutional and laboratory approval; defer any
prospective clinical-validation activity to Stage 6B behind the gates above. Stage 6A is
**reproducible benchmark infrastructure with genuine governed model execution — not
scientific or clinical validation**, and is not validated by its passing code tests.
