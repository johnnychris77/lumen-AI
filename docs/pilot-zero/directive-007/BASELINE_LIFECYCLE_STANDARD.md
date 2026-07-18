# LPZ-DIR-007 — Baseline Lifecycle Standard

**Purpose:** define the lifecycle states of a baseline and the governed
transitions between them, so a baseline's trust level is always explicit and no
baseline is used outside its authorized state. This maps directly onto the
lifecycle already implemented in the baseline image library
(`BASELINE_IMAGE_STATES` + validated transition map).

## States and transitions

```
Draft ─▶ Candidate ─▶ Under Review ─▶ Approved ─▶ Published
                            │             │           │
                            ▼             ▼           ▼
                        (Rejected)   (Rejected)   Superseded ─▶ Archived
                                                     │
                                            Retired ─▶ Archived
```

Implemented mapping (`baseline_image_library.py`): `DRAFT → PENDING_REVIEW →
APPROVED → ACTIVE(Published) → {SUSPENDED, SUPERSEDED} → ARCHIVED`, plus
`REJECTED → ARCHIVED`. "Under Review" = `PENDING_REVIEW`; "Published" = `ACTIVE`;
"Retired" is represented by suspension/supersession leading to `ARCHIVED`.

## Per-state definition

### Draft
* **Entry:** a baseline record is created from reviewed source material.
* **Exit:** promoted to Candidate/Under Review, or Archived.
* **Allowed actions:** edit candidate content (each change versioned); attach
  source images/GT.
* **Required approvals:** none (not yet a reference).

### Candidate
* **Entry:** assembled reference (image[s] + GT + provenance) proposed.
* **Exit:** submitted for review, or Archived.
* **Allowed actions:** finalize the candidate package.
* **Required approvals:** none; **not usable for comparison.**

### Under Review (`PENDING_REVIEW`)
* **Entry:** submitted for engineering/clinical review.
* **Exit:** Approved or Rejected.
* **Allowed actions:** reviewer assessment; record review outcome.
* **Required approvals:** reviewer sign-off to proceed.

### Approved
* **Entry:** Baseline Approver approves per `BASELINE_APPROVAL_STANDARD.md`.
* **Exit:** Published (activated), or Archived.
* **Allowed actions:** associate with Digital Twin; prepare publication.
* **Required approvals:** Baseline Approver (separation of duties enforced).

### Published (`ACTIVE`)
* **Entry:** activated as a live comparison reference.
* **Exit:** Superseded (new version), Suspended, Retired, or Archived.
* **Allowed actions:** used as a comparison reference; read-only content.
* **Required approvals:** activation is attributable; changes require a new
  version.

### Superseded
* **Entry:** a newer approved version replaces it.
* **Exit:** Archived.
* **Allowed actions:** retained for audit and to reproduce past comparisons; **not**
  used for new comparisons.
* **Required approvals:** supersession recorded with reason.

### Retired
* **Entry:** withdrawn from active use (quality, defect, policy).
* **Exit:** Archived.
* **Allowed actions:** none for new comparisons; retained for history.
* **Required approvals:** Baseline Approver records retirement + reason.

### Archived
* **Entry:** terminal state from Superseded/Retired/Rejected/Draft.
* **Exit:** none — **nothing leaves Archived.**
* **Allowed actions:** read-only retrieval for audit/lineage.
* **Required approvals:** n/a.

## Rules

* **Only Published baselines are live references.** Draft/Candidate/Under Review
  and Retired/Superseded/Archived baselines are never used for new comparisons.
* **Validated transitions only.** The transition map is enforced; illegal jumps
  (e.g., Draft → Published) are rejected.
* **Every transition is attributable and audited** (actor, action, timestamp,
  reason).
* **Suspension** (`SUSPENDED`) temporarily removes a Published baseline from use
  (e.g., pending investigation) and may return to Active or move to Superseded/
  Archived.

## Governance note (existing system)

`BASELINE_IMAGE_STATES` and `BASELINE_IMAGE_TRANSITIONS` implement this lifecycle
with a validated state machine today; `BaselineImageReview` and the access log
provide review and audit. Governance additions recorded for a future authorized
change: expose "Candidate" explicitly (vs. folding it into DRAFT) and map
"Retired" to a first-class retirement action distinct from supersession. No code
is changed under this directive.
