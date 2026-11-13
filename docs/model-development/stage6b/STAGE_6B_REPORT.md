# Stage 6B — Real-Image Scientific Validation & Clinical Study Readiness

Status: **research-only.** No production clinical inference, technician recommendation,
Lumen Decision Engine, clinical serving, manufacturer intelligence, model promotion, or
clinical disposition is changed. Extends Stage 6A (PR #167). Preserves Project Canvas,
Project Lens, LCID, scientific annotation, the checkpoint registry, validation, and
model-governance architecture.

> **Two explicit determinations.** The real-image benchmark is
> **`BLOCKED_REAL_IMAGE_BENCHMARK`** and prospective clinical validation is
> **`NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`** — because no authorized real
> surgical-instrument/borescope images and no license-and-source-verified scientific
> checkpoint exist here. No random-weight execution metric is presented as real-image
> scientific performance.

---

## 1. The four separated states (the report's spine)

| State | Stage 6B status |
|---|---|
| **Implemented software (tested)** | ✅ Corrected leakage grouping, fail-closed checkpoint governance, decomposed readiness; governed benchmark harness; protocol docs. |
| **Executed model experiments** | ✅ PaDiM + PatchCore run through the governed localizer (coverage 1.0, deterministic) — **synthetic inputs, random-weight backbone: pipeline verification only.** |
| **Independent scientific validation** | ❌ **None.** No authorized real cohort, no reviewed ground truth, no lab evidence → `BLOCKED_REAL_IMAGE_BENCHMARK`. |
| **Prospective clinical authorization** | ❌ **None** → `NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION` (separate IRB + governance required). |

## 2. Stage 6A safety-gap corrections (§2)

Each with regression tests in `test_stage6b_corrections.py`:

- **Dataset leakage (2a)** — `image_identity_tokens` returns the full physical-identity
  set (instrument, specimen, session, study batch, image hash, repeat-imaging); leakage
  is detected on **any** shared token, across all splits and **across modalities**
  (replaces Stage 6A's first-identity-only, per-modality grouping).
- **Checkpoint governance (2b)** — fail-closed: authenticated `approver_id` required;
  scientific use requires verifiable **license + source evidence**; random-weight
  backbones are `research_execution_only` and never scientific
  (`assert_scientific_checkpoint` → `CheckpointScientificUseError`).
- **Readiness integrity (2c)** — five independent dimensions (metadata completeness,
  verified authorization, ground-truth readiness, model-execution readiness, statistical
  adequacy). A filled manifest / one image per split is never "scientifically ready";
  statistical adequacy needs minimum per-modality sizes **and** a statistical-reviewer
  sign-off, plus an approved scientific checkpoint.

## 3. Real dataset & benchmark (§3–§4)

Reuses Canvas/LCID ingestion; **no fabricated or relabeled images; no unauthorized
hospital/external data**. The governed runner (`stage6a_governed_benchmark.py`) emits
**`BLOCKED_REAL_IMAGE_BENCHMARK`** with detailed `missing_requirements`
(`docs/model-development/stage6a/governed_benchmark_result.json`). Checkpoints and
datasets stay outside the repository.

## 4. Ground truth, evaluation, clinical study (§5–§7)

- `GROUND_TRUTH_VALIDATION.md` — qualified reviewers, adjudication, **reviewer-agreement
  measurement**, evidence linked to specimen/session/image/region, visual-vs-confirmed
  identity, category-appropriate confirming evidence.
- `PREREGISTRATION_AND_EVALUATION.md` — pre-registered intended use/hypotheses/endpoints/
  error definitions; verified group independence; statistical sign-off on sizes/CIs;
  per-modality/subgroup metrics with false-negative and confounder prominence; no
  identity/severity/cleanliness/sterility from scores.
- `PROSPECTIVE_CLINICAL_STUDY_PROTOCOL.md` — observational, non-interventional template;
  **`NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`**; the model must not influence
  instrument release or technician disposition.

## 5. Governance (preserved)

Cross-tenant authorization, clinical/research provenance separation, informed data-use
permissions, checkpoint governance, immutable audit, image integrity, and independent
ground-truth review are preserved. **No model promotion, no clinical recommendation, no
unauthorized clinical evaluation.** `app/` imports nothing from `research/`.

## 6. Limitations & unresolved blockers (missing evidence)

1. **Institutional/ethics** authorization + data-use agreements for authorized real
   images (external + borescope); no unauthorized hospital data.
2. **Laboratory** partner(s) + reference methods per category, or documented reference
   specimens/simulants for residue classes; reviewer-agreement on a pilot set.
3. **Data** — governed, reviewed cohorts meeting the pre-registered minimum sizes, with
   verified group independence across modalities.
4. **Checkpoint** — a human-verified, licensed (public-rights) pretrained backbone with
   recorded SHA-256 and license/source evidence (`assert_scientific_checkpoint`).
5. **Statistical/clinical** sign-off on endpoints, cohort sizes, and intended use.
6. **Compute** — suitable CPU/GPU for full-cohort fit/score at scale.

## 7. Success criterion

Stage 6B produces a **credible, independently-reviewable readiness position**: the
corrected, leakage-safe, fail-closed infrastructure plus an **explicit, evidence-based
blocker report** (`BLOCKED_REAL_IMAGE_BENCHMARK` / `NOT_READY_FOR_PROSPECTIVE_CLINICAL_VALIDATION`)
identifying exactly why a real-image scientific benchmark cannot yet occur. It is **not**
scientific or clinical validation and is not validated by its passing code tests.
