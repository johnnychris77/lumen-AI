# LPZ-DIR-006 — Disagreement Resolution Standard

**Purpose:** define what happens when reviewers do not agree, so that
disagreement is resolved **transparently, with evidence preserved**, and never
by silently overriding a reviewer. Disagreement is a normal, healthy signal — it
is recorded and resolved, not suppressed.

## When this applies

Entered when the Primary Annotator and the independent Secondary Reviewer differ
on the observation, region, severity, or confidence — or when either flags the
item as requiring escalation. *System:* `AnnotationReview.agreement = false`,
state `SECOND_REVIEW → DISAGREEMENT`.

## Possible outcomes

| Outcome | Meaning |
|---|---|
| **Agreement** | On re-examination the reviewers converge; recorded with rationale. |
| **Consensus Review** | Reviewers jointly reach a single governed annotation. |
| **Third Reviewer** | An independent third reviewer breaks the tie. |
| **Expert Panel** | A panel (clinical + engineering as needed) decides complex cases. |
| **Unable to Determine** | Evidence does not permit a resolution; recorded as a governed outcome. |
| **Rejected** | The annotation is not usable (e.g., image quality); routed out of the GT path. |

`Unable to Determine` and `Rejected` are **valid endpoints** — the framework
does not force a defect classification to close a disagreement.

## Escalation ladder

```
Disagreement
   │
   ├─▶ Consensus Review (reviewers reconcile)  ── resolved ─▶ Adjudicated
   │
   ├─▶ Third Reviewer (independent)            ── resolved ─▶ Adjudicated
   │
   └─▶ Expert Panel (clinical/engineering)     ── resolved ─▶ Adjudicated
                                                    │
                                                    ├─▶ Unable to Determine
                                                    └─▶ Rejected
```

Escalation level is chosen by the assigned adjudicator based on complexity;
skipping straight to Expert Panel is permitted for high-stakes/ambiguous cases.

## Decision recording (required for every resolution)

* **Adjudicator identity** and role (must not be a party to the disagreement).
* **Outcome** (from the table above).
* **Rationale** referencing the evidence relied on.
* **Timestamp.**
* **Resulting annotation state / version** (a new version is written; the prior
  reviewers' inputs are never deleted).

*System:* `AnnotationReview.adjudicator / resolution / adjudication_reason /
resolved_at`, state `DISAGREEMENT → ADJUDICATED (→ APPROVED | ARCHIVED)`.

## Evidence preservation (non-negotiable)

* Both reviewers' original inputs (labels, confidence, comments) are preserved
  immutably — resolution **adds** a record, it never overwrites the disagreement.
* The evidence (image regions, baseline comparisons) cited by each party is
  retained and referenced in the resolution.
* The full disagreement → resolution path is reconstructable from the audit
  trail and version history.

## Separation of duties

* The adjudicator (Third Reviewer, Clinical/Engineering Reviewer, or panel
  member) must be independent of the primary and secondary reviewers of the
  item.
* An adjudicated outcome still passes through **Ground Truth Approval** before
  becoming Ground Truth — adjudication resolves the disagreement, it does not by
  itself create Ground Truth.

## Governance note (existing system)

`annotation_review_service` implements primary/secondary submission and clinical
adjudication (`adjudicate` route) with `AnnotationReview` capturing both
reviewers plus the adjudicator immutably. Governance additions recorded for a
future authorized change: represent the intermediate outcomes (Consensus / Third
Reviewer / Expert Panel / Unable to Determine / Rejected) as an explicit,
validated vocabulary, and enforce adjudicator independence in code.
