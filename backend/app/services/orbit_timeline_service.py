"""v4.5 — Project Orbit, Section 6: Surgical Timeline.

Extends `or_connect_service.build_case_timeline`'s existing 7-step
timeline (Case Scheduled → Vendor Confirmed → Tray Received → Inspection
Complete → Supervisor Approved → Packaging → Ready for OR) to the
9-step sequence Section 6 asks for, by composing Symphony's own steps
with the new Orbit dimensions (case cart, and a terminal Procedure
Complete step) rather than re-deriving the shared steps a second way.

"Sterilization Status (visibility only)" is deliberately not a real
per-case cycle timestamp — no per-case sterilization-cycle tracking
exists anywhere in this codebase (the only sterilization concept is
P25's facility-level `sterilization_cycle_compliance` score). This step
surfaces that facility-level figure as read-only context and says so
explicitly, rather than fabricating a per-case sterilization event
LumenAI does not actually observe.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.orbit_readiness import CART_COMPLETE, CaseCart
from app.services import or_connect_service, p25_infrastructure_service


def build_surgical_timeline(db: Session, tenant_id: str, case_id: int) -> dict:
    base = or_connect_service.build_case_timeline(db, tenant_id, case_id)
    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)

    cart = (
        db.query(CaseCart).filter(CaseCart.tenant_id == tenant_id, CaseCart.case_id == case_id).order_by(CaseCart.id.desc()).first()
    )
    cart_complete = cart is not None and cart.status == CART_COMPLETE

    try:
        facility_readiness = p25_infrastructure_service.get_readiness_score(db, tenant_id, "facility", "facility")
        sterilization_note = (
            f"Facility-level sterilization cycle compliance: {round(facility_readiness.get('sterilization_cycle_compliance', 0) * 100)}% "
            "(visibility only — LumenAI does not track per-case sterilization cycles; see P25's Surgical Readiness Index)."
        )
    except Exception:
        sterilization_note = "Sterilization cycle data not available (visibility only — LumenAI does not manage sterilization)."

    steps = list(base["steps"])
    # Insert "Inventory Reserved" right after "Case Scheduled" — Symphony's
    # "Vendor Confirmed"/"Tray Received" steps already carry this signal;
    # Orbit's spec names it explicitly as its own step for the case-cart-
    # inclusive inventory picture.
    steps.insert(1, {
        "step": "Inventory Reserved", "completed": base["steps"][1]["completed"] or base["steps"][2]["completed"],
        "timestamp": base["steps"][2]["timestamp"],
    })
    # "Sterilization Status" is visibility-only — never marked "completed"
    # since LumenAI doesn't own or observe that process.
    steps.append({"step": "Sterilization Status (visibility only)", "completed": None, "timestamp": None, "note": sterilization_note})
    steps.append({"step": "Case Cart Complete", "completed": cart_complete, "timestamp": cart.verified_at.isoformat() if cart and cart.verified_at else None})
    steps.append({
        "step": "Procedure Complete", "completed": case.procedure_completed_at is not None,
        "timestamp": case.procedure_completed_at.isoformat() if case.procedure_completed_at else None,
    })
    # Rename Symphony's terminal step to Orbit's "OR Ready" wording.
    for s in steps:
        if s["step"] == "Ready for OR":
            s["step"] = "OR Ready"

    blockers = [{"step": s["step"], "reason": f"{s['step']} not yet complete.", "delayed": base["past_due"]} for s in steps if s["completed"] is False]

    return {
        "case_id": case_id, "case_ref": case.case_ref, "steps": steps, "blockers": blockers, "past_due": base["past_due"],
        "note": base["note"],
    }


def mark_procedure_complete(db: Session, tenant_id: str, case_id: int, *, completed_by: str) -> dict:
    from datetime import datetime, timezone

    case = or_connect_service.get_case_or_404(db, tenant_id, case_id)
    case.procedure_completed_by = completed_by
    case.procedure_completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)
    return {"case_id": case_id, "procedure_completed_at": case.procedure_completed_at.isoformat(), "procedure_completed_by": completed_by}
