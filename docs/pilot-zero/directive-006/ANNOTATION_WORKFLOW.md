# LPZ-DIR-006 — Annotation Workflow

**Purpose:** define the end-to-end lifecycle by which a raw inspection image
becomes a governed **Ground Truth** record eligible for future dataset use.
This is a **governance standard**, not new software. Where the standard names a
mechanism, the mapping to the system already in the repository is stated so the
document is auditable against reality (see the gap notes at the end).

Scope guardrails (non-negotiable): no new product functionality, no AI model
training, no hospital deployment workflow, and no regulatory or clinical
performance claim is created by this document. "Ground Truth" here means the
highest-trust **human-approved** representation of an inspected image, produced
only through the approved review workflow below.

## Lifecycle

```
Raw Image
   │  (governed capture, Directive 005 metadata present)
   ▼
Quality Verification ──── reject ──▶ Quarantine (not annotated; logged)
   │  pass
   ▼
Primary Annotation
   │  attributable, evidence-based, version 1 created
   ▼
Secondary Review  (independent reviewer ≠ primary)
   │
   ├── agree ─────────────────────────────────┐
   │                                           │
   └── disagree ─▶ Disagreement Resolution     │
                     (consensus / third        │
                      reviewer / expert panel / │
                      Unable to Determine /     │
                      Rejected)                 │
                        │  resolved             │
                        ▼                       ▼
                 Ground Truth Candidate ◀───────┘
                        │
                        ▼
                 Expert Approval  (Ground Truth Approver; separation of duties)
                        │  approve                 │ reject / return
                        ▼                          ▼
                 Ground Truth Record        back to annotation/review
                 (immutable version)        (new version, reason logged)
                        │
                        ▼
                 Dataset Eligibility  (curator selects; GT never mutated)
```

## Stage definitions

### 1. Raw Image
An acquired inspection image with complete acquisition provenance (Directive
005). No annotation begins until the image is registered with an instrument
identity and integrity hash. *System:* `Annotation.retained_image_id`,
`digital_twin_id`, `inspection_id`.

### 2. Quality Verification
A gate, not a formality. The image is scored against the controlled quality
vocabulary (`Excellent / Good / Marginal / Poor / Reject`). **Reject** images are
quarantined and never annotated for Ground Truth; the decision is logged with a
reason. A **Poor/Marginal** image may still be annotated but the limitation is
recorded (it constrains achievable confidence). *System:*
`Annotation.image_quality`, `IMAGE_QUALITY_LEVELS`.

### 3. Primary Annotation
The Primary Annotator records observations using the controlled taxonomy
(`ANNOTATION_TAXONOMY.md`), region, severity, location, evidence references, and
**reviewer confidence** (not AI certainty). Uncertain findings are recorded as
**Unknown** — annotators are never forced to guess. Creating the annotation
writes **version 1** and an immutable version snapshot. *System:*
`annotation_service.create_annotation`, `Annotation`, `AnnotationVersion`,
state `UNLABELED → LABELED`.

### 4. Secondary Review
An **independent** reviewer (never the primary annotator — separation of duties)
assesses the annotation. Before submitting, the reviewer sees only what blind
review permits (they do not see the primary's label first). *System:*
`annotation_blind_review_service`, `annotation_review_service`,
`AnnotationReview.secondary_*`, state `LABELED → SECOND_REVIEW`.

### 5. Disagreement Resolution (conditional)
Entered only when primary and secondary disagree. Outcomes: **Agreement,
Consensus Review, Third Reviewer, Expert Panel, Unable to Determine, Rejected**
(`DISAGREEMENT_RESOLUTION_STANDARD.md`). Every escalation and decision is
recorded with evidence preserved. *System:* state `SECOND_REVIEW → DISAGREEMENT
→ ADJUDICATED`, `AnnotationReview.adjudicator / resolution /
adjudication_reason`.

### 6. Ground Truth Candidate
An annotation that has cleared review (agreement or resolved disagreement) is a
**candidate**. It is not yet Ground Truth. *System:* review resolved,
`review_status = APPROVED` reachable; `ground_truth_status = DRAFT`.

### 7. Expert Approval
A **Ground Truth Approver** (distinct authority; may not approve their own
annotation or review) confirms the candidate against the evidence and the
guidelines. Approval is attributable and timestamped. Rejection returns the item
to annotation/review as a **new version** with a recorded reason. *System:*
`annotation_ground_truth_service`, `promote-ground-truth`,
`ROLES_MAY_FINALIZE_GROUND_TRUTH`.

### 8. Ground Truth Record
On approval, an **immutable** Ground Truth version is created:
`DRAFT → ACTIVE`. **No Ground Truth version is ever overwritten or deleted** —
any later change supersedes it with a new version and full history
(`GROUND_TRUTH_GOVERNANCE.md`). *System:* `GROUND_TRUTH_ACTIVE`,
`ground_truth_version`, `AnnotationVersion` chain.

### 9. Dataset Eligibility
A Dataset Curator may select `ACTIVE` Ground Truth records into a dataset. This
directive stops here: it does **not** build training datasets or compute model
metrics. Export selects, it never mutates Ground Truth. *System:*
`annotation_export_service` (ACTIVE-only), `dataset_version_id` linkage.

## Invariants (every stage)

* **Attributable** — every action names an actor and time.
* **Reproducible** — the taxonomy + guidelines make the same image yield the
  same governed outcome across reviewers.
* **Reviewable** — nothing becomes Ground Truth without independent review.
* **Version controlled** — every change writes an immutable version; history is
  never overwritten (`ANNOTATION_VERSIONING_STANDARD.md`).
* **Evidence based** — each observation references the image region / baseline
  evidence supporting it.
* **Auditable** — the full chain (capture → quality → annotation → review →
  resolution → approval → GT → dataset) is reconstructable from the audit trail.
* **Fail-closed** — missing identity, missing evidence, or an unmet review step
  blocks promotion; it never silently passes.

## Alignment with the existing system (honest mapping)

The repository already implements most of this lifecycle (models
`Annotation` / `AnnotationVersion` / `AnnotationReview`; services
`annotation_service`, `annotation_review_service`,
`annotation_ground_truth_service`, `annotation_blind_review_service`,
`annotation_analytics_service`, `annotation_export_service`; routes under
`/annotations`). Governance gaps this directive records for a future,
separately-authorized change (**documentation only here**):

1. **Taxonomy is not yet a hard constraint** — `primary_observation` is a free
   string; `ANNOTATION_TAXONOMY.md` defines the controlled vocabulary a future
   validation layer should enforce.
2. **Confidence is stored numerically** — the qualitative reviewer-confidence
   bands in `ANNOTATION_CONFIDENCE_STANDARD.md` are a governance overlay on the
   existing float fields.
3. **Role names** — the directive's nine governance roles map onto six
   implemented role strings; `ANNOTATION_ROLES_AND_RESPONSIBILITIES.md` records
   the mapping and the separation-of-duties rules to enforce.

These are captured as a migration plan in `DIRECTIVE_006_REPORT.md`; no code is
changed under this directive.
