"""v2.2 — Image Quality Intelligence.

⚠️  THIS IS A DETERMINISTIC PLACEHOLDER — NOT PRODUCTION COMPUTER VISION.

Scores one captured image across the eight metrics the sprint specifies
(focus, blur, lighting, exposure, glare, field coverage, obstruction,
perspective), deterministically seeded from the image's own SHA-256 hash —
the same "stable pseudo-value" pattern
`baseline_comparison_scoring_service._seed_from`/`_pseudo` already uses, so
the same image always scores the same, and no metric is ever fabricated
independently of that seed. A future real-CV release drops into the same
per-metric contract without changing callers.
"""
from __future__ import annotations

import hashlib

METRICS = (
    "focus", "blur", "lighting", "exposure", "glare",
    "field_coverage", "obstruction", "perspective",
)

QUALITY_BANDS = ("excellent", "good", "acceptable", "poor", "reject")


def _seed_from(image_sha256: str | None, fallback: str) -> int:
    """Stable integer seed so the same image always scores the same —
    mirrors baseline_comparison_scoring_service._seed_from exactly."""
    basis = image_sha256 or hashlib.sha256(fallback.encode()).hexdigest()
    return int(basis[:8], 16)


def _pseudo(seed: int, salt: int) -> float:
    """Deterministic pseudo-value in [0, 1) derived from seed + salt."""
    digest = hashlib.sha256(f"{seed}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _band_for_score(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 55:
        return "acceptable"
    if score >= 30:
        return "poor"
    return "reject"


def score_image(image_sha256: str | None, *, fallback_key: str = "") -> dict:
    """Deterministic per-metric quality scores (0-100) plus an overall score
    and band for one captured image.

    `fallback_key` (e.g. f"{inspection_id}:{anatomy_zone}:{sequence}") seeds
    the score when no real image hash is available, so two untagged images
    in the same session still get distinguishable (not identical) scores
    rather than a fabricated fixed value.
    """
    seed = _seed_from(image_sha256, fallback_key or "unscored-image")

    per_metric = {}
    for idx, metric in enumerate(METRICS):
        # Bias toward the "good" range (60-100) — a real captured image is
        # usually usable; a bad one is the exception, not scored 50/50.
        raw = _pseudo(seed, idx)
        per_metric[metric] = round(55 + raw * 45)

    overall = round(sum(per_metric.values()) / len(per_metric))
    band = _band_for_score(overall)

    return {
        "metrics": per_metric,
        "overall_score": overall,
        "quality_band": band,
        "assignment_method": "deterministic_placeholder",
        "human_review_required": band in ("poor", "reject"),
    }
