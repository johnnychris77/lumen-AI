"""Project Vulcan, Section 3: Failure Progression Model.

Tracks condition progression using real `InspectionFinding` rows (severity_index
0 none / 1 minor / 2 moderate / 3 severe, see
`baseline_comparison_scoring_service._severity_index`) for one physical
instrument, optionally scoped to one anatomy zone. Never fabricates a trend
when there isn't enough real history -- fewer than two matching findings
always yields `insufficient_history`.
"""
from __future__ import annotations

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.models.vulcan_reliability import (
    PROGRESSION_IMPROVING,
    PROGRESSION_INSUFFICIENT_HISTORY,
    PROGRESSION_INTERMITTENT,
    PROGRESSION_RAPIDLY_WORSENING,
    PROGRESSION_SLOWLY_WORSENING,
    PROGRESSION_STABLE,
    PROGRESSION_UNRESOLVED,
)


def _inspections_for_identity(db, tenant_id: str, instrument_identity: str) -> list:
    if instrument_identity.startswith("barcode:"):
        value = instrument_identity.removeprefix("barcode:")
        return (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_barcode == value)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )
    if instrument_identity.startswith("udi:"):
        value = instrument_identity.removeprefix("udi:")
        return (
            db.query(models.Inspection)
            .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.instrument_udi == value)
            .order_by(models.Inspection.created_at.asc())
            .all()
        )
    return []


def findings_timeline(db, tenant_id: str, instrument_identity: str, zone: str | None = None) -> list[dict]:
    """Real, time-ordered finding history for one instrument (optionally one zone)."""
    inspections = _inspections_for_identity(db, tenant_id, instrument_identity)
    if not inspections:
        return []
    inspection_by_id = {i.id: i for i in inspections}
    ids = list(inspection_by_id.keys())
    q = db.query(InspectionFinding).filter(InspectionFinding.inspection_id.in_(ids))
    if zone:
        q = q.filter(InspectionFinding.zone == zone)
    findings = q.all()
    timeline = []
    for f in findings:
        insp = inspection_by_id.get(f.inspection_id)
        timeline.append({
            "inspection_id": f.inspection_id,
            "created_at": insp.created_at if insp else f.created_at,
            "finding_type": f.finding_type,
            "zone": f.zone,
            "severity_index": f.severity_index,
        })
    timeline.sort(key=lambda row: row["created_at"])
    return timeline


def compute_progression(db, tenant_id: str, instrument_identity: str, zone: str | None = None) -> dict:
    """Classify progression for one instrument (+ optional zone) from real history."""
    timeline = findings_timeline(db, tenant_id, instrument_identity, zone=zone)
    recurrence_count = len(timeline)

    if recurrence_count < 2:
        return {
            "progression": PROGRESSION_INSUFFICIENT_HISTORY,
            "recurrence_count": recurrence_count,
            "severity_sequence": [row["severity_index"] for row in timeline],
            "days_span": 0,
            "confidence": "low",
            "evidence": timeline,
        }

    severities = [row["severity_index"] for row in timeline]
    first_at, last_at = timeline[0]["created_at"], timeline[-1]["created_at"]
    days_span = max(0, (last_at - first_at).days) if first_at and last_at else 0

    diffs = [b - a for a, b in zip(severities, severities[1:])]
    non_decreasing = all(d >= 0 for d in diffs)
    non_increasing = all(d <= 0 for d in diffs)
    net_change = severities[-1] - severities[0]

    if non_decreasing and net_change >= 2:
        progression = PROGRESSION_RAPIDLY_WORSENING
        confidence = "high"
    elif non_decreasing and net_change == 1:
        progression = PROGRESSION_SLOWLY_WORSENING
        confidence = "moderate"
    elif non_increasing and net_change < 0:
        progression = PROGRESSION_IMPROVING
        confidence = "moderate"
    elif non_decreasing and net_change == 0 and max(severities) >= 2:
        progression = PROGRESSION_UNRESOLVED
        confidence = "moderate"
    elif non_decreasing and net_change == 0:
        progression = PROGRESSION_STABLE
        confidence = "moderate"
    else:
        progression = PROGRESSION_INTERMITTENT
        confidence = "low"

    return {
        "progression": progression,
        "recurrence_count": recurrence_count,
        "severity_sequence": severities,
        "days_span": days_span,
        "confidence": confidence,
        "evidence": timeline,
    }
