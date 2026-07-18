# LPZ-DIR-007 — Baseline Creation Workflow

**Purpose:** define the governed path by which acquired images become an approved
baseline reference associated with a Digital Twin. **No baseline is created from
unreviewed images** — a baseline inherits the trust of the Ground Truth beneath
it.

## Workflow

```
Image Acquisition            (Directive 005 — governed capture, identity-bound)
      │
      ▼
Annotation                   (Directive 006 — controlled taxonomy, evidence)
      │
      ▼
Ground Truth                 (Directive 006 — human-approved, immutable, ACTIVE)
      │
      ▼
Engineering Review           (optics/structure/coverage adequate for a reference)
      │
      ▼
Clinical Review (if applicable)  (domain acceptability where relevant)
      │
      ▼
Baseline Candidate           (assembled reference: image(s) + GT + provenance)
      │
      ▼
Approval                     (Baseline Approver; separation of duties)
      │
      ▼
Digital Twin Association     (attach approved baseline to the instrument twin)
      │
      ▼
Reference Publication        (baseline becomes an ACTIVE/Published reference)
```

## Stage detail

### 1. Image Acquisition
Governed capture under Directive 005: identity-bound, provenance-complete,
integrity-hashed, no PHI. Images without this provenance cannot seed a baseline.

### 2. Annotation
Findings recorded under Directive 006's controlled taxonomy with evidence
references and reviewer confidence; uncertainty recorded as Unknown rather than
forced.

### 3. Ground Truth
The image's annotation must reach **ACTIVE Ground Truth** (independent review +
approval). A baseline may only be built on ACTIVE Ground Truth — this is the
"no baseline from unreviewed images" rule made concrete.

### 4. Engineering Review
An Engineering Reviewer confirms the image(s) are technically fit to be a
reference: focus, lighting, coverage, and geometry adequate; artifacts excluded.

### 5. Clinical Review (if applicable)
Where domain judgment is relevant, a Clinical Reviewer confirms acceptability.
Marked "not applicable" with rationale when not required — never skipped silently.

### 6. Baseline Candidate
The reviewed image(s) + Ground Truth version + provenance + proposed category are
assembled into a **candidate** (single image or a `BaselineSet` of several
known-good images). The candidate is not yet usable for comparison.

### 7. Approval
A **Baseline Approver** (who did not author the annotation or the reviews)
approves the candidate against `BASELINE_APPROVAL_STANDARD.md`, recording
approver, timestamp, rationale, confidence, and evidence references. Rejection
returns it with a reason (a new version).

### 8. Digital Twin Association
The approved baseline is attached to the instrument's Digital Twin as a
**Baseline Reference**, so all future inspections of that instrument resolve to
it.

### 9. Reference Publication
The baseline transitions to **ACTIVE/Published** and becomes selectable as a
comparison reference (`BASELINE_LIFECYCLE_STANDARD.md`). Publication is explicit
and attributable.

## Invariants

* **GT-gated:** no ACTIVE Ground Truth → no baseline candidate.
* **Separation of duties:** approver ≠ annotator/reviewer of the same evidence.
* **Provenance & rights:** source and usage rights recorded before approval.
* **Fail-closed:** any missing review, evidence, or identity blocks progression.
* **No overwrite:** revisions create new versions; history retained.

## Governance note (existing system)

The repository already implements much of this: `baseline_image_library_service`
links an LCID-registered, Ground-Truth-eligible image to a `BaselineLibraryEntry`
via `BaselineImageLink`, with a `BaselineImageReview` record and a lifecycle
(`DRAFT → PENDING_REVIEW → APPROVED → ACTIVE …`); `BaselineSet` groups multiple
known-good images. Governance additions recorded for a future authorized change:
enforce the ACTIVE-Ground-Truth precondition and the approver-≠-author/reviewer
separation of duties at the approval boundary, and make Digital Twin association
an explicit published step.
