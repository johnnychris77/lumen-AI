# LPZ-DIR-009 — Model Promotion Standard

**Purpose:** define the promotion stages a candidate model passes through and the
gates between them, so advancement is evidence-based, attributable, and
fail-closed. Promotion is a **governance** progression — reaching a later stage is
**not** clinical deployment, which remains out of scope.

## Stages

```
Experimental → Candidate → Technically Validated → Pilot Eligible →
Clinical Validation Candidate → Production Candidate → Retired
```

Implemented mapping (`candidate_promotion.CANDIDATE_STAGES` =
`Experimental → Candidate → Validated Candidate → Pilot → Production`): "Technically
Validated" ≈ `Validated Candidate`; "Pilot Eligible" ≈ `Pilot` entry; "Clinical
Validation Candidate" and "Production Candidate" refine `Production` into governed
sub-gates; "Retired" is a terminal status. Advancement is one step at a time.

## Per-stage definition

### Experimental
* **Entry:** a registered model from a governed experiment.
* **Exit:** evaluation complete + model card started.
* **Approval authority:** author/owner.
* **Evidence:** registry entry, reproducibility recorded.
* **Restrictions:** internal only; not a reference for anything.

### Candidate
* **Entry:** complete evaluation on the sealed test set.
* **Exit:** independent technical review scheduled.
* **Approval authority:** owner + reviewer.
* **Evidence:** evaluation metrics, calibration, error analysis.
* **Restrictions:** no pilot use.

### Technically Validated (`Validated Candidate`)
* **Entry:** independent technical review **passed**; reproducibility confirmed.
* **Exit:** governance review complete.
* **Approval authority:** independent Technical Reviewer (≠ author).
* **Evidence:** `reproducible_training_confirmed`, `error_analysis_reviewed`,
  stratified evaluation, model card complete.
* **Restrictions:** still not clinical; governance state only.

### Pilot Eligible (`Pilot`)
* **Entry:** governance review complete; human-review requirements defined.
* **Exit:** decision to enter a governed pilot (separate directive).
* **Approval authority:** AI Governance Lead + owner.
* **Evidence:** full validation package + governance sign-off + rollback reference.
* **Restrictions:** **not** clinical deployment; pilot is shadow/advisory,
  human-supervised, under its own authorized directive.

### Clinical Validation Candidate
* **Entry:** a governed pilot/validation directive is authorized.
* **Exit:** clinical-validation evidence assembled (that directive's remit).
* **Approval authority:** clinical governance (separate directive).
* **Evidence:** prospective validation evidence (out of scope here).
* **Restrictions:** advisory, human-in-the-loop; no autonomous decisions.

### Production Candidate
* **Entry:** clinical-validation evidence accepted (future directive).
* **Exit:** production-readiness decision (future directive).
* **Approval authority:** executive + clinical + security governance.
* **Evidence:** the full body from prior stages.
* **Restrictions:** **out of scope for Directive 009**; reserved.

### Retired
* **Entry:** withdrawn (superseded, drift, defect, policy).
* **Exit:** terminal.
* **Approval authority:** AI Governance Lead.
* **Evidence:** reason + rollback/preservation record.
* **Restrictions:** not used; retained for audit (`MODEL_ROLLBACK_STANDARD.md`).

## Promotion rules

1. **One step at a time**; no skipping stages.
2. **Evidence-gated and fail-closed:** each gate requires its recorded evidence;
   missing evidence blocks promotion.
3. **Separation of duties:** the Technical Reviewer and approvers are not the model
   author.
4. **Attributable + audited:** every promotion records who, when, and the evidence.
5. **No deployment by promotion:** Pilot Eligible and beyond are governance states;
   clinical use requires a separate authorized directive.
6. **Reversible:** every promoted model carries a rollback reference.

## Governance note (existing system)

`candidate_promotion` implements the 5-stage ladder with checklist gates,
shadow-evidence requirements for `Validated Candidate`/`Pilot`/`Production`, and a
pilot-evidence requirement for `Production`; `model_promotion` evaluates full
readiness. Governance additions recorded for a future authorized change: expand the
ladder to name "Technically Validated / Pilot Eligible / Clinical Validation
Candidate / Production Candidate / Retired" explicitly and bind each gate's
evidence + separation-of-duties in code. No code is changed under this directive.
