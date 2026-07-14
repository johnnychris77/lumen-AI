"""Phase 17 §4 — Baseline-comparison feature store.

Defines the feature vector a future image model / baseline-diff will consume, and
extracts what is *honestly* available today from the deterministic pilot scoring
result. Real computer-vision features (color/texture/edge/corrosion similarity)
are still labeled as not-yet-computed rather than fabricated — no trained vision
model exists in this repo. As of the Dataset Registry & AI Model Development
Foundation pass, ``image_blur_score``/``lighting_quality_score`` ARE real,
computed values when the actual image bytes are supplied (see
``app.services.ml.image_quality``, real Pillow-based blur/brightness
computation) — they move from ``_CV_FEATURES`` (permanently null) into
computed features whenever ``image_bytes`` is passed in.
"""
from __future__ import annotations

from typing import Any

# The full feature schema (order is stable so it can back a real feature matrix).
FEATURE_NAMES = [
    "baseline_match_score",
    "image_similarity_score",
    "color_deviation",
    "texture_deviation",
    "edge_anomaly",
    "corrosion_color_signature",
    "dark_residue_signal",
    "image_blur_score",
    "lighting_quality_score",
    "zone_coverage_score",
]

# Features that still require a real trained vision model — not computed
# anywhere in this codebase (unlike blur/lighting, which are now real pixel
# computations — see extract_features()'s image_bytes handling below).
_CV_FEATURES = {
    "image_similarity_score", "color_deviation", "texture_deviation",
    "edge_anomaly", "corrosion_color_signature", "dark_residue_signal",
}


def extract_features(
    analysis_result: dict, coverage: dict | None = None, image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Extract the feature vector for one inspection.

    Available-now features come from the deterministic scoring result, the
    coverage engine, and — when ``image_bytes`` is supplied — real Pillow-
    based blur/brightness computation (``app.services.ml.image_quality``).
    Remaining CV features are returned as ``None`` with an ``available``
    flag — the store records that they are pending a real vision model,
    never a fabricated number.
    """
    coverage = coverage or analysis_result.get("inspection_coverage") or {}
    values: dict[str, Any] = {name: None for name in FEATURE_NAMES}

    values["baseline_match_score"] = analysis_result.get("baseline_match_score")
    cov_pct = coverage.get("overall_coverage")
    values["zone_coverage_score"] = cov_pct if isinstance(cov_pct, (int, float)) else None

    if image_bytes:
        from app.services.ml.image_quality import assess_image_bytes

        quality = assess_image_bytes(image_bytes)
        if quality["decodable"]:
            # Sharpness/brightness are on different natural scales; expose
            # them as-is (not normalized to a fake 0-1 "quality" score) so a
            # future model consumes the real measurement, not a guess.
            values["image_blur_score"] = quality["sharpness_score"]
            values["lighting_quality_score"] = quality["brightness_mean"]

    computed_now = {"image_blur_score", "lighting_quality_score"}
    available = {
        name: (values[name] is not None) and (name not in _CV_FEATURES or name in computed_now)
        for name in FEATURE_NAMES
    }
    return {
        "features": values,
        "available": available,
        "pending_cv_features": sorted(_CV_FEATURES),
        "note": (
            "color/texture/edge/corrosion/similarity features require a trained vision "
            "model; stored as null until then — not fabricated. blur/lighting are real, "
            "pixel-computed values when image_bytes is supplied."
        ),
    }


def feature_completeness(feature_record: dict) -> float:
    """Fraction of the schema that is actually populated today (0..1)."""
    avail = feature_record.get("available", {})
    if not avail:
        return 0.0
    return round(sum(1 for v in avail.values() if v) / len(avail), 3)
