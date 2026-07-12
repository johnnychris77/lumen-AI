"""Project Veritas, Section 8: Evidence Readiness Score.

0-100 composite with a transparent breakdown -- evaluates evidence quality,
not instrument cleanliness (a Vulcan reliability score answers a different
question and is never conflated with this one).
"""
from __future__ import annotations

from app.models.veritas_evidence import (
    BASELINE_STATUS_APPROVED,
    BASELINE_STATUS_CONDITIONALLY_APPROVED,
    IMAGE_QUALITY_ACCEPTABLE,
    IMAGE_QUALITY_EXCELLENT,
    IMAGE_QUALITY_INSUFFICIENT,
    IMAGE_QUALITY_LIMITED,
    MATCH_COMPATIBLE,
    MATCH_EXACT,
    MATCH_MISMATCH,
    MATCH_PARTIAL,
    MATCH_UNAVAILABLE,
    MATCH_UNCERTAIN,
    readiness_category,
)

_MATCH_PENALTY = {
    MATCH_EXACT: 0, MATCH_COMPATIBLE: 5, MATCH_PARTIAL: 15, MATCH_UNCERTAIN: 20,
    MATCH_MISMATCH: 40, MATCH_UNAVAILABLE: 30,
}
_IMAGE_QUALITY_PENALTY = {
    IMAGE_QUALITY_EXCELLENT: 0, IMAGE_QUALITY_ACCEPTABLE: 5, IMAGE_QUALITY_LIMITED: 15, IMAGE_QUALITY_INSUFFICIENT: 30,
}
_COVERAGE_PENALTY = {
    "complete": 0, "acceptable": 5, "incomplete": 15, "insufficient": 30, "not_assessed": 20,
}
_IDENTITY_CONFIDENCE_PENALTY = {"high": 0, "moderate": 5, "low": 15}


def compute_evidence_readiness_score(
    *, match_classification: str, baseline_governance_status: str, image_quality_status: str, coverage_status: str,
    instrument_identity_confidence: str = "moderate", provenance_complete: bool = True,
    supervisor_validated: bool = False, model_compatible: bool = True, has_conflicts: bool = False,
) -> dict:
    breakdown: dict[str, int] = {}

    match_penalty = _MATCH_PENALTY.get(match_classification, 20)
    if match_penalty:
        breakdown["baseline_match_quality"] = -match_penalty

    if baseline_governance_status == BASELINE_STATUS_APPROVED:
        pass
    elif baseline_governance_status == BASELINE_STATUS_CONDITIONALLY_APPROVED:
        breakdown["baseline_governance_status"] = -10
    else:
        breakdown["baseline_governance_status"] = -25

    image_penalty = _IMAGE_QUALITY_PENALTY.get(image_quality_status, 15)
    if image_penalty:
        breakdown["image_quality"] = -image_penalty

    coverage_penalty = _COVERAGE_PENALTY.get(coverage_status, 20)
    if coverage_penalty:
        breakdown["anatomy_zone_coverage"] = -coverage_penalty

    identity_penalty = _IDENTITY_CONFIDENCE_PENALTY.get(instrument_identity_confidence, 10)
    if identity_penalty:
        breakdown["instrument_identity_confidence"] = -identity_penalty

    if not provenance_complete:
        breakdown["evidence_provenance_completeness"] = -10

    if not supervisor_validated:
        breakdown["supervisor_validation_status"] = -5

    if not model_compatible:
        breakdown["model_compatibility"] = -20

    if has_conflicts:
        breakdown["conflicting_evidence"] = -15

    score = max(0, min(100, 100 + sum(breakdown.values())))

    return {
        "readiness_score": float(score),
        "readiness_category": readiness_category(score),
        "score_breakdown": breakdown,
    }
