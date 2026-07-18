# LPZ-DIR-009 — AI Architecture (Candidate Vision Models)

**Purpose:** define the logical architecture by which a governed Pilot Zero
dataset becomes a **trustworthy candidate vision model** — reproducible, version
controlled, traceable, scientifically documented, independently testable,
governed, auditable, and human-supervised. This is a **governance standard**, not
new software; each stage maps to the ML code already present in the repository so
the architecture is auditable against reality.

Guardrails (non-negotiable): **no production AI features, no deployment into
clinical workflows, no diagnostic-performance claim, no autonomous clinical
decision-making, no model training under this directive.** The objective is not
the *best* model — it is a *trustworthy* one.

## Logical flow

```
Dataset                 (readiness-certified, frozen — Directive 008)
   ▼
Training Pipeline       (reproducible: config + seed + software/hardware recorded)
   ▼
Experiment              (governed run: objective, versions, hyperparameters)
   ▼
Candidate Model         (artifact + checksum + model card)
   ▼
Validation              (evaluation protocols; calibration; error analysis)
   ▼
Technical Review        (independent reviewer; reproducibility confirmed)
   ▼
Approval                (governed approval; separation of duties)
   ▼
Registry                (Candidate Model Registry entry, versioned)
   ▼
Pilot Eligible Model    (governance gate passed; NOT clinical deployment)
   ▼
Future Production Candidate  (reserved — separate authorized directive)
```

## Stage responsibilities

| Stage | Responsibility | System mapping |
|---|---|---|
| Dataset | Frozen, readiness-certified input | Directive 008; `DatasetVersion`, `dataset_version_id` |
| Training Pipeline | Reproducible training config | `ml.training_config`, `ml.candidate_training`, `ml.training_pipeline` |
| Experiment | Governed, fully-specified run | `EXPERIMENT_GOVERNANCE_STANDARD.md` (governance overlay) |
| Candidate Model | Artifact + checksum + card | `ModelRegistryEntry` (`artifact_path`, `artifact_checksum`, `model_card_markdown`) |
| Validation | Evaluation, calibration, error analysis | `ml.evaluation`, `ml.error_analysis`, `calibration_report` |
| Technical Review | Independent verification | `reviewer`, `reproducible_training_confirmed`, `error_analysis_reviewed` |
| Approval | Governed sign-off | `approval_status`, `approved_by`, `governance_review_completed` |
| Registry | Versioned model record | `ModelRegistryEntry` |
| Pilot Eligible | Governance gate (not clinical) | `candidate_stage` ("Pilot") |
| Future Production Candidate | Reserved | out of scope |

## Architectural principles

1. **Dataset-gated.** A model may only be trained from a **readiness-certified,
   frozen** dataset version (Directive 008). No ad-hoc data.
2. **Reproducible by construction.** Config, seed, software/hardware, git commit,
   and preprocessing version are recorded so a run can be reproduced and verified.
3. **Traceable end-to-end.** Every model links to its experiment, dataset version,
   Ground Truth version, and evaluation — back to the evidence chain.
4. **Independently testable.** Evaluation is defined as a **methodology** (no
   deployment thresholds) and runs on a sealed test partition.
5. **Human-supervised.** No stage is autonomous; approvals and reviews are
   attributable, and no model output is a clinical decision.
6. **Immutable artifacts.** A registered model version is frozen (checksum);
   changes create a new version.
7. **Fail-closed.** Missing reproducibility, evaluation, review, or lineage blocks
   promotion — it never silently advances.

## Governance note (existing system)

The repository already implements this spine: `ModelRegistryEntry`, reproducible
`training_config`/`candidate_training`, pure-Python `evaluation`/`error_analysis`,
`model_card`, and the `candidate_promotion` ladder
(`CANDIDATE_STAGES = Experimental → Candidate → Validated Candidate → Pilot →
Production`) with checklist gates and shadow/pilot evidence requirements. This
architecture **governs** those pieces as one trustworthy-model pipeline; it adds
no code under this directive. Gaps and a migration plan are in
`DIRECTIVE_009_REPORT.md`.
