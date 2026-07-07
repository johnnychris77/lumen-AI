"""v1.7 — Workflow Intelligence & Smart Work Queue.

- GET  /api/inspection-work-queue                     — Deliverable 1
- GET  /api/operations-board                          — Deliverable 5
- POST /api/inspections/{id}/assign                   — Deliverable 3
- GET  /api/inspections/{id}/assignments              — Deliverable 3 (history)
- GET  /api/inspections/{id}/workflow-state            — Deliverable 4 (history)
- POST /api/inspections/{id}/workflow/cancel           — Deliverable 4
- GET  /api/workflow/technician-workload               — Deliverable 3
- GET  /api/workflow/sla-monitoring                    — Deliverable 6
- GET  /api/workflow/escalations                       — Deliverable 7
- GET  /api/workflow/daily-dashboard                   — Deliverable 8
- GET  /api/workflow/shift-handoff                     — Deliverable 9
- GET  /api/workflow/notifications                     — Deliverable 10
- POST /api/workflow/notifications/generate            — Deliverable 10
- POST /api/workflow/notifications/{id}/read           — Deliverable 10
- GET  /api/workflow/analytics                         — Deliverable 11
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authz import require_roles
from app.db import models
from app.deps import get_db
from app.enterprise_auth import get_request_tenant_id
from app.services import workflow_state_service
from app.services.daily_operations_dashboard_service import daily_operations_dashboard
from app.services.escalation_engine import escalation_queue
from app.services.operational_analytics_service import operational_analytics
from app.services.operations_board_service import operations_board
from app.services.shift_handoff_service import shift_handoff_report
from app.services.sla_monitoring_service import sla_monitoring
from app.services.technician_workload_service import technician_workload
from app.services.work_queue_service import build_work_queue
from app.services.workflow_notification_service import (
    generate_workflow_notifications, list_notifications, mark_read,
)

router = APIRouter(tags=["workflow-intelligence"])

_ALL_ROLES = ("admin", "spd_manager", "operator", "viewer")
_LEADERSHIP_ROLES = ("admin", "spd_manager")


def _actor(user) -> str:
    return getattr(user, "email", None) or getattr(user, "username", "unknown")


def _tenant(current_user, request: Request) -> str:
    return getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)


def _get_inspection(db: Session, tenant_id: str, inspection_id: int):
    insp = (
        db.query(models.Inspection)
        .filter(models.Inspection.id == inspection_id, models.Inspection.tenant_id == tenant_id)
        .first()
    )
    if insp is None:
        raise HTTPException(status_code=404, detail="Inspection not found.")
    return insp


@router.get("/api/inspection-work-queue")
def get_inspection_work_queue(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return build_work_queue(db, _tenant(current_user, request))


@router.get("/api/operations-board")
def get_operations_board(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return operations_board(db, _tenant(current_user, request))


class AssignmentIn(BaseModel):
    technician: str = Field(..., min_length=1, max_length=255)
    note: str = Field("", max_length=500)


@router.post("/api/inspections/{inspection_id}/assign", status_code=201)
def post_assignment(
    inspection_id: int,
    body: AssignmentIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)

    row = workflow_state_service.assign_technician(
        db, insp=insp, tenant_id=tenant_id, technician=body.technician,
        assigned_by=_actor(current_user), note=body.note,
    )

    from app.services.workflow_notification_service import notify
    notify(
        db, tenant_id=tenant_id, inspection_id=inspection_id, notification_type="inspection_assigned",
        recipient_role="operator", recipient_name=body.technician,
        message=f"Inspection #{inspection_id} ({insp.instrument_type}) assigned to you.",
    )

    db.commit()
    db.refresh(row)
    return {"id": row.id, "inspection_id": row.inspection_id, "technician": row.technician, "assigned_by": row.assigned_by}


@router.get("/api/inspections/{inspection_id}/assignments")
def get_assignments(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    _get_inspection(db, tenant_id, inspection_id)
    from app.models.workflow import InspectionAssignment

    rows = (
        db.query(InspectionAssignment)
        .filter(InspectionAssignment.tenant_id == tenant_id, InspectionAssignment.inspection_id == inspection_id)
        .order_by(InspectionAssignment.id.desc())
        .all()
    )
    return {
        "assignments": [
            {
                "id": r.id, "technician": r.technician, "assigned_by": r.assigned_by, "note": r.note,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/api/inspections/{inspection_id}/workflow-state")
def get_workflow_state(
    inspection_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    history = workflow_state_service.state_history(db, inspection_id)
    return {
        "inspection_id": inspection_id,
        "current_state": workflow_state_service.current_state(db, insp),
        "history": [
            {
                "from_state": e.from_state, "to_state": e.to_state, "actor": e.actor, "reason": e.reason,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in history
        ],
    }


class CancelIn(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


@router.post("/api/inspections/{inspection_id}/workflow/cancel", status_code=201)
def post_cancel_inspection(
    inspection_id: int,
    body: CancelIn,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    insp = _get_inspection(db, tenant_id, inspection_id)
    event = workflow_state_service.cancel_inspection(
        db, insp=insp, tenant_id=tenant_id, actor=_actor(current_user), reason=body.reason,
    )
    db.commit()
    db.refresh(event)
    return {"inspection_id": inspection_id, "to_state": event.to_state, "reason": event.reason}


@router.get("/api/workflow/technician-workload")
def get_technician_workload(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return technician_workload(db, _tenant(current_user, request))


@router.get("/api/workflow/sla-monitoring")
def get_sla_monitoring(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return sla_monitoring(db, _tenant(current_user, request))


@router.get("/api/workflow/escalations")
def get_escalations(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return escalation_queue(db, _tenant(current_user, request))


@router.get("/api/workflow/daily-dashboard")
def get_daily_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    return daily_operations_dashboard(db, _tenant(current_user, request))


@router.get("/api/workflow/shift-handoff")
def get_shift_handoff(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return shift_handoff_report(db, _tenant(current_user, request), shift_actor=_actor(current_user))


@router.get("/api/workflow/notifications")
def get_notifications(
    request: Request,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    role = getattr(current_user, "role", "viewer")
    rows = list_notifications(db, tenant_id, recipient_role=role, unread_only=unread_only)
    return {
        "notifications": [
            {
                "id": n.id, "inspection_id": n.inspection_id, "notification_type": n.notification_type,
                "recipient_role": n.recipient_role, "recipient_name": n.recipient_name, "message": n.message,
                "read": n.read, "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in rows
        ],
    }


@router.post("/api/workflow/notifications/generate")
def post_generate_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return generate_workflow_notifications(db, _tenant(current_user, request))


@router.post("/api/workflow/notifications/{notification_id}/read")
def post_mark_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_ALL_ROLES)),
):
    tenant_id = _tenant(current_user, request)
    row = mark_read(db, tenant_id, notification_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    db.commit()
    return {"id": row.id, "read": row.read}


@router.get("/api/workflow/analytics")
def get_operational_analytics(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*_LEADERSHIP_ROLES)),
):
    return operational_analytics(db, _tenant(current_user, request), days=days)
