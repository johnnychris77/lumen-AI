# LPZ-DIR-006 — Annotation Confidence Standard

**Purpose:** define confidence levels for annotations. **Confidence here is
reviewer confidence — a human judgement of how certain the reviewer is — not an
AI certainty, probability, or model score.** This distinction is
non-negotiable: no confidence value in this framework represents model output.

## Confidence levels

| Level | Meaning | Typical evidence |
|---|---|---|
| **High** | The reviewer is confident the annotation is correct. | Good/Excellent image quality; clear, unambiguous appearance; identity confirmed; region well-defined. |
| **Moderate** | Reasonable confidence; minor ambiguity remains. | Adequate quality; appearance mostly clear but with some ambiguity; small evidence gaps. |
| **Low** | The reviewer leans toward the annotation but is uncertain. | Marginal quality or ambiguous appearance; competing interpretations plausible. |
| **Unable to Determine** | The reviewer cannot make a confident call. | Poor/Reject quality, incomplete coverage, or genuinely indeterminate evidence. |

`Unable to Determine` is a **governed, acceptable outcome** and pairs with the
`unable_to_determine` / `unknown_finding` taxonomy terms. Reviewers are never
required to raise confidence beyond what the evidence supports.

## Required evidence per level

* **High** — image quality `Good`/`Excellent`; region annotation present;
  identity confirmed; no unresolved competing interpretation; comment optional.
* **Moderate** — image quality at least `Marginal`; region present; a comment
  noting the residual ambiguity.
* **Low** — a comment is **required** stating the source of uncertainty and the
  interpretation considered; the item is a candidate for Secondary Review
  attention.
* **Unable to Determine** — a comment is **required** stating why; the item
  generally routes to re-capture, disagreement resolution, or an Unknown
  outcome rather than to Ground Truth.

## Interaction with image quality

Confidence may not exceed what image quality supports:

| Image quality | Maximum reviewer confidence |
|---|---|
| Excellent / Good | High |
| Marginal | Moderate |
| Poor | Low |
| Reject | Unable to Determine (image not annotated for GT) |

This prevents "confident" annotations on unreliable images.

## Confidence vs. Ground Truth

* Confidence is recorded on the annotation and carried onto the Ground Truth
  record, but **Ground Truth status is decided by the review workflow and the
  approver**, not by a confidence threshold alone.
* A `Low` or `Unable to Determine` annotation may still be valuable (e.g., feeds
  the Unknown learning loop) but should not be approved as high-trust Ground
  Truth without resolution.

## System mapping and governance note

The system stores two numeric fields today: `Annotation.confidence` (may hold an
AI observation's score where the annotation originated from an AI observation)
and `Annotation.reviewer_confidence` (the human value this standard governs).
`AnnotationReview.primary_confidence` / `secondary_confidence` hold each
reviewer's value.

Governance additions recorded for a future authorized change (not implemented
here): map the qualitative bands (High/Moderate/Low/Unable to Determine) onto the
stored `reviewer_confidence` field via a documented banding, keep AI `confidence`
strictly separate from `reviewer_confidence`, and label every confidence display
in any workspace as **reviewer** confidence so it is never mistaken for model
certainty.
