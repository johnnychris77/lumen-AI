"""v2.9 — LumenAI Quality (Project Guardian), Section 8: First Pass Yield
Intelligence.

True First Pass Yield: the fraction of PASS-dispositioned inspections with
no subsequently-confirmed OR quality event pointing back at them. False Pass
Yield is the complement — a PASS that a confirmed, supervisor-verified OR
event later showed had actually missed something.

LumenAI does not track reprocess-cycle/attempt-number lineage on
`Inspection` today, so this is scoped honestly to what the data actually
supports (pass vs. later-confirmed-miss), not a fabricated "attempt 1 vs
attempt 2" distinction the platform can't back with real records.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.models.quality_guardian import DISCLAIMER, EventCorrelation, FirstPassYieldSnapshot

_PASS_DISPOSITIONS = ("PASS",)


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def _confirmed_inspection_ids(db: Session, tenant_id: str) -> set[int]:
    """Inspection IDs with a supervisor-confirmed correlation to a
    confirmed quality event — i.e. a real OR-verified missed finding."""
    from app.models.quality_guardian import QualityEvent

    rows = (
        db.query(EventCorrelation.target_id)
        .join(QualityEvent, QualityEvent.id == EventCorrelation.event_id)
        .filter(
            EventCorrelation.tenant_id == tenant_id, EventCorrelation.target_type == "inspection",
            EventCorrelation.supervisor_confirmed.is_(True), QualityEvent.confirmed.is_(True),
        )
        .all()
    )
    return {int(r[0]) for r in rows if r[0]}


def compute_first_pass_yield(db: Session, tenant_id: str, *, scope_type: str, scope_value: str | None = None) -> dict:
    if scope_type not in ("department", "instrument", "technician", "facility"):
        raise ValueError("scope_type must be one of department, instrument, technician, facility")

    scope_field = {
        "department": models.Inspection.department, "instrument": models.Inspection.instrument_type,
        "technician": models.Inspection.technician, "facility": models.Inspection.facility_name,
    }[scope_type]

    q = db.query(models.Inspection).filter(
        models.Inspection.tenant_id == tenant_id, models.Inspection.disposition.in_(_PASS_DISPOSITIONS),
    )
    if scope_value is not None:
        q = q.filter(scope_field == scope_value)
    pass_inspections = q.all()

    confirmed_miss_ids = _confirmed_inspection_ids(db, tenant_id)
    total = len(pass_inspections)
    misses = sum(1 for i in pass_inspections if i.id in confirmed_miss_ids)
    true_first_pass = total - misses

    true_fpy_pct = round(100 * true_first_pass / total, 1) if total else 0.0
    false_pass_pct = round(100 * misses / total, 1) if total else 0.0

    snapshot = FirstPassYieldSnapshot(
        tenant_id=tenant_id, scope_type=scope_type, scope_value=scope_value or "all",
        total_pass_count=total, confirmed_miss_count=misses, true_fpy_pct=true_fpy_pct, false_pass_pct=false_pass_pct,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    result = _row_to_dict(snapshot)
    result["disclaimer"] = DISCLAIMER
    return result


def _distinct_values(db: Session, tenant_id: str, column) -> set[str]:
    return {
        r[0] for r in db.query(column)
        .filter(models.Inspection.tenant_id == tenant_id, models.Inspection.disposition.in_(_PASS_DISPOSITIONS))
        .distinct().all() if r[0]
    }


def compute_all_scopes(db: Session, tenant_id: str) -> dict:
    """Overall (tenant-wide) FPY plus Department/Instrument/Technician/
    Facility breakdowns, for the Executive Quality Dashboard."""
    overall = compute_first_pass_yield(db, tenant_id, scope_type="facility")

    by_department = [
        compute_first_pass_yield(db, tenant_id, scope_type="department", scope_value=v)
        for v in _distinct_values(db, tenant_id, models.Inspection.department)
    ]
    by_instrument = [
        compute_first_pass_yield(db, tenant_id, scope_type="instrument", scope_value=v)
        for v in _distinct_values(db, tenant_id, models.Inspection.instrument_type)
    ]
    by_technician = [
        compute_first_pass_yield(db, tenant_id, scope_type="technician", scope_value=v)
        for v in _distinct_values(db, tenant_id, models.Inspection.technician)
    ]
    by_facility = [
        compute_first_pass_yield(db, tenant_id, scope_type="facility", scope_value=v)
        for v in _distinct_values(db, tenant_id, models.Inspection.facility_name)
    ]

    return {
        "overall": overall, "by_department": by_department, "by_instrument": by_instrument,
        "by_technician": by_technician, "by_facility": by_facility, "disclaimer": DISCLAIMER,
    }
