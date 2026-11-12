# Stage 5A — Scientific Vision Research Foundation (research-only)

Status: **research-only**. No clinical model trained, no inference deployed, no
clinical decisioning changed, no model auto-promoted. Builds on the Stage 4
provenance/governance foundation (PR #162) and the Stage 5 plan
(`STAGE_5_PROJECT_LENS_PLAN.md`).

## What this delivers

An **isolated, optional** computer-vision research package —
`backend/research/lens_vision/` — that is importable and fully testable **without
PyTorch**, reuses the production governance contracts read-only, and never touches
clinical decisioning, inference, promotion, deployment, or the manufacturer
baseline comparison.

### Isolation & reproducibility
- Heavy ML deps (PyTorch, torchvision, numpy) live in a **separate**
  `backend/requirements-research.txt` that **CI and production never install**.
  Every research module imports cleanly with no torch; CPU smoke tests use a
  deterministic stub embedder.
- `config.ResearchRunConfig` records seed, git revision, framework versions,
  checkpoint id + digest, and source provenance, and emits a stable
  `fingerprint()` so an identical config reproduces an identical run id.
- Nothing under `app/` imports `research/`. Model weights, datasets, patient
  images, and secrets are never committed.

### Pretrained visual-feature benchmark (DINOv2)
`benchmark.run_research_benchmark` runs: **provenance gate → group-safe split
(reusing the production `dataset_split`) → embedding extraction → lightweight
research classifier → evaluation on the governed observation labels → metrics +
model-card evidence**, with a fair comparison against the current Project Lens
Pillow-feature baseline using the same classifier head.

- `embeddings.Dinov2Embedder` — the real frozen DINOv2 path. It requires torch
  **and** an explicitly-approved, rights-cleared, hash-verified checkpoint
  (`checkpoint.verify_checkpoint`). The DINOv2 checkpoints are registered but
  **ship unapproved / rights-not-cleared**, so the real path is a documented,
  governed **blocker** (see licensing status below) — it raises rather than
  silently downloading or falling back.
- `embeddings.StubEmbedder` — a deterministic Pillow-only grid-mean extractor for
  **CPU pipeline smoke tests only**; it is explicitly **not** a learned model and
  produces **no** scientific embeddings.
- Every result is `research_only=True`, `clinical_promotion_eligible=False`, with
  a note that the metric is **not** a clinical accuracy claim.

### Anomaly-localization feasibility (PatchCore / PaDiM)
`anomaly_feasibility.feasibility_assessment()` gives a structured architecture
comparison (both normal-only/unsupervised, via Anomalib, Apache-2.0),
recommending **PaDiM first → PatchCore target**, with `data_status =
awaiting_qualified_image_data`. `AnomalyRegion` retains uncertainty, carries no
diagnosis, and **raises** on any attempt to convert an anomaly region into a
clinical finding (`ClinicalDiagnosisForbiddenError`). No prototype is trained in
this increment (blocked on permitted data + an isolated torch environment).

### Stage 4 governance reused (not bypassed)
- `provenance.assert_research_authorized` admits only `synthetic_experimental` /
  `external_nonclinical` / `laboratory_controlled` (and explicitly-approved
  `real_clinical` only on opt-in). Unknown/legacy/unapproved are refused
  (fail-closed).
- `provenance.is_clinically_promotable` is a constant **False** for research
  artifacts; external/lab data can never qualify for clinical promotion.
- `data_loader.load_research_samples` is **tenant-scoped** on both the registry
  query and the retained-image lookup — no cross-tenant bytes.
- Group-safe splitting, shadow/actionable separation, model approval, deployment
  authorization, and the Genesis grouping-reliability gate remain the Stage 4
  mechanisms; this increment adds no path around them.

## Dataset & checkpoint licensing status

| Asset | Status in this increment |
|---|---|
| DINOv2 ViT-S/14, ViT-B/14 | Registered, **BLOCKED** (`approved=False`, `rights_cleared=False`) pending license + data-rights verification. License noted Apache-2.0 (re-verify upstream). |
| WPI / DefectAtlas-20 / MVTec / any external dataset | **Not downloaded, not used.** Commercial/clinical training rights unverified. |
| Synthetic fixtures | `synthetic_experimental`; used solely for pipeline smoke tests. |
| Real clinical images | Governed via Stage 4; **not** used here (clinical-validation track, not research). |

No external dataset was downloaded or trained on; no clinical data was acquired;
no external research rights were fabricated.

## Tests & executed results

New suite `backend/tests/test_stage5a_research_foundation.py` (runs without
torch): dependency isolation, baseline-without-torch, research-only provenance
enforcement, checkpoint approval + file-hash verification, deterministic feature
extraction + reproducible benchmark, invalid-image handling, group-safe splitting
+ reliability reporting, research-only non-promotable artifacts, external/lab
never promotable, model-card research-only marking, anomaly no-auto-diagnosis,
**no change to production inference**, **no change to baseline comparison**, and
**tenant-scoped (no cross-tenant) research loading**. The real DINOv2 path is
covered by a torch-gated test (skipped where torch is absent).

Executed results are recorded in the PR description.

## Known limitations

- The **real DINOv2 benchmark is an environment/governance blocker**: no torch is
  installed here and no DINOv2 checkpoint is approved/rights-cleared, so only the
  deterministic stub path runs. The code path is complete and governed for when an
  isolated research environment with an approved checkpoint is available.
- The stub embedder is a smoke device, not science; stub-vs-baseline metrics are
  pipeline evidence only, not a model comparison.
- No anomaly-localization prototype was trained (awaiting permitted data).

## Stage 5B readiness

Ready to proceed to Stage 5B (localization research) once: (1) an isolated torch
research environment is provisioned; (2) a DINOv2 checkpoint is license/rights
verified and approved in the registry with its digest; (3) a governed set of
NORMAL instrument images (and any permitted external stainless-steel data) is
cleared. First 5B step: a **PaDiM** normal-only anomaly baseline via Anomalib on
that data, outputs research-only with retained uncertainty — never auto-diagnosed.
