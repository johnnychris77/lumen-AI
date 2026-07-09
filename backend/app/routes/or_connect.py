"""v2.8 — LumenAI OR Connect: Perioperative Coordination Engine routes.

Route: /case-intelligence (frontend). API prefix: /api/or-connect.

  * POST /api/or-connect/cases                              — Section 1
  * GET  /api/or-connect/cases                               — Section 1/6
  * GET  /api/or-connect/cases/{case_id}                     — Section 1
  * POST /api/or-connect/cases/{case_id}/link-inspection       — Section 1
  * POST /api/or-connect/cases/{case_id}/approve              — Section 1
  * POST /api/or-connect/cases/{case_id}/trays                — Section 1
  * PATCH /api/or-connect/trays/{tray_id}                     — Section 1
  * GET  /api/or-connect/cases/{case_id}/readiness-score      — Section 2
  * GET  /api/or-connect/cases/{case_id}/timeline             — Section 3
  * GET  /api/or-connect/cases/{case_id}/risks                — Section 4
  * POST /api/or-connect/cases/{case_id}/notifications/generate — Section 5
  * GET  /api/or-connect/notifications                        — Section 5
  * POST /api/or-connect/notifications/{id}/read              — Section 5
  * GET  /api/or-connect/dashboard                            — Section 6
  * POST /api/or-connect/repairs                              — Section 8
  * PATCH /api/or-connect/repairs/{repair_id}                 — Section 8
  * GET  /api/or-connect/clinical-engineering                 — Section 8
  * GET  /api/or-connect/executive-dashboard                  — Section 9
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.authz import require_roles
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.models.or_connect import STAKEHOLDER_ROLES
from app.services import or_connect_service as engine

router = APIRouter(prefix="/api/or-connect", tags=["or-connect"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _actor(current_user) -> str:
    return getattr(current_user, "email", None) or getattr(current_user, "username", "unknown")


def _not_found(exc: engine.CaseNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


class CaseIn(BaseModel):
    procedure: str = Field(..., min_length=1, max_length=255)
    scheduled_start: datetime
    service_line: str = ""
    surgeon: str = ""
    facility_name: str = ""
    operating_room: str = ""
    vendor_name: str = ""
    notes: str = ""


class TrayIn(BaseModel):
    tray_name: str = Field(..., min_length=1, max_length=255)
    vendor_name: str = ""
    tray_label: str = ""
    is_vendor_tray: bool = True


class TrayStatusIn(BaseModel):
    status: str = Field(..., pattern="^(requested|shipped|received|returned)$")


class ApprovalIn(BaseModel):
    approved: bool = True


class RepairIn(BaseModel):
    inspection_id: int
    case_id: int | None = None
    vendor_name: str = ""
    repair_type: str = ""
    expected_return_date: datetime | None = None
    notes: str = ""


class RepairUpdateIn(BaseModel):
    status: str | None = Field(default=None, pattern="^(pending|in_progress|returned|replaced)$")
    actual_return_date: datetime | None = None
    replacement_available: bool | None = None


@router.post("/cases", status_code=201)
def post_case(
    body: CaseIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    case = engine.create_case(db, tenant_id, **body.model_dump())
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="or_connect.case_created", resource_type="surgical_case", resource_id=str(case.id),
        details={"case_ref": case.case_ref, "procedure": case.procedure},
    )
    return engine._row_to_dict(case)


@router.get("/cases")
def get_cases(
    request: Request, target_date: date | None = Query(default=None), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    cases = engine.list_cases(db, tenant_id, target_date=target_date)
    return {"cases": [engine._row_to_dict(c) for c in cases]}


@router.get("/dashboard")
def get_dashboard(
    request: Request, target_date: date | None = Query(default=None), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return engine.dashboard_summary(db, tenant_id, target_date=target_date)


@router.get("/executive-dashboard")
def get_executive_dashboard(
    request: Request, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return engine.executive_dashboard(db, tenant_id, days=days)


@router.get("/clinical-engineering")
def get_clinical_engineering(
    request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    return engine.clinical_engineering_summary(db, tenant_id)


@router.post("/repairs", status_code=201)
def post_repair(
    body: RepairIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.create_repair_request(db, tenant_id, **body.model_dump())
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.patch("/repairs/{repair_id}")
def patch_repair(
    repair_id: int, body: RepairUpdateIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.update_repair_request(db, tenant_id, repair_id, **body.model_dump())
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/notifications")
def get_notifications(
    request: Request, recipient_role: str = Query(...), unread_only: bool = Query(default=False),
    db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    if recipient_role not in STAKEHOLDER_ROLES:
        raise HTTPException(status_code=422, detail=f"recipient_role must be one of {STAKEHOLDER_ROLES}")
    tenant_id = _tenant(current_user, request)
    return {"notifications": engine.list_case_notifications(db, tenant_id, recipient_role=recipient_role, unread_only=unread_only)}


@router.post("/notifications/{notification_id}/read")
def post_mark_read(
    notification_id: int, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    result = engine.mark_notification_read(db, tenant_id, notification_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found.")
    return result


@router.post("/cases/{case_id}/link-inspection")
def post_link_inspection(
    case_id: int, request: Request, inspection_id: int = Query(...), db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        insp = engine.link_inspection_to_case(db, tenant_id, case_id, inspection_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    return {"inspection_id": insp.id, "case_id": case_id}


@router.post("/cases/{case_id}/approve")
def post_approve_case(
    case_id: int, body: ApprovalIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        case = engine._get_case(db, tenant_id, case_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    case.supervisor_approved = body.approved
    case.supervisor_approved_by = _actor(current_user)
    case.supervisor_approved_at = datetime.now(timezone.utc) if body.approved else None
    db.commit()
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="or_connect.case_approved", resource_type="surgical_case", resource_id=str(case_id),
        details={"approved": body.approved},
    )
    return engine._row_to_dict(case)


@router.post("/cases/{case_id}/trays", status_code=201)
def post_tray(
    case_id: int, body: TrayIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        tray = engine.add_vendor_tray(db, tenant_id, case_id, **body.model_dump())
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    return engine._row_to_dict(tray)


@router.patch("/trays/{tray_id}")
def patch_tray(
    tray_id: int, body: TrayStatusIn, request: Request, db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        tray = engine.update_tray_status(db, tenant_id, tray_id, status=body.status)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    return engine._row_to_dict(tray)


@router.get("/cases/{case_id}/readiness-score")
def get_readiness_score(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.compute_case_readiness_score(db, tenant_id, case_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/cases/{case_id}/timeline")
def get_timeline(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.build_case_timeline(db, tenant_id, case_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.get("/cases/{case_id}/risks")
def get_risks(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return {"risks": engine.detect_operational_risks(db, tenant_id, case_id)}
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/cases/{case_id}/notifications/generate")
def post_generate_notifications(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        created = engine.generate_stakeholder_notifications(db, tenant_id, case_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
    log_audit_event(
        db, tenant_id=tenant_id, tenant_name=tenant_id, actor_email=_actor(current_user), actor_role="",
        action_type="or_connect.notifications_generated", resource_type="surgical_case", resource_id=str(case_id),
        details={"created_count": len(created)},
    )
    return {"notifications": created}


@router.get("/cases/{case_id}")
def get_case(
    case_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    try:
        return engine.case_detail(db, tenant_id, case_id)
    except engine.CaseNotFoundError as exc:
        raise _not_found(exc) from exc
