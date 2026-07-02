"""Phase 17 §4 — Baseline-comparison feature store (stubs).

Defines the feature vector a future image model / baseline-diff will consume, and
extracts what is *honestly* available today from the deterministic pilot scoring
result. Real computer-vision features (color/texture/edge/corrosion/blur/lighting)
are labeled as not-yet-computed rather than fabricated.
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

# Features that require real pixel-level CV — not computed in the pilot.
_CV_FEATURES = {
    "image_similarity_score", "color_deviation", "texture_deviation",
    "edge_anomaly", "corrosion_color_signature", "dark_residue_signal",
    "image_blur_score", "lighting_quality_score",
}


def extract_features(analysis_result: dict, coverage: dict | None = None) -> dict[str, Any]:
    """Extract the feature vector for one inspection.

    Available-now features come from the deterministic scoring result and the
    coverage engine. CV features are returned as ``None`` with an ``available``
    flag — the store records that they are pending a real vision model, never a
    fabricated number.
    """
    coverage = coverage or analysis_result.get("inspection_coverage") or {}
    values: dict[str, Any] = {name: None for name in FEATURE_NAMES}

    values["baseline_match_score"] = analysis_result.get("baseline_match_score")
    cov_pct = coverage.get("overall_coverage")
    values["zone_coverage_score"] = cov_pct if isinstance(cov_pct, (int, float)) else None

    available = {
        name: (values[name] is not None) and (name not in _CV_FEATURES)
        for name in FEATURE_NAMES
    }
    return {
        "features": values,
        "available": available,
        "pending_cv_features": sorted(_CV_FEATURES),
        "note": (
            "CV features (color/texture/edge/corrosion/blur/lighting/similarity) "
            "require a trained vision model; stored as null until then — not fabricated."
        ),
    }


def feature_completeness(feature_record: dict) -> float:
    """Fraction of the schema that is actually populated today (0..1)."""
    avail = feature_record.get("available", {})
    if not avail:
        return 0.0
    return round(sum(1 for v in avail.values() if v) / len(avail), 3)
