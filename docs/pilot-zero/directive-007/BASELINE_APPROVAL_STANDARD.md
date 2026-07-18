# LPZ-DIR-007 — Baseline Approval Standard

**Purpose:** define what a baseline record must contain and the rules for
approving it. **No baseline shall be created from unreviewed images.** Approval is
the point at which a candidate becomes a trusted reference; it is attributable,
evidence-gated, and subject to separation of duties.

## Required baseline record fields

| Field | Meaning | System mapping |
|---|---|---|
| **Baseline UUID** | Permanent, immutable identity | `BaselineImageLink` / `BaselineLibraryEntry` id |
| **Source Images** | The reviewed image(s) the baseline is built on | `BaselineImageLink` → LCID `DatasetRegistryEntry` / `RetainedImage`; `BaselineSet` members |
| **Ground Truth Version** | The ACTIVE GT version backing each source image | `Annotation` GT version |
| **Reviewer** | Engineering (and clinical, if applicable) reviewer(s) | `BaselineImageReview` |
| **Approver** | Who approved (attributable) | approval fields / `approved_by` |
| **Approval Timestamp** | When approved | `approved_at` |
| **Confidence** | Reviewer confidence in the reference (not AI certainty) | review confidence |
| **Approval Status** | pending / approved / rejected | `approval_status`, lifecycle state |
| **Evidence References** | Regions / GT / provenance supporting approval | link + review records |
| **Version Number** | Baseline version | `baseline_version` |
| **Approval Rationale** | Why the baseline was approved | `governance_notes` / review reason |

## Approval requirements

1. **Reviewed images only.** Every source image must have **ACTIVE Ground Truth**
   (Directive 006). Unreviewed or non-GT images are ineligible — fail-closed.
2. **Evidence-gated.** Approval requires evidence references (source images, GT
   versions, provenance); missing evidence blocks approval.
3. **Separation of duties.** The approver may not have authored the annotation or
   performed the review of the same evidence (`ANNOTATION_ROLES...` carries the
   role model).
4. **Explicit and attributable.** Approval is a deliberate action recording
   approver, timestamp, and rationale — never automatic.
5. **Provenance & rights.** Source and usage rights are recorded; a baseline with
   unclear rights is not approved.
6. **Category declared.** The baseline's category
   (`BASELINE_CLASSIFICATION_STANDARD.md`) and its permitted uses are set at
   approval.
7. **Confidence recorded.** Reviewer confidence in the reference is recorded and
   labeled as reviewer confidence, not AI certainty.

## Rejection

A rejected candidate records the rejecting authority, reason, and timestamp, and
is retained as history (a new version); it does not become a reference and is not
deleted.

## Multi-image baselines

A `BaselineSet` (several known-good images) is approved as a unit: each member
must independently satisfy the GT and review requirements, and the set records
which member(s) are canonical. This supports "multiple known-good images instead
of one perfect reference."

## Governance note (existing system)

`BaselineImageReview` + the baseline image library service capture reviewer,
approver, status, and notes today, and `BaselineLibraryEntry` carries
`approval_status / approved_by / approved_at / baseline_version /
governance_notes`. Governance additions recorded for a future authorized change:
enforce the ACTIVE-Ground-Truth precondition and separation-of-duties in code at
the approval boundary, and make approval rationale + evidence references
mandatory fields.
