"""v2.4 — Learning Dashboard (Clinical Memory, Section 8).

Tenant-wide rollup of what the fleet's own history teaches: which finding
types recur most, which anatomy zones see repeated contamination, which
physical instruments are trending better or worse, and which are repeat
repair candidates. Built entirely from data already persisted
(`Inspection`, `InspectionFinding`) via
`instrument_condition_service.instrument_condition_history` — no new
detection model, no fabricated trend.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.db import models
from app.models.inspection_finding import InspectionFinding
from app.services.instrument_condition_service import instrument_condition_history
from app.services.pre_sterilization_command_center_service import _instrument_identity
from app.services.recurrence_detection_service import CONTAMINATION_TYPES

_TOP_N = 5
_RECURRENCE_THRESHOLD = 2


def _tracked_conditions(db: Session, tenant_id: str) -> dict[str, dict]:
    """Real re-identified instruments (barcode/UDI) with 2+ inspections —
    untracked singletons can't be trended, so they're excluded rather than
    faked into a one-point 'trend'."""
    rows = db.query(models.Inspection).filter(models.Inspection.tenant_id == tenant_id).all()
    by_identity: dict[str, list] = defaultdict(list)
    for row in rows:
        by_identity[_instrument_identity(row)].append(row)

    conditions: dict[str, dict] = {}
    for identity, insp_rows in by_identity.items():
        if identity.startswith("untracked:") or len(insp_rows) < 2:
            continue
        condition = instrument_condition_history(db, tenant_id, identity)
        if condition:
            conditions[identity] = condition
    return conditions


def _instrument_summary(identity: str, condition: dict) -> dict:
    return {
        "instrument_identity": identity,
        "instrument_type": condition["instrument_type"],
        "condition_trend": condition["condition_trend"],
        "inspection_count": condition["inspection_count"],
        "repair_count": condition["repair_count"],
        "corrosion_history_count": condition["corrosion_history_count"],
    }


def learning_dashboard(db: Session, tenant_id: str) -> dict:
    conditions = _tracked_conditions(db, tenant_id)

    most_improved = sorted(
        ((identity, c) for identity, c in conditions.items() if c["condition_trend"] == "improving"),
        key=lambda item: item[1]["inspection_count"],
        reverse=True,
    )[:_TOP_N]
    most_problematic = sorted(
        ((identity, c) for identity, c in conditions.items() if c["condition_trend"] == "declining"),
        key=lambda item: (item[1]["repair_count"], item[1]["corrosion_history_count"]),
        reverse=True,
    )[:_TOP_N]
    repeat_repair_candidates = sorted(
        ((identity, c) for identity, c in conditions.items() if c["repair_count"] >= _RECURRENCE_THRESHOLD),
        key=lambda item: item[1]["repair_count"],
        reverse=True,
    )[:_TOP_N]

    finding_rows = (
        db.query(InspectionFinding.finding_type, InspectionFinding.zone)
        .filter(InspectionFinding.tenant_id == tenant_id)
        .all()
    )
    finding_counts: dict[str, int] = defaultdict(int)
    contamination_zone_counts: dict[str, int] = defaultdict(int)
    for finding_type, zone in finding_rows:
        finding_counts[finding_type] += 1
        if finding_type in CONTAMINATION_TYPES:
            contamination_zone_counts[zone or "unspecified"] += 1

    recurring_findings = sorted(
        (
            {"finding_type": finding_type, "count": count}
            for finding_type, count in finding_counts.items()
            if count >= _RECURRENCE_THRESHOLD
        ),
        key=lambda x: x["count"], reverse=True,
    )[:10]
    repeated_contamination_zones = sorted(
        (
            {"zone": zone, "count": count}
            for zone, count in contamination_zone_counts.items()
            if count >= _RECURRENCE_THRESHOLD
        ),
        key=lambda x: x["count"], reverse=True,
    )[:10]

    return {
        "tracked_instrument_count": len(conditions),
        "recurring_findings": recurring_findings,
        "repeated_contamination_zones": repeated_contamination_zones,
        "most_improved_instruments": [_instrument_summary(i, c) for i, c in most_improved],
        "most_problematic_instruments": [_instrument_summary(i, c) for i, c in most_problematic],
        "repeat_repair_candidates": [_instrument_summary(i, c) for i, c in repeat_repair_candidates],
        "human_review_required": True,
    }
