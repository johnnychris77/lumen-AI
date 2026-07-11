"""Project Vulcan, Section 4: Anatomy-Zone Reliability Analysis.

Groups an instrument's real finding history (via `vulcan_progression_service`)
by anatomy zone, and attaches the real family-level "recommended manual
inspection" guidance already curated in `instrument_family_profiles.py`
(inspection_priorities / manual_steps) rather than inventing new guidance
text per zone.
"""
from __future__ import annotations

from app.services.instrument_anatomy import get_anatomy
from app.services.vulcan_failure_taxonomy_service import classify_finding_type
from app.services.vulcan_progression_service import findings_timeline


def _manual_inspection_guidance(instrument_type: str) -> list[str]:
    return get_anatomy(instrument_type).get("manual_steps", []) if instrument_type else []


def zone_reliability_analysis(db, tenant_id: str, instrument_identity: str, instrument_type: str) -> dict:
    """Section 4 output: one entry per zone that has real finding history."""
    timeline = findings_timeline(db, tenant_id, instrument_identity)
    zones = sorted({row["zone"] for row in timeline if row["zone"]})
    manual_steps = _manual_inspection_guidance(instrument_type)

    zone_reports = []
    for zone in zones:
        zone_timeline = [row for row in timeline if row["zone"] == zone]
        severities = [row["severity_index"] for row in zone_timeline]
        taxonomy = [classify_finding_type(row["finding_type"]) for row in zone_timeline]
        leaves = sorted({t["taxonomy_leaf"] for t in taxonomy})
        severity_trend = (
            "worsening" if len(severities) >= 2 and severities[-1] > severities[0]
            else "improving" if len(severities) >= 2 and severities[-1] < severities[0]
            else "stable"
        )
        zone_reports.append({
            "anatomy_zone": zone,
            "failure_categories": leaves,
            "recurrence_count": len(zone_timeline),
            "severity_trend": severity_trend,
            "latest_severity_index": severities[-1] if severities else 0,
            "recommended_manual_inspection": manual_steps,
        })

    zone_reports.sort(key=lambda z: z["recurrence_count"], reverse=True)
    return {
        "instrument_identity": instrument_identity,
        "instrument_type": instrument_type,
        "zones": zone_reports,
    }
