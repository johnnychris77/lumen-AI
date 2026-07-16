# LCID Annotation Guide

**This extends, and does not duplicate,**
`docs/ml-governance/ANNOTATION_GUIDE.md` — that document remains the
authoritative description of the 7-state annotation lifecycle
(`app.models.dataset_governance.ANNOTATION_STATES`) and the
`AnnotationEvent` append-only log. This page adds only the LCID-spec
naming and the two fields that sprint added (`lcid`, `digital_twin_id`,
`baseline_id`) to what an annotator sees per image.

## State-name mapping

The LCID spec (Sprint 1) uses different display names for the same 7
states already implemented:

| LCID spec name | Codebase constant |
|---|---|
| UNREVIEWED | `UNLABELED` |
| PRIMARY REVIEW | `LABELED` |
| SECOND REVIEW | `SECOND_REVIEW` |
| DISAGREEMENT | `DISAGREEMENT` |
| ADJUDICATION | `ADJUDICATED` |
| APPROVED | `APPROVED` |
| ARCHIVED | `ARCHIVED` |

No renaming was done in code — the existing constants are unchanged
(renaming would be a breaking change to `test_dataset_registry.py` and
every dependent service) — this table is the single place the mapping is
recorded.

## What an annotator sees for each image

In addition to the fields `docs/ml-governance/ANNOTATION_GUIDE.md` already
describes: the image's permanent `lcid` (Dataset ID — quote this in any
reviewer note or ticket, never the internal row `id`), its
`digital_twin_id` (the same physical-instrument identity used elsewhere in
this codebase — `untracked:...` when no barcode/UDI was captured), and
`baseline_id` (which approved baseline it was compared against, if any).

## Required transition record

Every `AnnotationEvent` still requires reviewer, confidence, and comments
per the existing guide — Section 6 of the LCID spec's "track reviewer /
timestamp / confidence / comments / agreement / disagreement reason" is
already the shape of `AnnotationEvent` plus `DoubleBlindReview.agreement`/
`.reason`.
