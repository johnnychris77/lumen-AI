# LCID Review Guide

## Workflow

UNREVIEWED → PRIMARY REVIEW → SECOND REVIEW → DISAGREEMENT → ADJUDICATION
→ APPROVED → ARCHIVED (see `ANNOTATION_GUIDE.md` for the exact mapping
onto the codebase's `UNLABELED`/`LABELED`/... constants — nothing was
renamed).

`ARCHIVED` is reachable from any non-terminal state
(`VALID_ANNOTATION_TRANSITIONS` in `app/models/dataset_governance.py`) — a
curator may retire an entry at any point; nothing leaves `ARCHIVED`.

## What's tracked on every review

- **Reviewer** — `AnnotationEvent.reviewer` / `DoubleBlindReview.primary_reviewer`
  / `.independent_reviewer` / `.adjudicator`.
- **Timestamp** — `AnnotationEvent.created_at`,
  `DoubleBlindReview.primary_submitted_at` / `.independent_submitted_at` /
  `.resolved_at`.
- **Confidence** — `AnnotationEvent.confidence`,
  `DoubleBlindReview.primary_confidence` / `.independent_confidence`.
- **Comments** — `AnnotationEvent.comments`, `DoubleBlindReview.reason`
  (the adjudicator's rationale).
- **Agreement** — `DoubleBlindReview.agreement` (a real boolean computed
  from comparing the two independent labels, never assumed).
- **Disagreement reason** — captured in `DoubleBlindReview.reason` once
  the entry reaches `DISAGREEMENT`/`ADJUDICATED`.

## Independence guarantee

Neither reviewer sees the other's label at submission time — enforced in
the service layer (`app.services.ml.double_blind_review`): the independent
label may only be submitted once, and the primary reviewer's label is
never surfaced to the independent reviewer through this record before
they submit their own.
