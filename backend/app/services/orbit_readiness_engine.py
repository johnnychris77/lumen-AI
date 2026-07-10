"""v4.5 — Project Orbit, Section 1: Surgical Readiness Engine.

Computes one composite Surgical Readiness Score per `SurgicalCase`,
spanning nine dimensions: Patient Procedure → Case Cart → Instrument
Trays → Individual Instruments → Implants → Equipment → Staff →
Environmental → Clinical.

This never re-derives instrument/tray/inspection/supervisor logic —
`or_connect_service.compute_case_readiness_score`'s own 8-factor
breakdown (already computed from real `Inspection`/`VendorTray`/
`RepairRequest`/`SupervisorReview` rows) supplies three of Orbit's nine
dimensions directly. Only the genuinely new dimensions (case cart,
implants, loaner equipment, staff, environmental) are computed here from
this sprint's own new tables.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.or_connect import SurgicalCase
from app.models.orbit_readiness import (
    CART_ASSEMBLED,
    CART_ASSEMBLING,
    CART_COMPLETE,
    CART_NOT_STARTED,
    CART_VERIFIED,
    DISCLAIMER,
    IMPLANT_AVAILABLE,
    IMPLANT_VERIFIED,
    STAFF_READY,
    CaseCart,
    EnvironmentalReadinessRecord,
    ImplantRecord,
    LoanerEquipment,
    StaffReadinessRecord,
    SurgicalReadinessSnapshot,
)
from app.services import or_connect_service

_CART_STATUS_SCORE = {
    CART_NOT_STARTED: 0.0, CART_ASSEMBLING: 0.4, CART_ASSEMBLED: 0.7, CART_VERIFIED: 0.9, CART_COMPLETE: 1.0,
}

# ── Dimension weights (sum to 100) ───────────────────────────────────────────
_WEIGHTS = {
    "patient_procedure_score": 10,
    "case_cart_score": 10,
    "instrument_tray_score": 15,
    "individual_instrument_score": 20,
    "implant_score": 10,
    "equipment_score": 10,
    "staff_score": 10,
    "environmental_score": 10,
    "clinical_score": 5,
}


def _ratio(numerator: int, denominator: int) -> float:
    """1.0 (not blocking) when nothing of this kind is required yet — the
    same convention `or_connect_service._ratio` already established."""
    return 1.0 if denominator == 0 else numerator / denominator


def _patient_procedure_score(case: SurgicalCase) -> float:
    if case.procedure and case.service_line and case.surgeon:
        return 1.0
    if case.procedure:
        return 0.5
    return 0.0


def _case_cart_score(db: Session, tenant_id: str, case_id: int) -> float:
    cart = (
        db.query(CaseCart)
        .filter(CaseCart.tenant_id == tenant_id, CaseCart.case_id == case_id)
        .order_by(CaseCart.id.desc())
        .first()
    )
    return _CART_STATUS_SCORE[cart.status] if cart is not None else 0.0


def _implant_score(db: Session, tenant_id: str, case_id: int) -> float:
    implants = db.query(ImplantRecord).filter(ImplantRecord.tenant_id == tenant_id, ImplantRecord.case_id == case_id).all()
    ready = sum(1 for i in implants if i.status in (IMPLANT_AVAILABLE, IMPLANT_VERIFIED))
    return _ratio(ready, len(implants))


def _equipment_score(db: Session, tenant_id: str, case_id: int) -> float:
    equipment = db.query(LoanerEquipment).filter(LoanerEquipment.tenant_id == tenant_id, LoanerEquipment.case_id == case_id).all()
    ready = sum(1 for e in equipment if e.status in ("received", "returned"))
    return _ratio(ready, len(equipment))


def _staff_score(db: Session, tenant_id: str, case_id: int) -> float:
    staff = db.query(StaffReadinessRecord).filter(StaffReadinessRecord.tenant_id == tenant_id, StaffReadinessRecord.case_id == case_id).all()
    ready = sum(1 for s in staff if s.status == STAFF_READY)
    return _ratio(ready, len(staff))


def _environmental_score(db: Session, tenant_id: str, case_id: int) -> float:
    record = (
        db.query(EnvironmentalReadinessRecord)
        .filter(EnvironmentalReadinessRecord.tenant_id == tenant_id, EnvironmentalReadinessRecord.case_id == case_id)
        .order_by(EnvironmentalReadinessRecord.id.desc())
        .first()
    )
    if record is None:
        return 0.0
    checks = [record.room_turnover_complete, record.equipment_calibrated, record.supplies_stocked]
    return sum(1 for c in checks if c) / len(checks)


def compute_surgical_readiness(db: Session, tenant_id: str, case_id: int) -> dict:
    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    or_connect_score = or_connect_service.compute_case_readiness_score(db, tenant_id, case_id)
    factors = or_connect_score["factors"]

    def _factor(*names: str) -> float:
        values = [factors[n]["value"] for n in names]
        return sum(values) / len(values)

    dimensions = {
        "patient_procedure_score": _patient_procedure_score(case),
        "case_cart_score": _case_cart_score(db, tenant_id, case_id),
        "instrument_tray_score": _factor("vendor_tray_arrival", "specialty_equipment_available"),
        "individual_instrument_score": _factor(
            "instrument_readiness", "inspection_completion", "coverage_completion", "baseline_verification", "repair_completion",
        ),
        "implant_score": _implant_score(db, tenant_id, case_id),
        "equipment_score": _equipment_score(db, tenant_id, case_id),
        "staff_score": _staff_score(db, tenant_id, case_id),
        "environmental_score": _environmental_score(db, tenant_id, case_id),
        "clinical_score": factors["supervisor_approvals"]["value"],
    }

    overall = round(sum(_WEIGHTS[name] * value for name, value in dimensions.items()))

    rationale_parts = [
        f"{name.replace('_', ' ')} is {round(value * 100)}% (worth {_WEIGHTS[name]} pts)."
        for name, value in dimensions.items() if value < 1.0
    ]
    rationale = " ".join(rationale_parts) or "All nine readiness dimensions are fully satisfied."

    factor_breakdown = {
        name: {"weight": _WEIGHTS[name], "value": round(value, 3), "points": round(_WEIGHTS[name] * value, 2)}
        for name, value in dimensions.items()
    }

    snapshot = SurgicalReadinessSnapshot(
        tenant_id=tenant_id, case_id=case_id, overall_score=overall, factors_json=json.dumps(factor_breakdown),
        rationale=rationale, **dimensions,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return {
        "id": snapshot.id, "case_id": case_id, "case_ref": case.case_ref, "overall_score": overall,
        "dimensions": factor_breakdown, "rationale": rationale, "or_connect_readiness_score": or_connect_score["score"],
        "human_review_required": True, "disclaimer": DISCLAIMER,
    }


def readiness_history(db: Session, tenant_id: str, case_id: int, *, limit: int = 30) -> list[dict]:
    rows = (
        db.query(SurgicalReadinessSnapshot)
        .filter(SurgicalReadinessSnapshot.tenant_id == tenant_id, SurgicalReadinessSnapshot.case_id == case_id)
        .order_by(SurgicalReadinessSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": r.id, "created_at": r.created_at.isoformat(), "overall_score": r.overall_score, "factors": json.loads(r.factors_json)}
        for r in rows
    ]
