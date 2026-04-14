from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.scheduled_packet_service import run_scheduled_packet_once
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["scheduled-leadership-packets"])


class ScheduledPacketPayload(BaseModel):
    name: str
    briefing_type: str = "board_packet"
    audience: str = "executive"
    days: int = 30
    schedule_cron: str = "0 8 * * 1"
    delivery_channel: str = "email"
    delivery_target: str = ""
    include_docx: bool = True
    include_pptx: bool = True
    include_pdf: bool = True
    is_enabled: bool = True
    notes: str = ""


def _schedule_row(row: models.ScheduledLeadershipPacket) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "name": row.name,
        "briefing_type": row.briefing_type,
        "audience": row.audience,
        "days": row.days,
        "schedule_cron": row.schedule_cron,
        "delivery_channel": row.delivery_channel,
        "delivery_target": row.delivery_target,
        "include_docx": row.include_docx,
        "include_pptx": row.include_pptx,
        "include_pdf": row.include_pdf,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _delivery_row(row: models.LeadershipPacketDelivery) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "schedule_id": row.schedule_id,
        "briefing_id": row.briefing_id,
        "packet_id": row.packet_id,
        "delivery_channel": row.delivery_channel,
        "delivery_target": row.delivery_target,
        "delivery_status": row.delivery_status,
        "result_json": row.result_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/scheduled-leadership-packets")
def create_schedule(
    payload: ScheduledPacketPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.ScheduledLeadershipPacket(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        name=payload.name,
        briefing_type=payload.briefing_type,
        audience=payload.audience,
        days=payload.days,
        schedule_cron=payload.schedule_cron,
        delivery_channel=payload.delivery_channel,
        delivery_target=payload.delivery_target,
        include_docx=payload.include_docx,
        include_pptx=payload.include_pptx,
        include_pdf=payload.include_pdf,
        is_enabled=payload.is_enabled,
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="scheduled_leadership_packet_create",
        resource_type="scheduled_leadership_packet",
        resource_id=row.id,
        request=request,
        details=_schedule_row(row),
        compliance_flag=True,
    )

    return {"item": _schedule_row(row)}


@router.get("/scheduled-leadership-packets")
def list_schedules(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.ScheduledLeadershipPacket)
        .filter(models.ScheduledLeadershipPacket.tenant_id == tenant["tenant_id"])
        .order_by(models.ScheduledLeadershipPacket.id.desc())
        .all()
    )
    return {"items": [_schedule_row(r) for r in rows]}


@router.post("/scheduled-leadership-packets/{schedule_id}/run")
def run_schedule(
    schedule_id: int,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.ScheduledLeadershipPacket)
        .filter(
            models.ScheduledLeadershipPacket.id == schedule_id,
            models.ScheduledLeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Scheduled leadership packet not found")

    result = run_scheduled_packet_once(db, row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="scheduled_leadership_packet_run",
        resource_type="scheduled_leadership_packet",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/scheduled-leadership-packets/deliveries")
def list_deliveries(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.LeadershipPacketDelivery)
        .filter(models.LeadershipPacketDelivery.tenant_id == tenant["tenant_id"])
        .order_by(models.LeadershipPacketDelivery.id.desc())
        .limit(200)
        .all()
    )
    return {"items": [_delivery_row(r) for r in rows]}
