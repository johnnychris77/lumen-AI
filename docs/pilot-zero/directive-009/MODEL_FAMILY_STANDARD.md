# LPZ-DIR-009 — Model Family Standard

**Purpose:** define the supported categories of candidate vision model, each with
its purpose, inputs, outputs, limitations, and **human review requirements**.
Defining a family here does **not** authorize training or deployment — it sets the
governance envelope a future, separately-authorized model must live within.

Guardrail: every family below is **decision-support only**, human-supervised, and
carries **no diagnostic-performance claim**. Outputs are advisory candidates for
human confirmation, never autonomous clinical decisions.

## Common requirements (all families)

* **Inputs** are governed Pilot Zero images + metadata (Directives 005–008).
* **Outputs** are advisory: a prediction plus an honest uncertainty/Unknown path.
* **Human review is mandatory** before any output informs an action.
* **Unknown is a valid output** — a family must be able to abstain rather than
  force a class.
* **Limitations** are documented in the model card and surfaced at use.

## Families

### Image Quality Assessment
* **Purpose:** score whether an image is adequate for downstream use.
* **Inputs:** image + capture metadata. **Outputs:** quality band + reasons.
* **Limitations:** quality ≠ cleanliness; poor score routes to re-capture.
* **Human review:** reviewer confirms borderline/reject cases.

### Instrument Classification
* **Purpose:** propose the instrument family/type shown.
* **Inputs:** image (+ identity context). **Outputs:** candidate class + confidence.
* **Limitations:** never a substitute for governed identity (UDI/barcode).
* **Human review:** identity must be confirmed, not inferred.

### Tray Classification
* **Purpose:** propose tray/set membership.
* **Inputs:** image/context. **Outputs:** candidate tray + confidence.
* **Limitations:** advisory grouping only.
* **Human review:** confirmation required before use.

### Lumen Segmentation
* **Purpose:** localize lumen/interior regions.
* **Inputs:** image. **Outputs:** region mask (candidate).
* **Limitations:** segmentation quality bounded by image quality/coverage.
* **Human review:** reviewer validates masks used as evidence.

### Anatomical Region Detection
* **Purpose:** locate engineering regions (tip/hinge/serration/lumen).
* **Inputs:** image. **Outputs:** region boxes/points (candidate).
* **Limitations:** engineering regions of the instrument, not patient anatomy.
* **Human review:** required for evidence use.

### Contamination Detection
* **Purpose:** flag apparent residual/contamination for review.
* **Inputs:** image (+ baseline context). **Outputs:** candidate finding + region.
* **Limitations:** **absence of a flag is not evidence of cleanliness**; bounded
  by identity/coverage/quality (see comparison safety invariant, Directive 007).
* **Human review:** **mandatory**; contamination-relevant outputs fail closed to
  human/supervisor review.

### Damage Detection
* **Purpose:** flag apparent damage (corrosion/pitting/scratches/cracks).
* **Inputs:** image. **Outputs:** candidate finding + region.
* **Limitations:** appearance-only; severity is not a risk claim.
* **Human review:** mandatory for any flagged damage.

### Baseline Comparison
* **Purpose:** compare an inspection image to an approved baseline (Directive 007).
* **Inputs:** image + approved baseline version. **Outputs:** deviation candidate.
* **Limitations:** governed by the baseline comparison standard; advisory only.
* **Human review:** expert judgment is the authority; AI may assist, not finalize.

### Finding Classification
* **Purpose:** propose a controlled-taxonomy finding label (Directive 006).
* **Inputs:** image/region. **Outputs:** candidate taxonomy term + confidence.
* **Limitations:** must support Unknown; never forces a class.
* **Human review:** confirmation required; feeds annotation, not Ground Truth
  directly.

### Risk Prioritization
* **Purpose:** order items for human attention (triage support).
* **Inputs:** governed features/outputs. **Outputs:** priority ordering (advisory).
* **Limitations:** prioritization ≠ decision; never suppresses a required review.
* **Human review:** humans decide; the model only orders the queue.

## Governance note (existing system)

`ModelRegistryEntry.model_type` already keys models by task, and existing services
(quality assessment, similarity/baseline comparison, error analysis) cover several
of these families as decision support with human oversight. This standard defines
the **governance envelope** per family; it authorizes no new family and trains no
model. A future authorized change may register a `model_family` vocabulary and
per-family human-review policy.
