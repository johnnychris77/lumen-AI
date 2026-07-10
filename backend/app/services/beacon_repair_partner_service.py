"""v3.5 — Project Beacon, Section 3: Repair Partner Portal.

Extends `or_connect_vendor_service.py`'s real-identity-filtered query
pattern (every function there filters real rows by `vendor_name`, never a
mock) rather than the mock `manufacturer_portal.py` pattern. The one
genuine difference: `or_connect_vendor_service.vendor_portal_view` is
scoped to a single tenant (one hospital's own vendor portal); a repair
vendor legitimately services many hospitals, so every function here
filters `RepairRequest`/`VendorTray` by `vendor_name` alone, across every
tenant — a vendor already knows which hospital shipped them an
instrument in real life, so this is not a cross-tenant de-identification
boundary, unlike the Manufacturer Intelligence Portal's aggregate
network views.

"Repair outcomes update Digital Twins" (Section 3) is implemented by
reusing `digital_twin_engine.log_instrument_flow` + `complete_flow`
directly — never a raw `InstrumentFlowRecord` construction.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.or_connect import DISCLAIMER, REPAIR_REPLACED, REPAIR_RETURNED, RepairRequest
from app.services import digital_twin_engine
from app.services.or_connect_service import _row_to_dict

_FAILED_CATEGORIES = {"corrosion", "mechanical_wear", "manufacturing_defect"}


def repair_history(db: Session, vendor_id: str) -> list[dict]:
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.vendor_name == vendor_id)
        .order_by(RepairRequest.id.desc())
        .all()
    )
    return [_row_to_dict(r) for r in repairs]


def repair_referrals(db: Session, vendor_id: str, *, status: str = "") -> list[dict]:
    q = db.query(RepairRequest).filter(RepairRequest.vendor_name == vendor_id)
    if status:
        q = q.filter(RepairRequest.status == status)
    return [_row_to_dict(r) for r in q.order_by(RepairRequest.id.desc()).all()]


def failure_category_breakdown(db: Session, vendor_id: str) -> dict:
    repairs = db.query(RepairRequest).filter(RepairRequest.vendor_name == vendor_id).all()
    by_category: dict[str, int] = {}
    for r in repairs:
        key = r.failure_category or "uncategorized"
        by_category[key] = by_category.get(key, 0) + 1
    return {"total_repairs": len(repairs), "failure_categories": by_category}


def repair_turnaround(db: Session, vendor_id: str) -> dict:
    repairs = (
        db.query(RepairRequest)
        .filter(RepairRequest.vendor_name == vendor_id, RepairRequest.actual_return_date.isnot(None))
        .all()
    )
    if not repairs:
        return {"completed_repairs": 0, "avg_turnaround_days": None}
    days = [(r.actual_return_date - r.created_at).days for r in repairs]
    return {"completed_repairs": len(repairs), "avg_turnaround_days": round(sum(days) / len(days), 1)}


def repeat_repair_analysis(db: Session, vendor_id: str) -> dict:
    """Instruments this vendor has repaired more than once — a real signal
    of recurring failure, not a fabricated recurrence score."""
    repairs = db.query(RepairRequest).filter(RepairRequest.vendor_name == vendor_id).all()
    by_instrument: dict[str, int] = {}
    for r in repairs:
        if r.instrument_identity:
            by_instrument[r.instrument_identity] = by_instrument.get(r.instrument_identity, 0) + 1
    repeats = {k: v for k, v in by_instrument.items() if v > 1}
    return {
        "instruments_with_repeat_repairs": repeats,
        "repeat_repair_rate": round(len(repeats) / len(by_instrument), 4) if by_instrument else None,
    }


def digital_twin_history(db: Session, vendor_id: str, instrument_identity: str) -> list[dict]:
    """Digital Twin flow history for one instrument this vendor has
    serviced — reuses `digital_twin_engine.list_recent_flows` rather than
    querying `InstrumentFlowRecord` directly here."""
    owns = db.query(RepairRequest.id).filter(
        RepairRequest.vendor_name == vendor_id, RepairRequest.instrument_identity == instrument_identity,
    ).first()
    if owns is None:
        return []
    from app.models.digital_twin import InstrumentFlowRecord
    rows = (
        db.query(InstrumentFlowRecord)
        .filter(InstrumentFlowRecord.instrument_name == instrument_identity)
        .order_by(InstrumentFlowRecord.arrived_at.desc())
        .all()
    )
    return [
        {
            "tenant_id": r.tenant_id, "to_station": r.to_station, "station_type": r.station_type,
            "arrived_at": r.arrived_at.isoformat() if r.arrived_at else None, "outcome": r.outcome, "notes": r.notes,
        }
        for r in rows
    ]


def record_repair_outcome(db: Session, vendor_id: str, repair_id: int, *, notes: str = "") -> dict:
    """Called when a repair is returned/replaced — updates the instrument's
    Digital Twin flow history with the real repair outcome."""
    repair = db.query(RepairRequest).filter(RepairRequest.id == repair_id, RepairRequest.vendor_name == vendor_id).first()
    if repair is None:
        raise ValueError(f"Repair request {repair_id} not found for vendor {vendor_id}.")
    if repair.status not in (REPAIR_RETURNED, REPAIR_REPLACED):
        raise ValueError(f"Repair request {repair_id} is '{repair.status}' — outcome can only be recorded once returned or replaced.")

    twin_outcome = "failed" if (repair.failure_category in _FAILED_CATEGORIES) else "passed"
    flow = digital_twin_engine.log_instrument_flow(
        repair.tenant_id, "", repair.instrument_identity, str(repair.id),
        "vendor_repair", "returned_to_service", "repair_return", notes, db,
    )
    digital_twin_engine.complete_flow(flow.id, twin_outcome, notes, repair.tenant_id, db)

    return {
        "repair_id": repair.id,
        "instrument_identity": repair.instrument_identity,
        "digital_twin_outcome": twin_outcome,
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }


def repair_partner_portal_view(db: Session, vendor_id: str) -> dict:
    return {
        "vendor_id": vendor_id,
        "repair_history": repair_history(db, vendor_id),
        "failure_categories": failure_category_breakdown(db, vendor_id),
        "turnaround": repair_turnaround(db, vendor_id),
        "repeat_repair_analysis": repeat_repair_analysis(db, vendor_id),
        "human_review_required": True,
        "disclaimer": DISCLAIMER,
    }
