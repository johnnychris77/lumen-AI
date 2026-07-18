# LPZ-DIR-009 — AI Governance Standard

**Purpose:** define the cross-cutting governance every candidate vision model is
subject to across its lifecycle — from experiment to retirement — so models remain
trustworthy, transparent, and human-supervised.

Guardrail: nothing here authorizes production AI, clinical deployment, a
diagnostic-performance claim, or autonomous clinical decision-making. AI is
decision **support**, always human-supervised.

## Governance requirements

### Human review
* Every model output that informs an action is reviewed by a qualified human.
* Contamination-, damage-, and safety-relevant outputs **fail closed** to human
  (and, where defined, supervisor) review.
* Models may rank/highlight/pre-populate; they may **not** finalize a clinical
  decision. Expert judgment is the authority.

### Transparency
* Each model discloses what it is, its family, its training dataset version, its
  intended use, and its limitations (via the model card).
* Any AI-assisted output is labeled as such at the point of use, and its
  confidence is presented as **model** confidence, distinct from reviewer
  confidence.

### Explainability
* Each candidate model provides governed explanation evidence appropriate to its
  family (e.g., region of interest, contributing features), recorded with the
  output — never a fabricated rationale.
* Explanations support review; they are not a performance claim.

### Bias monitoring
* Performance is reported **stratified** (instrument family, manufacturer, image
  quality) so systematic gaps are visible (`MODEL_EVALUATION_STANDARD.md`).
* Material disparities are documented and are a governance trigger.

### Drift monitoring
* A model in a governed pilot is monitored for input/performance drift against its
  evaluation baseline; drift beyond a governed bound triggers review and possible
  rollback (`MODEL_ROLLBACK_STANDARD.md`).

### Performance monitoring
* Ongoing performance (in a governed pilot) is recorded and compared to the
  model's evaluation record; anomalies trigger review. No monitoring result is a
  clinical guarantee.

### Model retirement
* A model is retired on supersession, sustained drift, a discovered defect, or
  policy; retirement is attributable, reasoned, and preserves history
  (`MODEL_PROMOTION_STANDARD.md`, `MODEL_ROLLBACK_STANDARD.md`).

### Dataset dependencies
* Each model records its **frozen** training/validation dataset versions
  (Directive 008); a change in those datasets requires a new model version.

### Ground Truth dependencies
* Each model records the **Ground Truth version** underlying its data (Directive
  006); GT correction/supersession is tracked and may require re-validation.

### Digital Twin dependencies
* Baseline-comparison and instrument models record the **Digital Twin / baseline
  versions** they depend on (Directive 007); changes are tracked.

### Evidence preservation
* Experiment, dataset lineage, evaluation, approvals, monitoring, and rollback
  records are preserved immutably and are reconstructable for audit.

## Roles (governance)

| Role | Responsibility |
|---|---|
| Model Owner | Accountable for the model across its lifecycle |
| Technical Reviewer | Independent validation + reproducibility (≠ author) |
| AI Governance Lead | Approves promotion/retirement; owns governance policy |
| Clinical Governance | (Future directives) clinical-validation decisions |
| Quality Auditor | Read-only audit of the above |

Separation of duties: the author does not approve, validate, or govern their own
model.

## Fail-closed principle

Missing human review, explainability evidence, lineage, monitoring, or approval
**blocks** advancement and use. Ambiguity escalates to a human; it never
auto-advances and never becomes an autonomous decision.

## Governance note (existing system)

`ModelRegistryEntry` carries governance flags (`governance_review_completed`,
`reproducible_training_confirmed`, `error_analysis_reviewed`,
`clinical_review_complete`, `known_limitations`, model card), and the
shadow/drift/monitoring services (`ml.shadow_error_review_queue`, drift/monitoring
from the Shadow/Advisor work) plus `guardianx_model_governance_service` provide
monitoring substrate. Governance additions recorded for a future authorized
change: bind stratified bias reporting, drift bounds, and evidence-preservation
into one governance record per model, and enforce human-review/SoD gates in code.
No code is changed under this directive.
