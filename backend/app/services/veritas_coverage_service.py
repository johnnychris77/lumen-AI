"""Project Veritas, Section 6: Inspection Coverage Assurance.

Wraps the real `inspection_coverage.compute_coverage` (required/inspected/
missing zones + a quality band that already maps almost 1:1 onto this
brief's coverage statuses) rather than re-deriving coverage. Adds only the
brief's explicit "identify high-risk zones captured" and duplicate-view
detection on top of the real engine's output.
"""
from __future__ import annotations

from collections import Counter

from app.models.veritas_evidence import COVERAGE_NOT_ASSESSED
from app.services.instrument_anatomy import get_anatomy
from app.services.inspection_coverage import compute_coverage

_QUALITY_TO_COVERAGE_STATUS = {
    "not_assessed": COVERAGE_NOT_ASSESSED,
    "complete": "complete",
    "acceptable": "acceptable",
    "incomplete": "incomplete",
    "insufficient": "insufficient",
}


def assess_coverage(instrument_type: str, inspected_zones: list[str] | None) -> dict:
    """Section 6: coverage assurance, built on the real coverage engine."""
    result = compute_coverage(instrument_type, inspected_zones)
    anatomy = get_anatomy(instrument_type)
    high_risk_zones = set(anatomy.get("high_risk_zones", []))

    inspected_norm = [z for z in (inspected_zones or [])]
    duplicate_views = [zone for zone, count in Counter(inspected_norm).items() if count > 1]
    high_risk_captured = sorted({z for z in result.get("inspected", []) if z in high_risk_zones})
    high_risk_missing = sorted({z for z in result.get("missing", []) if z in high_risk_zones})

    return {
        "assessed": result["assessed"],
        "coverage_pct": result["overall_coverage"],
        "coverage_status": _QUALITY_TO_COVERAGE_STATUS.get(result["quality"], COVERAGE_NOT_ASSESSED),
        "required_zones": result["required_zones"],
        "captured_zones": result["inspected"],
        "missing_zones": result["missing"],
        "high_risk_zones_captured": high_risk_captured,
        "high_risk_zones_missing": high_risk_missing,
        "duplicate_views": duplicate_views,
        "message": result["message"],
    }
