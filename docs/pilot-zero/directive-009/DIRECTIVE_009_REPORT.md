# LPZ-DIR-009 — Directive Report: Candidate Vision Model Framework & AI Governance

## Executive summary

Directive 009 establishes the engineering, governance, lifecycle, validation, and
promotion **framework** for Candidate Vision Models developed from Pilot Zero
datasets. It delivers ten standards (AI architecture, model families, experiment
governance, model registry, versioning, evaluation, promotion, rollback, AI
governance, and this report), each grounded in the ML code already present in the
repository so the framework is auditable against reality.

Every model governed by this framework is **reproducible, version controlled,
fully traceable, scientifically documented, independently testable, governed,
auditable, and human-supervised**. The objective is not the best model — it is a
**trustworthy** one. This directive is **governance and documentation only**: no
production AI features, no deployment into clinical workflows, no
diagnostic-performance claim, no autonomous clinical decision-making, and **no
model training**. No application code was modified.

## AI architecture

`AI_ARCHITECTURE.md` defines Dataset → Training Pipeline → Experiment → Candidate
Model → Validation → Technical Review → Approval → Registry → Pilot Eligible Model
→ Future Production Candidate (reserved), with principles: dataset-gated,
reproducible-by-construction, traceable, independently testable, human-supervised,
immutable artifacts, fail-closed.

## Model families

`MODEL_FAMILY_STANDARD.md` defines ten decision-support families (Image Quality,
Instrument/Tray Classification, Lumen Segmentation, Anatomical Region Detection,
Contamination Detection, Damage Detection, Baseline Comparison, Finding
Classification, Risk Prioritization) — each with purpose, inputs, outputs,
limitations, and **mandatory human review**; all advisory, Unknown-capable, and
never autonomous. Contamination/damage outputs fail closed to human review.

## Experiment governance

`EXPERIMENT_GOVERNANCE_STANDARD.md` requires Experiment UUID, research objective,
dataset/GT/baseline/Digital-Twin versions, architecture, hyperparameters, training
environment, seed, software/hardware, author, reviewer, results, and approval —
with reproducibility completeness, frozen-dataset input, pinned lineage,
independent review, and an append-only record.

## Registry

`MODEL_REGISTRY_STANDARD.md` defines the Candidate Model Registry (Model UUID,
name, version, architecture, training/validation datasets, GT version, experiment
UUID, owner, approval/validation/release status, checksum, training date, plus
model card and governance flags) with register-before-advancing, artifact
integrity, complete lineage, immutable versions, and "no deployment implied".

## Versioning

`MODEL_VERSIONING_STANDARD.md` defines major/minor/patch semantics, parent model,
pinned training-dataset and Ground-Truth versions, evaluation version, approval
history, retirement status, and rollback reference — append-only, never
overwritten, historical versions retrievable.

## Evaluation

`MODEL_EVALUATION_STANDARD.md` defines the evaluation **methodology** (precision,
recall, sensitivity, specificity, F1, calibration, confusion matrix, ROC, AUC,
FP/FN analysis, performance by instrument family/manufacturer/image quality,
Unknown rate) on the sealed test partition — **no deployment thresholds**, honest
uncertainty, no performance claim, reproducible.

## Promotion

`MODEL_PROMOTION_STANDARD.md` defines Experimental → Candidate → Technically
Validated → Pilot Eligible → Clinical Validation Candidate → Production Candidate →
Retired, with per-stage entry/exit criteria, approval authority, evidence, and
restrictions — one step at a time, evidence-gated, fail-closed, separation of
duties, and **no deployment by promotion** (mapping onto the implemented 5-stage
`CANDIDATE_STAGES` ladder).

## Rollback

`MODEL_ROLLBACK_STANDARD.md` defines immediate rollback, historical retrieval,
previous-version restoration, audit preservation, performance history, and reason
for rollback — supersede-never-delete, checksum-verified restore, human-decided,
trigger-ready (drift/error-spike/defect/policy).

## AI governance

`AI_GOVERNANCE_STANDARD.md` defines human review, transparency, explainability,
bias monitoring, drift monitoring, performance monitoring, model retirement,
dataset/Ground-Truth/Digital-Twin dependencies, and evidence preservation — with
governance roles, separation of duties, and a fail-closed principle. AI is
decision support, always human-supervised.

## Validation procedures (test requirements) & expected outcomes

Documentation-only directive — these are the validation procedures a future
authorized implementation change must satisfy. No tests were added or modified.

| # | Validates | Procedure (future) | Expected outcome |
|---|---|---|---|
| 1 | Experiment registration | Register an experiment missing seed/dataset version. | Rejected; reproducibility fields required. |
| 2 | Model registration | Register a model without an artifact checksum or lineage. | Rejected; registry integrity enforced. |
| 3 | Version creation | Modify a released model version. | Rejected; a new version is required (immutability). |
| 4 | Promotion workflow | Promote skipping a stage or as the model's author. | Rejected; one-step + separation-of-duties + evidence gates. |
| 5 | Rollback | Trigger rollback on a model in a governed pilot. | Prior version restored; checksum verified; both versions + reason retained in audit. |
| 6 | Evaluation reproducibility | Re-run evaluation on the same model version + test partition. | Identical metrics reproduced. |
| 7 | Dataset linkage | Register a model against a non-frozen/uncertified dataset. | Rejected; frozen readiness-certified dataset required (Directive 008). |
| 8 | Ground Truth linkage | Resolve a model to its Ground Truth version. | GT version returned; lineage complete. |
| 9 | Registry integrity | Retrieve lineage/checksum/evaluation for any model. | All present and verifiable; missing/unverifiable blocks promotion. |

## Existing-system gap analysis & migration plan

The repository already implements much of this: `ModelRegistryEntry` (model
id/version/type, architecture/framework/hyperparameters, dataset linkage, artifact
path + checksum, evaluation/calibration/error-analysis reports, model card,
candidate stage, governance flags); services `ml.training_config`,
`ml.candidate_training`, `ml.training_pipeline`, `ml.evaluation`,
`ml.error_analysis`, `ml.model_card`, `ml.candidate_promotion`
(`Experimental → Candidate → Validated Candidate → Pilot → Production`),
`ml.model_promotion`, and `guardianx_model_governance_service`.

| Gap | Current state | Migration step (future) | Priority |
|---|---|---|---|
| First-class Experiment record | Training run id + config | Add Experiment UUID binding all governance fields + pinned lineage | High |
| Frozen-dataset precondition | dataset linkage referenced | Enforce readiness-certified frozen dataset at experiment/registration | High |
| Separation of duties in code | Reviewer field exists | Block author == reviewer/approver of same model | High |
| Rollback reference + event | Versioned entries + checksum | Add rollback pointer + checksum-verified restore + rollback event | High |
| Pinned GT/baseline/eval versions | ids referenced | Pin GT, baseline, and evaluation **versions** into each model version | Medium |
| Stage naming | 5-stage ladder | Expand to the 7 named stages incl. Retired | Low |
| Stratified bias reporting | metrics computed | Standardize stratified-by-family/manufacturer/quality output | Medium |
| Governance record | flags scattered on entry | Bind human-review/drift/monitoring/evidence into one governance record | Medium |

**No migration step is executed under Directive 009.** Each is a candidate for a
future directive that explicitly authorizes code changes. Per the directive's
constraint, **no model was trained** — the existing ML machinery is governed, not
extended.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Non-reproducible experiment | Untrustworthy model | Experiment governance + reproducibility gate |
| Model from uncertified data | Untrustworthy model | Frozen readiness-certified dataset precondition (Directive 008) |
| Deployment thresholds set prematurely | False assurance | Evaluation is methodology only; no thresholds; no performance claim |
| Self-approval | Weak validation | Separation of duties (planned code enforcement) |
| Model used autonomously in clinical flow | Safety/governance breach | Human-supervised, decision-support-only, fail-closed; deployment out of scope |
| Undetected drift/bias | Degraded trust | Drift + stratified bias monitoring; rollback triggers |
| Scope creep into production/clinical AI | Violates directive & freeze | Reserved layers; non-goals restated in every doc |

## Dependencies

* **Program:** Directives 001, 002, 004, 005, 006, 007, 008 (all complete).
* **System:** the model registry, training/evaluation/error-analysis/model-card
  services, promotion ladder, and monitoring services above; frozen datasets
  (Directive 008); GT (006); baselines/twins (007).
* **Personnel:** model owners, independent technical reviewers, AI Governance Lead,
  quality auditors — with separation of duties.

## Acceptance criteria

All ten deliverables exist under `docs/pilot-zero/directive-009/`, are internally
consistent and vendor-neutral, make no diagnostic-performance claim, keep models
decision-support-only and human-supervised, set no deployment thresholds, enforce
reproducibility/immutability/lineage, and include validation procedures with
expected outcomes plus an honest gap analysis. **Met.**

## Exit criteria (to develop candidate models under this framework — future work)

1. First-class Experiment record + frozen-dataset precondition enforced in code.
2. Separation-of-duties (author ≠ reviewer/approver) enforced.
3. Rollback reference + checksum-verified restore + rollback event implemented.
4. Pinned GT/baseline/evaluation versions per model version.
5. Validation procedures 1–9 implemented and passing on a clean database.

## Completion status

**LPZ-DIR-009 Candidate Vision Model Framework & AI Governance: COMPLETE
(documented).** The framework is defined, grounded in the existing system, and
accompanied by a migration plan and validation procedures. **Code enforcement of
the migration steps is NOT started (by design — deferred to a future authorized
directive).** No model was trained or deployed, no deployment threshold was set,
and no diagnostic or clinical-performance claim is made.
