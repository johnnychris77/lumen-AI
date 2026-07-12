# Project Veritas — Image Quality Assessment

LumenAI AI Specialist, Section 5.

## No real CV quality model exists

A repo-wide search before writing any code confirmed: no focus/blur/
lighting/glare/exposure/obstruction/framing/magnification/orientation/
duplication/compression-artifact detector exists anywhere in this
codebase. `app/cv/image_validator.py` only does SSRF/format/size
validation; `app/cv/ssim_comparator.py` is an explicit mock/fallback
comparator.

## Honest reporting, not fabrication

`veritas_image_quality_service.assess_image_quality` reports every one of
those per-signal metrics as `{"available": false}` — the same discipline
Nova's observability summary and Vulcan's Aegis integration already
established in this codebase. A `note` field states plainly what is and
isn't measured.

## Coarse, documented proxy

`quality_status` (excellent/acceptable/limited/insufficient) is derived
only from two real signals:

1. Whether an image was actually captured (`Inspection.has_image`).
2. The AI confidence already computed for that inspection
   (`Inspection.ai_confidence`), bucketed at 85% / 65% / 40% thresholds.

This is explicitly a proxy, not a quality metric — confidence measures the
model's certainty in its finding, not image sharpness or lighting. The
docstring and `note` field say so directly so no caller mistakes it for a
real quality detector.

## Never a high-confidence result from insufficient evidence

`quality_status = insufficient` (no image, or very low confidence) always
contributes its maximum penalty in the Evidence Readiness Score and can
trigger the `ADDITIONAL_IMAGE_REQUIRED` evidence gate.
