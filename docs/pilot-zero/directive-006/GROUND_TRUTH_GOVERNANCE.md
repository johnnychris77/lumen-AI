# LPZ-DIR-006 — Ground Truth Governance

**Purpose:** define what a Ground Truth record is, how it is created, and the
immutability and audit rules that make it the **highest-trust** representation
of an inspected image. Ground Truth is created **only** through the approved
review workflow (`ANNOTATION_WORKFLOW.md`) and only by a Ground Truth Approver
with the authority defined in `ANNOTATION_ROLES_AND_RESPONSIBILITIES.md`.

Guardrails: Ground Truth is a **human-approved** label. It is not an AI output,
carries no clinical or regulatory meaning, and this directive does not build
training datasets or compute performance metrics from it.

## Ground Truth record — required fields

| Field | Meaning | System mapping |
|---|---|---|
| **Ground Truth UUID** | Permanent, immutable identifier | `Annotation.ann_id` (`ANN-YYYY-NNNNNNNNN`) + GT version |
| **Image UUID** | The image the GT describes | `Annotation.retained_image_id` / `digital_twin_id` |
| **Annotation Version** | The annotation version approved | `Annotation.current_version` |
| **Review Version** | The review that supported approval | `AnnotationReview` (id + resolution) |
| **Approver** | Who approved (attributable) | GT finalizer identity |
| **Approval Timestamp** | When approved | version `created_at` |
| **Evidence References** | Region(s) + baseline evidence | `region_*`, `baseline_*` |
| **Confidence** | Reviewer confidence band | `ANNOTATION_CONFIDENCE_STANDARD.md` |
| **Decision** | The governed observation/outcome | `primary_observation` / resolution |
| **Status** | `DRAFT` → `ACTIVE` (→ superseded) | `ground_truth_status` |
| **Version History** | Full immutable chain | `AnnotationVersion` (append-only) |

## Creation rules

1. **Candidate first.** Only an annotation that has passed Secondary Review
   (agreement, or a resolved disagreement) may become a Ground Truth candidate.
2. **Separation of duties.** The approver may not have authored or reviewed the
   same annotation.
3. **Evidence-gated.** Approval requires evidence references; an annotation
   without evidence cannot be approved (fail-closed).
4. **Explicit approval.** `DRAFT → ACTIVE` occurs only on an explicit,
   attributable approval action — never automatically, never as a side effect.
5. **Unknown is approvable.** A well-evidenced `unknown_finding` /
   `unable_to_determine` is a valid Ground Truth outcome; the framework does not
   force a defect class to reach approval.

## Immutability rules (non-negotiable)

* **No overwrite.** A Ground Truth version is never edited in place and never
  deleted. `AnnotationVersion` is append-only.
* **Supersede, don't mutate.** A correction creates a **new** version that
  supersedes the prior one; the prior version remains in history, marked
  superseded, with the reason and actor recorded.
* **Traceable lineage.** Every version records its `previous_version_id`, editor,
  timestamp, and reason (`ANNOTATION_VERSIONING_STANDARD.md`).
* **Stable identity.** The Ground Truth UUID is permanent; versioning tracks
  change beneath a stable identifier.

## Status lifecycle

```
DRAFT ──approve──▶ ACTIVE ──supersede──▶ ACTIVE (new version)
                     │                       (prior kept, marked superseded)
                     └── retire (curator) ─▶ ARCHIVED  (nothing leaves ARCHIVED)
```

Only `ACTIVE` Ground Truth is dataset-eligible. Superseded and archived versions
remain in history for audit but are not selected into new datasets.

## Dataset eligibility (boundary of this directive)

A Dataset Curator may **select** `ACTIVE` Ground Truth into a dataset. Selection
never mutates the Ground Truth record. Building training datasets and computing
model performance metrics are **out of scope** for Directive 006 and require a
separate, explicitly-authorized directive.

## Audit requirements

Every Ground Truth transition emits an attributable audit event (actor, action,
timestamp, before/after status, reason). The full chain — capture → quality →
annotation → review → resolution → approval → Ground Truth → dataset selection —
must be reconstructable from the audit trail and version history.

## Governance note (existing system)

`annotation_ground_truth_service` + the `promote-ground-truth` route implement
`DRAFT → ACTIVE` behind `ROLES_MAY_FINALIZE_GROUND_TRUTH`, and `AnnotationVersion`
provides append-only history today. The governance additions this directive
records (for a future authorized change, not implemented here): enforce the
evidence-reference precondition at approval time, and enforce approver-≠-author/
reviewer separation of duties in code as well as policy.
