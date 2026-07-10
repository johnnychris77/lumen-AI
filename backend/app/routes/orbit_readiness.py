"""v4.5 — LumenAI OS: Project Orbit — Perioperative Intelligence &
Surgical Readiness Platform routes.

Frontend route: /surgical-readiness (rewritten in place — see
`app/models/orbit_readiness.py`'s naming-disambiguation note for why this
keeps the existing route name while moving the API to a new prefix).
API prefix: /api/orbit — deliberately NOT `/api/infrastructure` (P25's
prefix, a different "surgical readiness" axis).

Case identity/CRUD, vendor trays, and repairs remain owned by
`/api/or-connect` (Project Symphony) — Orbit does not duplicate case
creation, it composes Symphony's `SurgicalCase` by `case_id` and adds new
sub-resources (cart/implants/loaner-equipment/staff/environmental) plus
the readiness engine, alerts, timeline, coordination, executive
dashboard, procedure knowledge, and simulation on top of it.

  * GET  /cases                                                — case list enriched with latest readiness
  * POST /cases/{case_id}/cart, PATCH /cart/{id}                — Section 1 (Case Cart)
  * POST /cases/{case_id}/implants, PATCH /implants/{id}         — Section 1 (Implants)
  * POST /cases/{case_id}/loaner-equipment, PATCH /loaner-equipment/{id} — Section 1 (Equipment)
  * POST /cases/{case_id}/staff, PATCH /staff/{id}               — Section 1 (Staff)
  * POST /cases/{case_id}/environmental                          — Section 1 (Environmental)
  * GET  /case-readiness/{case_id}, GET /case-readiness/{case_id}/history — Section 1/10
  * GET  /cases/{case_id}/intelligence                           — Section 3
  * GET  /cases/{case_id}/coordination, POST /cases/{case_id}/coordinate,
    GET  /department-inbox                                       — Section 4
  * GET  /readiness-alerts/{case_id}                             — Section 5/10
  * GET  /cases/{case_id}/timeline, POST /cases/{case_id}/procedure-complete — Section 6
  * GET  /executive                                              — Section 7
  * GET  /procedure-intelligence                                 — Section 8/10
  * POST /cases/{case_id}/simulate/time-shift|instrument-unavailable|vendor-tray-delay,
    GET  /cases/{case_id}/simulations                            — Section 9
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.orbit_readiness import CART_STATUSES, IMPLANT_STATUSES, STAFF_STATUSES
from app.models.orbit_readiness import CaseCart, EnvironmentalReadinessRecord, ImplantRecord, LoanerEquipment, StaffReadinessRecord
from app.services import (
    or_connect_service,
    orbit_alert_service,
    orbit_case_intelligence_service,
    orbit_coordination_service,
    orbit_executive_service,
    orbit_procedure_knowledge_service,
    orbit_readiness_engine,
    orbit_simulation_service,
    orbit_timeline_service,
)
from app.services.or_connect_service import CaseNotFoundError

router = APIRouter(prefix="/api/orbit", tags=["orbit"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _audit(db: Session, tenant_id: str, actor: str, action_type: str, resource_type: str, resource_id: str, details: dict) -> None:
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=actor, actor_role="",
        action_type=action_type, resource_type=resource_type, resource_id=resource_id, details=details, compliance_flag=True,
    )


def _not_found(exc: CaseNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


def _row_to_dict(obj) -> dict:
    result: dict = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result


# ---------------------------------------------------------------------------
# Case list (enriched)
# ---------------------------------------------------------------------------


@router.get("/cases")
def get_cases(
    request: Request, target_date: str = Query(""), db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    from datetime import date as date_cls
    tenant_id = _tenant(current_user, request)
    parsed_date = date_cls.fromisoformat(target_date) if target_date else None
    cases = or_connect_service.list_cases(db, tenant_id, target_date=parsed_date)
    return {
        "cases": [
            {"id": c.id, "case_ref": c.case_ref, "procedure": c.procedure, "scheduled_start": c.scheduled_start.isoformat()}
            for c in cases
        ],
    }


# ---------------------------------------------------------------------------
# Section 1 — Case Cart, Implants, Loaner Equipment, Staff, Environmental
# ---------------------------------------------------------------------------


class CartIn(BaseModel):
    status: str = Field("not_started")
    item_count: int = 0
    notes: str = ""


@router.post("/cases/{case_id}/cart")
def post_cart(
    case_id: int, body: CartIn, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    if body.status not in CART_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {CART_STATUSES}")
    try:
        or_connect_service.get_case_or_404(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    cart = CaseCart(tenant_id=tenant_id, case_id=case_id, status=body.status, item_count=body.item_count, notes=body.notes)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return _row_to_dict(cart)


class ImplantIn(BaseModel):
    implant_name: str = Field(..., min_length=1, max_length=255)
    manufacturer: str = ""
    lot_number: str = ""
    status: str = Field("available")


@router.post("/cases/{case_id}/implants")
def post_implant(
    case_id: int, body: ImplantIn, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    if body.status not in IMPLANT_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {IMPLANT_STATUSES}")
    try:
        or_connect_service.get_case_or_404(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    row = ImplantRecord(
        tenant_id=tenant_id, case_id=case_id, implant_name=body.implant_name, manufacturer=body.manufacturer,
        lot_number=body.lot_number, status=body.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


class LoanerEquipmentIn(BaseModel):
    equipment_name: str = Field(..., min_length=1, max_length=255)
    vendor_name: str = ""
    status: str = Field("requested")


@router.post("/cases/{case_id}/loaner-equipment")
def post_loaner_equipment(
    case_id: int, body: LoanerEquipmentIn, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        or_connect_service.get_case_or_404(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    row = LoanerEquipment(tenant_id=tenant_id, case_id=case_id, equipment_name=body.equipment_name, vendor_name=body.vendor_name, status=body.status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


class StaffIn(BaseModel):
    staff_name: str = Field(..., min_length=1, max_length=255)
    staff_role: str = ""
    status: str = Field("not_assigned")


@router.post("/cases/{case_id}/staff")
def post_staff(
    case_id: int, body: StaffIn, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    if body.status not in STAFF_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {STAFF_STATUSES}")
    try:
        or_connect_service.get_case_or_404(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    row = StaffReadinessRecord(tenant_id=tenant_id, case_id=case_id, staff_name=body.staff_name, staff_role=body.staff_role, status=body.status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


class EnvironmentalIn(BaseModel):
    operating_room: str = ""
    room_turnover_complete: bool = False
    equipment_calibrated: bool = False
    supplies_stocked: bool = False
    notes: str = ""


@router.post("/cases/{case_id}/environmental")
def post_environmental(
    case_id: int, body: EnvironmentalIn, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        or_connect_service.get_case_or_404(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    row = EnvironmentalReadinessRecord(
        tenant_id=tenant_id, case_id=case_id, operating_room=body.operating_room,
        room_turnover_complete=body.room_turnover_complete, equipment_calibrated=body.equipment_calibrated,
        supplies_stocked=body.supplies_stocked, notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


class StatusPatch(BaseModel):
    status: str


def _patch_status(db: Session, tenant_id: str, model, row_id: int, status: str, valid_statuses: list[str] | None = None) -> dict:
    if valid_statuses is not None and status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"status must be one of {valid_statuses}")
    row = db.query(model).filter(model.id == row_id, model.tenant_id == tenant_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} {row_id} not found for tenant {tenant_id}.")
    row.status = status
    db.commit()
    db.refresh(row)
    return _row_to_dict(row)


@router.patch("/cart/{cart_id}")
def patch_cart(cart_id: int, body: StatusPatch, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return _patch_status(db, _tenant(current_user, request), CaseCart, cart_id, body.status, CART_STATUSES)


@router.patch("/implants/{implant_id}")
def patch_implant(implant_id: int, body: StatusPatch, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return _patch_status(db, _tenant(current_user, request), ImplantRecord, implant_id, body.status, IMPLANT_STATUSES)


@router.patch("/loaner-equipment/{equipment_id}")
def patch_loaner_equipment(equipment_id: int, body: StatusPatch, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return _patch_status(db, _tenant(current_user, request), LoanerEquipment, equipment_id, body.status)


@router.patch("/staff/{staff_id}")
def patch_staff(staff_id: int, body: StatusPatch, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES))):
    return _patch_status(db, _tenant(current_user, request), StaffReadinessRecord, staff_id, body.status, STAFF_STATUSES)


# ---------------------------------------------------------------------------
# Surgical Readiness Engine / Case Readiness
# ---------------------------------------------------------------------------


@router.get("/case-readiness/{case_id}")
def get_case_readiness(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/case-readiness/{case_id}/history")
def get_case_readiness_history(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"history": orbit_readiness_engine.readiness_history(db, tenant_id, case_id)}


@router.get("/surgical-readiness/{case_id}")
def get_surgical_readiness(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    """Alias of `/case-readiness/{case_id}` matching the brief's literal
    `/surgical-readiness` API name — both compute the same real score."""
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_readiness_engine.compute_surgical_readiness(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


# ---------------------------------------------------------------------------
# Section 3 — Case Intelligence
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/intelligence")
def get_case_intelligence(
    case_id: int, request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_case_intelligence_service.case_intelligence(db, tenant_id, case_id, facility_id=facility_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


# ---------------------------------------------------------------------------
# Section 4 — Cross-Department Coordination
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/coordination")
def get_case_coordination(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return orbit_coordination_service.department_coordination_timeline(db, tenant_id, case_id)


@router.post("/cases/{case_id}/coordinate")
def post_case_coordinate(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = orbit_coordination_service.coordinate_case(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    _audit(db, tenant_id, actor, "orbit.case_coordinated", "surgical_cases", str(case_id), {"notifications_sent": result["notifications_sent"]})
    return result


@router.get("/department-inbox")
def get_department_inbox(
    request: Request, department: str = Query(...), unread_only: bool = Query(False), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_coordination_service.department_inbox(db, tenant_id, department=department, unread_only=unread_only)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Section 5 — Readiness Alert Engine
# ---------------------------------------------------------------------------


@router.get("/readiness-alerts/{case_id}")
def get_readiness_alerts(
    case_id: int, request: Request, facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return {"alerts": orbit_alert_service.generate_readiness_alerts(db, tenant_id, case_id, facility_id=facility_id)}
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


# ---------------------------------------------------------------------------
# Section 6 — Surgical Timeline
# ---------------------------------------------------------------------------


@router.get("/cases/{case_id}/timeline")
def get_case_timeline(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_timeline_service.build_surgical_timeline(db, tenant_id, case_id)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/cases/{case_id}/procedure-complete")
def post_procedure_complete(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    actor = _actor(current_user)
    try:
        result = orbit_timeline_service.mark_procedure_complete(db, tenant_id, case_id, completed_by=actor)
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    _audit(db, tenant_id, actor, "orbit.procedure_completed", "surgical_cases", str(case_id), {})
    return result


# ---------------------------------------------------------------------------
# Section 7 — Executive Surgical Operations Dashboard
# ---------------------------------------------------------------------------


@router.get("/executive")
def get_executive(
    request: Request, facility_id: str = Query(""), days: int = Query(30, le=365), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return orbit_executive_service.executive_surgical_operations(db, tenant_id, facility_id=facility_id, days=days)


# ---------------------------------------------------------------------------
# Section 8 — Procedure Knowledge
# ---------------------------------------------------------------------------


@router.get("/procedure-intelligence")
def get_procedure_intelligence(
    request: Request, procedure: str = Query(...), facility_id: str = Query(""), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return orbit_procedure_knowledge_service.procedure_knowledge(db, tenant_id, procedure=procedure, facility_id=facility_id)


# ---------------------------------------------------------------------------
# Section 9 — Readiness Simulation
# ---------------------------------------------------------------------------


@router.post("/cases/{case_id}/simulate/time-shift")
def post_simulate_time_shift(
    case_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_simulation_service.simulate_case_time_shift(db, tenant_id, case_id, hours_shift=float(payload.get("hours_shift", 0)))
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/cases/{case_id}/simulate/instrument-unavailable")
def post_simulate_instrument_unavailable(
    case_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_simulation_service.simulate_instrument_unavailable(db, tenant_id, case_id, inspection_id=int(payload.get("inspection_id", 0)))
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/cases/{case_id}/simulate/vendor-tray-delay")
def post_simulate_vendor_tray_delay(
    case_id: int, payload: dict, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return orbit_simulation_service.simulate_vendor_tray_delayed(
            db, tenant_id, case_id, tray_id=int(payload.get("tray_id", 0)), delay_hours=float(payload.get("delay_hours", 0)),
        )
    except CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/cases/{case_id}/simulations")
def get_case_simulations(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return {"simulations": orbit_simulation_service.list_simulation_runs(db, tenant_id, case_id)}
