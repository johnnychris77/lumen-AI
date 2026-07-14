"""Dataset Registry & AI Model Development Foundation — Section 5.

Real, pixel-computed image-quality assessment. Every score here is derived
from actual image bytes via Pillow (already a hard dependency, no new
package added) — never fabricated, randomly seeded, or derived from a proxy
signal like ``has_image``/``ai_confidence`` (see
``app.services.veritas_image_quality_service`` and
``app.services.ml.feature_store`` for the pre-existing, honestly-labeled
placeholders this module replaces with real computation).

Blur is estimated via edge-energy variance (the standard deviation of a
Laplacian-style edge filter) — a well-established, simple blur-detection
technique; a sharp image has high-variance edges, a blurry one has low
variance. Exposure/lighting is estimated from mean pixel brightness.
Cropping/resolution is a straightforward minimum-size + aspect-ratio check.
"Visibility" is disclosed as a composite proxy of the other signals, not
object-level occlusion detection — no such detector exists in this codebase.
"""
from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageFilter, ImageStat

from app.models.dataset_governance import (
    QUALITY_EXCELLENT,
    QUALITY_GOOD,
    QUALITY_MARGINAL,
    QUALITY_POOR,
    QUALITY_REJECT,
)

MIN_WIDTH = 200
MIN_HEIGHT = 200
MIN_ASPECT_RATIO = 0.4
MAX_ASPECT_RATIO = 2.5

DARK_THRESHOLD = 40.0
BRIGHT_THRESHOLD = 215.0

BLUR_THRESHOLD = 8.0
FOCUS_MARGINAL_THRESHOLD = 15.0


def assess_image_bytes(data: bytes) -> dict[str, Any]:
    """Assess one image's quality from its real bytes.

    Returns a dict with per-check flags (blur/lighting/exposure/focus/
    cropping/visibility), the raw computed values, and an overall
    Excellent/Good/Marginal/Poor/Reject classification. Undecodable bytes
    are honestly reported as Reject with a clear reason, never guessed.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img = img.convert("RGB")
            width, height = img.size
            gray = img.convert("L")
            brightness = ImageStat.Stat(gray).mean[0]
            edges = gray.filter(ImageFilter.FIND_EDGES)
            sharpness = ImageStat.Stat(edges).stddev[0]
    except Exception as exc:
        return {
            "decodable": False,
            "width": 0,
            "height": 0,
            "brightness_mean": 0.0,
            "sharpness_score": 0.0,
            "blur_flag": True,
            "lighting_flag": True,
            "exposure_flag": True,
            "focus_flag": True,
            "cropping_flag": True,
            "visibility_flag": True,
            "overall_quality": QUALITY_REJECT,
            "notes": f"Image bytes could not be decoded: {exc}",
        }

    blur_flag = sharpness < BLUR_THRESHOLD
    focus_flag = sharpness < FOCUS_MARGINAL_THRESHOLD
    exposure_flag = brightness < DARK_THRESHOLD or brightness > BRIGHT_THRESHOLD
    lighting_flag = exposure_flag
    aspect = (width / height) if height else 0.0
    resolution_flag = width < MIN_WIDTH or height < MIN_HEIGHT
    aspect_flag = not (MIN_ASPECT_RATIO <= aspect <= MAX_ASPECT_RATIO) if aspect else True
    cropping_flag = resolution_flag or aspect_flag
    # Visibility is a composite proxy (blur + exposure) — not an object-level
    # occlusion/visibility detector, which does not exist in this codebase.
    visibility_flag = blur_flag or exposure_flag

    failed = sum([blur_flag, lighting_flag, exposure_flag, focus_flag, cropping_flag, visibility_flag])

    if cropping_flag:
        overall = QUALITY_REJECT
    elif failed >= 3:
        overall = QUALITY_POOR
    elif failed == 2:
        overall = QUALITY_MARGINAL
    elif failed == 1:
        overall = QUALITY_GOOD
    else:
        overall = QUALITY_EXCELLENT

    notes = []
    if blur_flag:
        notes.append(f"Low edge-sharpness signal ({sharpness:.1f} < {BLUR_THRESHOLD}) — image may be blurry.")
    if exposure_flag:
        notes.append(f"Brightness {brightness:.0f}/255 outside the {DARK_THRESHOLD:.0f}-{BRIGHT_THRESHOLD:.0f} acceptable range.")
    if resolution_flag:
        notes.append(f"Resolution {width}x{height} below the {MIN_WIDTH}x{MIN_HEIGHT} minimum.")
    if aspect_flag:
        notes.append(f"Aspect ratio {aspect:.2f} outside the expected instrument-photo range.")

    return {
        "decodable": True,
        "width": width,
        "height": height,
        "brightness_mean": round(brightness, 2),
        "sharpness_score": round(sharpness, 2),
        "blur_flag": blur_flag,
        "lighting_flag": lighting_flag,
        "exposure_flag": exposure_flag,
        "focus_flag": focus_flag,
        "cropping_flag": cropping_flag,
        "visibility_flag": visibility_flag,
        "overall_quality": overall,
        "notes": " ".join(notes) if notes else "No quality issues detected.",
    }


def excluded_from_training(overall_quality: str) -> bool:
    """Reject-quality images are excluded from training datasets (Section 5)."""
    return overall_quality == QUALITY_REJECT
