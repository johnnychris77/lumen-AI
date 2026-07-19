# LPR-DIR-019 — AI Evolution Report (Phase 8)

## Honest current-state framing

**No production inference has run against real users**, so there are **no live
model-performance metrics** (no production accuracy, drift, or calibration data).
This report describes the **actual current AI/ML state** as implemented and
test-verified, and lays out an **evidence-based evolution path** — it does **not**
report production model KPIs (NOT AVAILABLE — not launched).

## Current AI/ML state (real — from code)

| Aspect | Current state | Evidence |
|---|---|---|
| Inference engine | **Deterministic placeholder inference**, honestly labeled "**not a trained CV model**" | Prior-directive code + labels |
| Model registry | `ModelRegistryEntry` — candidate models registered, checksum-verified | Governed pipeline |
| Dataset governance | `DatasetRegistryEntry`; freeze intended (AR-17 not yet enforced) | Phase 1 |
| Ground truth / annotation | `AnnotationVersion` + ground-truth stage; human-in-the-loop | Pipeline |
| Baselines / Digital Twin | `BaselineLibraryEntry`, `digital_twin_id` per instrument | Pipeline |
| Human review | Mandatory; `human_review_required: true` on correlation outputs | CLAUDE.md constraint |
| ML eval | `ml-eval-nightly.yml` scheduled eval workflow | CI |

**Key honesty anchor:** the platform does **not** currently ship a trained
computer-vision model. It ships a **governed pipeline** that can *register,
version, evaluate, and human-review* models, with a deterministic placeholder as
the current inference component. This is correctly and prominently labeled — it
must **not** be represented as clinical AI performance.

## Evolution path (evidence-based, staged)

| Stage | Goal | Precondition |
|---|---|---|
| AI-1 | **Instrument model-eval metrics** (per-candidate accuracy/precision/recall on frozen datasets) surfaced from `ml-eval-nightly` | Enforce AR-17 dataset freeze first |
| AI-2 | **Train + register a real candidate CV model** through the existing governed pipeline (dataset → candidate → human review → evidence) | Curated, frozen, PHI-free datasets |
| AI-3 | **Shadow / offline evaluation** of the candidate vs. placeholder before any production exposure | AI-1 metrics + human review |
| AI-4 | **Drift + calibration monitoring** once (and only once) a model serves real inferences | Controlled launch + OPS-OBS instrumentation |

## Guardrails that must survive any AI evolution (non-negotiable)

- **Never claim causation** — outputs stay "potential association / possible
  contributing factor / quality review recommended" (CLAUDE.md).
- **`human_review_required: true`** on all correlation outputs.
- **No FDA/regulatory-clearance claims** anywhere.
- **Hospital identities anonymized** in cross-hospital intelligence; **no PHI** in
  training/demo data or image metadata.
- Every intelligence-sharing action creates an **audit event**.

## Determination

The AI **governance scaffolding is real and strong** (registry, versioning, human
review, nightly eval, audit); the **model itself is a labeled placeholder**. The
honest next step is **AI-1 → AI-2 offline**, entirely pre-production. **No claim of
clinical or production AI performance can be made**, and none is made here.
