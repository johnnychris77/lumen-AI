"""v1.7 — Intelligent Prioritization Engine (Deliverable 2).

Ranks inspection work automatically. Each contributing factor is
point-scored and returned with its reason — auditable, mirroring the same
rubric style already used by risk_stratification_service.py — over
signals produced by the existing readiness/disposition engines (v1.6) plus
real intake data (procedure_priority, vendor/tray, prior findings). Never
a fabricated urgency guess: a factor with no real signal simply contributes
no points.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.instrument_anatomy import get_anatomy, resolve_family
from app.services.pre_sterilization_command_center_service import _instrument_identity

CRITICAL = "Critical"
HIGH = "High"
MEDIUM = "Medium"
LOW = "Low"
PRIORITY_TIERS = [CRITICAL, HIGH, MEDIUM, LOW]

_PROCEDURE_POINTS = {"emergency": 4, "trauma": 3, "first_case": 2}


def has_repeat_findings(db: Session, tenant_id: str, insp) -> bool:
    """Whether this physical instrument has any prior logged finding — a
    real repeat-condition signal (v1.5's InspectionFinding log), not a guess."""
    from app.db import models
    from app.models.inspection_finding import InspectionFinding

    identity = _instrument_identity(insp)
    if identity.startswith("untracked:"):
        return False

    barcode_filter = (
        (models.Inspection.instrument_barcode == insp.instrument_barcode)
        if insp.instrument_barcode
        else (models.Inspection.instrument_udi == insp.instrument_udi)
    )
    prior_ids = [
        r[0] for r in db.query(models.Inspection.id).filter(
            models.Inspection.tenant_id == tenant_id, barcode_filter, models.Inspection.id != insp.id,
        ).all()
    ]
    if not prior_ids:
        return False
    return (
        db.query(InspectionFinding.id)
        .filter(InspectionFinding.inspection_id.in_(prior_ids))
        .first()
        is not None
    )


def is_vendor_tray(insp) -> bool:
    return bool(insp.vendor_name and insp.vendor_name != "unknown" and insp.tray_id)


def is_supervisor_escalated(db: Session, tenant_id: str, insp) -> bool:
    from app.models.disposition_override import DispositionOverride

    latest = (
        db.query(DispositionOverride)
        .filter(DispositionOverride.tenant_id == tenant_id, DispositionOverride.inspection_id == insp.id)
        .order_by(DispositionOverride.id.desc())
        .first()
    )
    return bool(latest and latest.action == "escalate")


def _has_high_risk_anatomy(insp) -> bool:
    family = resolve_family(insp.instrument_type)
    if family == "default":
        return False
    anatomy = get_anatomy(insp.instrument_type)
    return any(z.get("zone_risk_level") in ("high", "critical") for z in anatomy.get("zones", []))


def compute_priority(
    db: Session, tenant_id: str, insp, *, readiness: dict, disposition: dict, repair_history: bool,
) -> dict:
    """Deliverable 2 — Priority Score (points) + tier, with the contributing
    reasons that produced it, so the ranking is auditable rather than a
    black box."""
    points = 0
    reasons: list[str] = []

    procedure_priority = (insp.procedure_priority or "").strip().lower()
    if procedure_priority in _PROCEDURE_POINTS:
        points += _PROCEDURE_POINTS[procedure_priority]
        reasons.append(f"Procedure priority: {procedure_priority.replace('_', ' ')}.")

    if readiness.get("is_critical_finding"):
        points += 3
        reasons.append("Critical finding on this inspection.")

    if _has_high_risk_anatomy(insp):
        points += 2
        reasons.append(f"High-risk anatomy family ({resolve_family(insp.instrument_type)}).")

    if repair_history:
        points += 2
        reasons.append("Prior repair/remove-from-service history on this instrument.")

    if disposition.get("disposition") in ("Repair Evaluation", "Manufacturer Evaluation"):
        points += 2
        reasons.append("Repair return awaiting evaluation.")

    if has_repeat_findings(db, tenant_id, insp):
        points += 1
        reasons.append("Repeat findings recorded on this instrument.")

    if is_vendor_tray(insp):
        points += 1
        reasons.append("Vendor tray instrument.")

    if insp.is_loaner_instrument:
        points += 1
        reasons.append("Loaner instrument.")

    if is_supervisor_escalated(db, tenant_id, insp):
        points += 3
        reasons.append("Supervisor escalation on record.")

    if points >= 8:
        tier = CRITICAL
    elif points >= 5:
        tier = HIGH
    elif points >= 2:
        tier = MEDIUM
    else:
        tier = LOW

    return {"priority_score": points, "priority_tier": tier, "reasons": reasons}
