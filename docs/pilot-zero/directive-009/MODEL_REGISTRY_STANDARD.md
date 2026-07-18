# LPZ-DIR-009 — Candidate Model Registry Standard

**Purpose:** define the **Candidate Model Registry** — the authoritative,
auditable record of every candidate vision model, its provenance, and its status.
A model that is not registered does not exist for governance purposes.

## Required registry fields (per model)

| Field | Meaning | System mapping |
|---|---|---|
| **Model UUID** | Permanent, immutable identity | `ModelRegistryEntry.model_id` |
| **Model Name** | Human-readable name | model name |
| **Version** | Major.minor.patch | `model_version` (`MODEL_VERSIONING_STANDARD.md`) |
| **Architecture** | Architecture used | `architecture` |
| **Training Dataset** | Frozen dataset version trained on | `dataset_version` / `dataset_version_id` |
| **Validation Dataset** | Validation partition/version | dataset lineage (Directive 008) |
| **Ground Truth Version** | GT version underlying the data | dataset lineage |
| **Experiment UUID** | The experiment that produced it | experiment link |
| **Owner** | Accountable owner | owner / `reviewer` |
| **Approval Status** | Draft / approved / rejected | `approval_status`, `approved_by` |
| **Validation Status** | Evaluated / calibration / error-analysis done | `evaluation_metrics`, `calibration_report`, `error_analysis_report` |
| **Release Status** | Stage (Experimental…Retired) / deployment | `candidate_stage`, `deployment_status` |
| **Checksum** | Artifact integrity | `artifact_checksum` |
| **Training Date** | When trained | `training_date` |

Supporting recorded fields already present: `framework`, `git_commit`,
`hyperparameters`, `preprocessing_version`, `training_run_id`, `known_limitations`,
`model_card_markdown`, and the governance flags (`documentation_complete`,
`reproducible_training_confirmed`, `error_analysis_reviewed`,
`governance_review_completed`, `metrics_approved`, `clinical_review_complete`).

## Registry rules

1. **Register before advancing.** No model may be reviewed, promoted, or referenced
   until it has a registry entry with the required fields.
2. **Artifact integrity.** Every entry records an `artifact_checksum`; the artifact
   is verifiable and immutable for that version.
3. **Lineage complete.** Each entry links its experiment, training/validation
   dataset versions, and Ground Truth version — traceable to the evidence chain.
4. **Attributable status.** Approval, validation, and release status changes are
   attributable and audited.
5. **Immutable versions.** A registered version is frozen; changes create a new
   version (`MODEL_VERSIONING_STANDARD.md`).
6. **Model card required.** Each entry carries a model card documenting purpose,
   data, evaluation methodology, limitations, and human-review requirements.
7. **No deployment implied.** Registration and even "Pilot Eligible" status are
   **governance states**, not clinical deployment (which is out of scope).

## Registry integrity (expected outcome)

The registry can, for any model, produce: its full lineage (experiment → dataset →
GT), its artifact checksum (verifiable), its evaluation/calibration/error-analysis
records, its stage and approval history, and its model card. A missing or
unverifiable field blocks promotion — fail-closed.

## Governance note (existing system)

`ModelRegistryEntry` already implements the registry with model id/version/type,
architecture/framework/hyperparameters, dataset linkage, artifact path + checksum,
evaluation/calibration/error-analysis reports, model card, candidate stage, and
governance flags; `model_card` generates the card. Governance additions recorded
for a future authorized change: add an explicit **Experiment UUID** link and an
append-only approval/validation/release **history** sub-record. No code is changed
under this directive.
