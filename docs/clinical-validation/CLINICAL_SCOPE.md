# LumenAI — Clinical Scope

**Clinical Validation Program · Phase 3: Florence · Clinical Review, Scientific Validation & Patient Safety Assurance**

This document states plainly what LumenAI does and does not do clinically, grounded in what the code actually implements today — not in aspirational or planned capability. Where current capability is narrower than documentation elsewhere implies, that gap is stated here rather than smoothed over.

## Intended clinical purpose

LumenAI is a decision-**support** tool for sterile processing department (SPD) instrument reprocessing. It assists a human technician/supervisor by surfacing visual evidence of possible contamination or damage on a reprocessed surgical instrument, alongside a confidence signal and (where evidence is insufficient) an explicit statement that a conclusion should not be drawn. It does not diagnose patients, does not detect pathogens (`docs/clinical/clinical-performance-report.md` states this explicitly — "LumenAI detects visual evidence of contamination... but does not detect specific pathogens"), and does not make an irreversible clinical or operational decision autonomously (verified in `PRODUCTION_READINESS_SCORECARD.md`/`HUMAN_OVERSIGHT_MODEL.md` — every gated transition requires a tier-checked human role).

## Intended users

The real, enforced role set is `admin`, `spd_manager`, `operator`, `viewer`, and `vendor_user` (`app/tenant_authz.py`). See [HUMAN_OVERSIGHT_MODEL.md](./HUMAN_OVERSIGHT_MODEL.md) for how these map (only partially) onto the informal "Technician/Supervisor/Manager/Director/Quality/Manufacturer" hierarchy clinical stakeholders may expect.

## Intended workflow

LumenAI is designed to sit inside the inspection step of a broader SPD reprocessing cycle, producing a scored recommendation that a human (supervisor or above, depending on risk) reviews before the instrument proceeds. See [HUMAN_OVERSIGHT_MODEL.md](./HUMAN_OVERSIGHT_MODEL.md) §Workflow Stage Coverage for exactly which of the 8 classically-named SPD stages (receiving → cleaning → inspection → assembly → packaging → pre-sterilization review → supervisor review → release) have a real, tracked equivalent in code today, and which are descriptive labels only.

## Supported environments

- Multi-tenant SaaS deployment with per-tenant data isolation (`tenant_authz.require_tenant_roles`).
- 112 named instrument families as of the v1.10 knowledge expansion (`docs/instrument-knowledge/v1.10-instrument-knowledge-expansion.md`), spanning general surgery, orthopedics, neurosurgery, ENT, ophthalmology, cardiothoracic/vascular, urology/gynecology, plastics/microsurgery, podiatry/dental, and minimally-invasive/laparoscopic instrumentation. See [INSTRUMENT_TAXONOMY.md](./INSTRUMENT_TAXONOMY.md) for the full inventory and honest gap list.
- A 6-category anatomy-zone taxonomy with per-zone risk/rationale metadata. See [ANATOMY_REFERENCE.md](./ANATOMY_REFERENCE.md).

## Unsupported environments and known limitations — stated plainly

- **No trained model weights ship in this repository.** `app/ai/inference.py` falls back to a deterministic placeholder (`_deterministic_fallback()`) unless a real YOLO model file is present at deploy time. That fallback only ever emits `debris`, `corrosion`, plus non-finding placeholders `stain`/`clean` — it does **not** produce the fuller 12-13 category finding taxonomy (rust, pitting, wear, discoloration, missing_component, etc.) that exists in the scoring/education layer. Any clinical scope claim about what LumenAI "detects" must distinguish the deployed model's actual behavior from the taxonomy the platform is *designed* to score once a real model is trained and deployed. See [FINDING_TAXONOMY.md](./FINDING_TAXONOMY.md).
- **Osteotomes are not modeled anywhere in the codebase** — no anatomy family, keyword match, test fixture, or documentation reference exists for this instrument family, despite being a commonly-expected orthopedic instrument. See [INSTRUMENT_TAXONOMY.md](./INSTRUMENT_TAXONOMY.md).
- **Anatomy-zone resolution is an explicitly placeholder-grade heuristic** (`instrument_zones.py`'s own docstring: "NOT pixel-level localization"), with confidence capped at 0.7 — it is a keyword/substring match to a probable zone, not true image-region localization.
- **Pre-market clinical performance data is mock/synthetic**, and the planned multi-site blinded reader study (`docs/clinical/clinical-validation-plan.md`) has not yet been conducted — current sensitivity/specificity/kappa figures cited elsewhere in the documentation set are targets and simulated figures, not completed real-world results. See [CLINICAL_VALIDATION_PLAN.md](./CLINICAL_VALIDATION_PLAN.md).
- **No FDA clearance or regulatory approval is claimed anywhere** (a non-negotiable constraint in this repository's `CLAUDE.md`, independently verified by this review — the codebase's own regulatory-tracking service explicitly refuses to fabricate FDA submission status when no real submission record exists).
- **Root-cause categorization is deliberately human-only**, never AI-inferred (`app/models/root_cause.py`: "guessing 'why' a finding occurred without a human judgment would be a fabricated causal claim").
- **Oracle's research hypotheses remain outside production clinical guidance** at every stage short of its final, human-gated `PRODUCTION_KNOWLEDGE` stage (tier-2-or-above authorization plus recorded gate-check notes required) — an Oracle hypothesis is never itself a clinical recommendation.

## Lumen Decision Engine & Observation Doctrine (foundational update)

This scope statement is now formalized as the permanent operating
philosophy in `docs/clinical/LUMENAI_OBSERVATION_DOCTRINE.md`. In
particular: LumenAI observes probable visual findings, compares them
against a resolved baseline, applies the organization's own governed
policy, and recommends a next action — it does not make a lab-confirmed
identification or an autonomous, irreversible decision. Every observation
is reported using the probability-based taxonomy in
`app/services/observation_taxonomy.py` (e.g. "probable blood-like organic
residue," never "confirmed blood"), and supervisor review is
exception-based, not required for every inspection — see
`docs/decision-engine/SUPERVISOR_ESCALATION_MODEL.md`.

## Baseline Image Library (Project Atlas Sprint 1) — scope clarification

"Compares them against a resolved baseline," above, describes the
Decision Engine's *metadata*-level baseline resolution
(`BaselineLibraryEntry`), which was already real prior to this update. This
sprint (`docs/baseline-library/`) adds governed *image* evidence behind
that same baseline entry — a reviewed, hash-verified, version-controlled
image (or set of images, across anatomy zones/views) that a human can view
alongside an inspection. **It does not add image-based similarity scoring
to any clinical recommendation.** `image_similarity_service.py` (the real,
tested perceptual-hash comparator) is still not called from the live
per-inspection scoring path. Until a validated comparator is wired in and
independently confirmed, no clinical claim should describe LumenAI as
performing image-based baseline comparison — only image-evidence
governance (linking, review, activation, and compatibility/resolution
decisions that never produce a fabricated similarity number) is complete
as of this sprint.
