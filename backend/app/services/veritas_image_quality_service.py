"""Project Veritas, Section 5: Image Quality Assessment.

Confirmed via repo-wide search: no real CV-based focus/blur/lighting/glare/
exposure/obstruction/framing/magnification/orientation/duplication/
compression-artifact detector exists anywhere in this codebase. Each of
those signals is honestly reported as unavailable (`"available": false`) --
the same discipline as Nova's observability summary -- rather than
fabricated. `quality_status` is derived only from what IS real: image
presence and, when present, the AI confidence score already computed for
that inspection (a coarse proxy, not a quality metric, and documented as
such).
"""
from __future__ import annotations

from app.models.veritas_evidence import (
    IMAGE_QUALITY_ACCEPTABLE,
    IMAGE_QUALITY_EXCELLENT,
    IMAGE_QUALITY_INSUFFICIENT,
    IMAGE_QUALITY_LIMITED,
)

_UNAVAILABLE_SIGNALS = [
    "focus", "blur", "lighting", "glare", "exposure", "obstruction", "framing",
    "magnification", "orientation", "image_duplication", "compression_artifacts",
]

_NOTE = (
    "Per-image focus/blur/lighting/glare/exposure/obstruction/framing/magnification/"
    "orientation/duplication/compression-artifact detection is not implemented in this "
    "codebase. quality_status below is a coarse proxy derived only from image presence "
    "and existing AI confidence -- never a fabricated per-signal quality score."
)


def assess_image_quality(*, has_image: bool, ai_confidence: float | None = None) -> dict:
    """Section 5: honest image quality assessment."""
    detected_issues: list[str] = []
    recommended_recapture_steps: list[str] = []

    if not has_image:
        return {
            "image_quality_score": 0.0,
            "quality_status": IMAGE_QUALITY_INSUFFICIENT,
            "detected_issues": ["no_image_captured"],
            "recommended_recapture_steps": ["Capture at least one in-focus image of the required anatomy zone."],
            "signals": {name: {"available": False} for name in _UNAVAILABLE_SIGNALS},
            "note": _NOTE,
        }

    if ai_confidence is None:
        return {
            "image_quality_score": None,
            "quality_status": IMAGE_QUALITY_LIMITED,
            "detected_issues": ["no_confidence_signal_available"],
            "recommended_recapture_steps": ["Re-run analysis or recapture if the image appears unclear."],
            "signals": {name: {"available": False} for name in _UNAVAILABLE_SIGNALS},
            "note": _NOTE,
        }

    score = round(100 * ai_confidence, 1)
    if score >= 85:
        status = IMAGE_QUALITY_EXCELLENT
    elif score >= 65:
        status = IMAGE_QUALITY_ACCEPTABLE
    elif score >= 40:
        status = IMAGE_QUALITY_LIMITED
        detected_issues.append("low_confidence_may_indicate_quality_issue")
        recommended_recapture_steps.append("Consider recapturing with better lighting/focus and re-running analysis.")
    else:
        status = IMAGE_QUALITY_INSUFFICIENT
        detected_issues.append("very_low_confidence")
        recommended_recapture_steps.append("Recapture this image before relying on it for a final disposition.")

    return {
        "image_quality_score": score,
        "quality_status": status,
        "detected_issues": detected_issues,
        "recommended_recapture_steps": recommended_recapture_steps,
        "signals": {name: {"available": False} for name in _UNAVAILABLE_SIGNALS},
        "note": _NOTE,
    }
