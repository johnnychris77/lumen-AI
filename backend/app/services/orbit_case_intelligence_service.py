"""v4.5 — Project Orbit, Section 3: Case Intelligence.

Composes `or_connect_service.case_detail` (procedure/trays/inspection
status/clinical readiness/repair status/supervisor approval — already
real) with the genuinely new Orbit dimensions (implants, loaner
equipment, staff, environmental, case cart) and Digital Twin/knowledge
context, into the single per-case view Section 3 describes. No field
already produced by `case_detail` is recomputed here.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.or_connect import CaseRiskAlert
from app.models.orbit_readiness import CaseCart, EnvironmentalReadinessRecord, ImplantRecord, LoanerEquipment, StaffReadinessRecord
from app.services import digital_twin_engine, knowledge_repository_service, or_connect_service


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


def case_intelligence(db: Session, tenant_id: str, case_id: int, *, facility_id: str = "") -> dict:
    detail = or_connect_service.case_detail(db, tenant_id, case_id)

    implants = db.query(ImplantRecord).filter(ImplantRecord.tenant_id == tenant_id, ImplantRecord.case_id == case_id).all()
    equipment = db.query(LoanerEquipment).filter(LoanerEquipment.tenant_id == tenant_id, LoanerEquipment.case_id == case_id).all()
    staff = db.query(StaffReadinessRecord).filter(StaffReadinessRecord.tenant_id == tenant_id, StaffReadinessRecord.case_id == case_id).all()
    cart = (
        db.query(CaseCart).filter(CaseCart.tenant_id == tenant_id, CaseCart.case_id == case_id).order_by(CaseCart.id.desc()).first()
    )
    environmental = (
        db.query(EnvironmentalReadinessRecord)
        .filter(EnvironmentalReadinessRecord.tenant_id == tenant_id, EnvironmentalReadinessRecord.case_id == case_id)
        .order_by(EnvironmentalReadinessRecord.id.desc())
        .first()
    )
    risk_alerts = (
        db.query(CaseRiskAlert)
        .filter(CaseRiskAlert.tenant_id == tenant_id, CaseRiskAlert.case_id == case_id, CaseRiskAlert.resolved_at.is_(None))
        .order_by(CaseRiskAlert.id.desc())
        .all()
    )

    # Knowledge notes: real articles tagged to this case's procedure, never fabricated.
    knowledge_notes = knowledge_repository_service.list_articles(db, tenant_id, procedure=detail["procedure"], approval_status="approved")

    twin_dashboard = None
    if detail["digital_twins"]:
        twin_dashboard = digital_twin_engine.compute_twin_dashboard(tenant_id, facility_id, db).model_dump()

    return {
        **detail,
        "implants": [_row_to_dict(i) for i in implants],
        "loaner_equipment": [_row_to_dict(e) for e in equipment],
        "staff_assignments": [_row_to_dict(s) for s in staff],
        "case_cart": _row_to_dict(cart) if cart is not None else None,
        "environmental_readiness": _row_to_dict(environmental) if environmental is not None else None,
        "risk_alerts": [_row_to_dict(r) for r in risk_alerts],
        "knowledge_notes": knowledge_notes[:10],
        "digital_twin_status": twin_dashboard,
        "supervisor_holds": [] if detail["supervisor_approval"] == "approved" else ["Supervisor approval pending for this case."],
    }
