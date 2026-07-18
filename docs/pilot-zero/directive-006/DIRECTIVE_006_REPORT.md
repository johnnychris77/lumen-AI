# LPZ-DIR-006 — Directive Report: Annotation & Ground Truth Framework

## Executive summary

Directive 006 establishes the **governance framework** by which raw inspection
images become governed **Ground Truth** records suitable for future AI training
and validation. It delivers a complete standard set — workflow, roles, controlled
taxonomy, per-category guidelines, Ground Truth governance, disagreement
resolution, confidence, quality metrics, and versioning — and grounds each
standard in the annotation system already present in the repository.

Every annotation governed by this framework is **attributable, reproducible,
reviewable, version-controlled, evidence-based, and auditable**. Ground Truth is
the highest-trust, **human-approved** representation of an inspected image,
created only through the approved review workflow, and **never overwritten**.

This directive is **governance and documentation only**. No new product
functionality, no AI model training, no hospital deployment workflow, and no
regulatory or clinical performance claim is created. Where the framework exceeds
what is currently enforced in code, the difference is recorded as a **migration
plan** (below) for a future, separately-authorized change — nothing in the
application was modified under this directive.

## Annotation workflow

`ANNOTATION_WORKFLOW.md` defines the lifecycle: Raw Image → Quality Verification
→ Primary Annotation → Secondary Review → Disagreement Resolution (if needed) →
Ground Truth Candidate → Expert Approval → Ground Truth Record → Dataset
Eligibility, with fail-closed gates (no identity/evidence/review → no promotion).
It maps onto the implemented state machine
`UNLABELED → LABELED → SECOND_REVIEW → {DISAGREEMENT|ADJUDICATED|APPROVED} →
ARCHIVED` and `DRAFT → ACTIVE` Ground Truth.

## Roles

`ANNOTATION_ROLES_AND_RESPONSIBILITIES.md` defines nine governance roles (Image
Acquisition Operator, Primary Annotator, Secondary Reviewer, Clinical Reviewer,
Engineering Reviewer, Ground Truth Approver, Dataset Curator, Quality Auditor,
Program Administrator) with responsibilities, permissions, approval authority,
training, and a **separation-of-duties matrix** — no one approves their own work;
at least two distinct people stand between a raw annotation and approved Ground
Truth. Roles map to the six implemented role strings and the
`ROLES_MAY_*` enforcement sets.

## Taxonomy

`ANNOTATION_TAXONOMY.md` provides a controlled vocabulary across identification,
clean surface, residual/contamination, material condition, uncertainty, and
image-quality/artifact groups, plus appearance attributes, severity, and region
types. **"Unknown" is an explicit, acceptable governed outcome** — annotators are
never forced to classify uncertain findings. Terms describe the *image of an
instrument* (engineering appearance), asserting no clinical meaning.

## Ground Truth process

`GROUND_TRUTH_GOVERNANCE.md` specifies the required record fields (GT UUID, Image
UUID, annotation/review versions, approver, timestamp, evidence, confidence,
decision, status, version history), the creation rules (candidate-first,
separation of duties, evidence-gated, explicit approval), and the **immutability
rules** (no overwrite; supersede with a new version; traceable lineage; stable
identity). Only `ACTIVE` Ground Truth is dataset-eligible; dataset building and
model metrics are explicitly out of scope.

## Confidence framework

`ANNOTATION_CONFIDENCE_STANDARD.md` defines High / Moderate / Low / Unable to
Determine as **reviewer** confidence — never AI certainty — with required
evidence per level and a rule that confidence may not exceed what image quality
supports. AI `confidence` is kept strictly separate from `reviewer_confidence`.

## Quality metrics

`ANNOTATION_QUALITY_METRICS.md` defines inter-reviewer agreement, completeness,
turnaround, approval rate, rejections, consensus rate, Unknown frequency, version
changes, and **audit completeness (target 100%)** — all computed from real
records, with "insufficient data" reported rather than fabricated numbers, and
no numeric pass/fail thresholds set prematurely.

## Versioning

`ANNOTATION_VERSIONING_STANDARD.md` requires immutable UUID, monotonic version
number, parent linkage, editor, timestamp, mandatory reason, evidence reference,
audit linkage, and Ground Truth/dataset links — **append-only, never
overwritten** — backed by the existing `AnnotationVersion` snapshot chain.

## Validation procedures (test requirements) & expected outcomes

Documentation-only directive — these are the **validation procedures** a future
authorized implementation change must satisfy, with expected outcomes. No tests
were added or modified under this directive.

| # | Validates | Procedure (future) | Expected outcome |
|---|---|---|---|
| 1 | Annotation completeness | Create an annotation missing a required field (taxonomy term / region / evidence). | Rejected or flagged incomplete; not GT-eligible. |
| 2 | Required metadata | Create with full required metadata. | Accepted; all fields persisted and retrievable. |
| 3 | Version creation | Edit an existing annotation. | New immutable version with parent link, editor, timestamp, reason; prior version unchanged. |
| 4 | Review workflow | Submit primary then independent secondary review. | State advances `LABELED → SECOND_REVIEW`; both inputs recorded; reviewer ≠ annotator enforced. |
| 5 | Disagreement escalation | Submit conflicting primary/secondary. | State enters `DISAGREEMENT`; adjudicator (independent) records outcome + reason; both original inputs preserved. |
| 6 | Ground Truth approval | Approve a candidate as GT with evidence. | `DRAFT → ACTIVE`; immutable GT version; approver ≠ author/reviewer; blocked if evidence missing. |
| 7 | Audit logging | Perform each lifecycle transition. | Every transition emits an attributable audit event; audit completeness = 100%. |
| 8 | Confidence recording | Record reviewer confidence; attempt High on a Poor image. | Reviewer confidence stored separately from AI confidence; quality cap prevents over-confident annotation. |
| 9 | Evidence linkage | Approve GT for an annotation with no region/baseline evidence. | Fail-closed: approval blocked until evidence is referenced. |

## Existing-system gap analysis & migration plan

The repository already implements most of the framework: models `Annotation`,
`AnnotationVersion`, `AnnotationReview`, `AnnotationSequenceCounter`; services
`annotation_service`, `annotation_review_service`,
`annotation_ground_truth_service`, `annotation_blind_review_service`,
`annotation_analytics_service`, `annotation_export_service`; routes under
`/annotations`. Governance gaps and the (future, separately-authorized) plan to
close them:

| Gap | Current state | Migration step (future) | Priority |
|---|---|---|---|
| Taxonomy not constrained | `primary_observation` is free `String(80)` | Add allow-list validation against `ANNOTATION_TAXONOMY.md` on create/update | High |
| Confidence banding | Numeric `reviewer_confidence` only | Map to High/Moderate/Low/UTD bands; label as reviewer confidence in UI | Medium |
| Evidence-gated approval | Not enforced at approval | Require evidence reference before `DRAFT → ACTIVE` | High |
| SoD in code | Enforced by role sets, not by author/reviewer identity | Block approver == author/reviewer of same annotation | High |
| Mandatory reason | Reason field exists | Make reason required at the API boundary for all mutations | Medium |
| Disagreement vocabulary | Free-form resolution | Represent Consensus/Third/Panel/UTD/Rejected as validated enum | Medium |
| Metrics coverage | Agreement/completeness/Unknown computed | Add turnaround, version-churn, audit-completeness aggregates | Low |

**No migration step is executed under Directive 006.** Each is a candidate for a
future directive that explicitly authorizes code changes.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Free-text taxonomy allows drift | Non-reproducible annotations | Controlled vocabulary defined; allow-list enforcement planned |
| Reviewer confidence mistaken for AI certainty | Misleading trust | Standard mandates "reviewer confidence" labeling; AI value kept separate |
| Ground Truth edited in place | Loss of trust/auditability | Immutability rule + append-only versioning (already in place) |
| Approver reviews own work | Weak Ground Truth | Separation-of-duties matrix; code enforcement planned |
| Forced classification of uncertain findings | False labels | "Unknown"/"Unable to Determine" are valid governed outcomes |
| Premature quality thresholds | Gaming / false assurance | Thresholds deferred until real baselines exist |
| Scope creep into model training | Violates directive & freeze | Non-goals restated in every document; dataset/metrics out of scope |

## Assumptions

* Governed image acquisition and metadata (Directives 004/005) are available so
  annotations attach to identity-bound, provenance-complete images.
* Trained personnel can fill the annotation/review/approval/curation/audit roles
  with separation of duties.
* No PHI enters annotations or metadata — instruments only.

## Dependencies

* **Program:** Directive 001 (Charter), 002 (Security & Engineering Gate), 004
  (Lab), 005 (Acquisition & Metadata) — all complete.
* **System:** the existing annotation models/services/routes above.
* **Personnel:** annotators, independent reviewers, adjudicators (clinical/
  engineering), Ground Truth approvers, dataset curators, quality auditors.

## Acceptance criteria

All ten deliverables exist under `docs/pilot-zero/directive-006/`, are internally
consistent and vendor-neutral, make no clinical/regulatory/performance claim,
treat "Unknown" as a valid outcome, define confidence as reviewer confidence,
enforce Ground Truth immutability, and include validation procedures with
expected outcomes plus an honest gap analysis of the existing system. **Met.**

## Exit criteria (to operate under this framework — future work)

1. Taxonomy allow-list and evidence-gated approval enforced in code (High-priority
   migration steps).
2. Separation-of-duties (approver ≠ author/reviewer) enforced in code.
3. Confidence banding + reviewer-confidence labeling in the workspace.
4. Validation procedures 1–9 implemented and passing on a clean database.
5. Personnel trained and roles assigned with separation of duties.

## Completion status

**LPZ-DIR-006 annotation & Ground Truth governance framework: COMPLETE
(documented).** The framework is defined, grounded in the existing system, and
accompanied by a migration plan and validation procedures. **Code enforcement of
the migration steps is NOT started (by design — deferred to a future authorized
directive).** No AI training datasets or performance metrics were created, and no
regulatory or clinical claim is made.
