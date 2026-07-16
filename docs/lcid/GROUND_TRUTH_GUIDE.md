# LCID Ground Truth Guide

## The rule

Ground Truth (the `APPROVED` annotation state) is only ever reached after:

- Primary Review (`LABELED`), **and**
- an independent Second Review that agrees with the primary label
  (`DoubleBlindReview.agreement == True`), **or**
- Clinical Adjudication (`DoubleBlindReview.adjudicator`/`.resolution`/`.reason`
  populated) resolving a disagreement.

No other path reaches `APPROVED` — `VALID_ANNOTATION_TRANSITIONS` in
`app/models/dataset_governance.py` only permits `SECOND_REVIEW -> APPROVED`
and `ADJUDICATED -> APPROVED`, never `UNLABELED`/`LABELED -> APPROVED`
directly.

## AI predictions are never Ground Truth

Nothing in this codebase writes an `APPROVED` `AnnotationEvent` or a
`DoubleBlindReview` row from a model's own inference output — every write
path requires a real reviewer/adjudicator string. The Lumen Decision
Engine's own observations (`docs/decision-engine/LUMEN_DECISION_ENGINE.md`)
are a *candidate* signal at most (see `UNKNOWN_FINDING_GUIDE.md`), never a
Ground Truth label by themselves.

## Verification

`docs/lcid/DATASET_SPECIFICATION.md`'s "no training outside this registry"
guarantee combines with this rule: `eligible_entries()` additionally
requires `review_status == APPROVED` before an image is trainable — so an
image can only ever enter training after the full human-review chain
above, never on the strength of a model's own confidence.
