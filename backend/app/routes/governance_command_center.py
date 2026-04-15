from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.governance_command_center import (
    build_work_items,
    command_center_summary,
    resolve_sla_event,
    run_command_center_scan,
)
from app.packet_release_governance import request_packet_release
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["governance-command-center"])


class ResolveSlaPayload(BaseModel):
    event_id: int
    notes: str = ""


class RequestReleasePayload(BaseModel):
    packet_id: int
    attestation_text: str = ""


class HoldPayload(BaseModel):
    packet_id: int
    hold_type: str = "compliance"
    reason: str


class OverridePayload(BaseModel):
    packet_id: int
    justification: str
    override_type: str = "emergency_release"


@router.get("/governance-command-center/summary")
def summary(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return command_center_summary(db, tenant["tenant_id"], tenant["tenant_name"])


@router.get("/governance-command-center/work-items")
def work_items(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return build_work_items(db, tenant["tenant_id"], tenant["tenant_name"])


@router.post("/governance-command-center/actions/run-sla-scan")
def run_sla_scan(
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    result = run_command_center_scan()

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="command_center_run_sla_scan",
        resource_type="governance_command_center",
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/governance-command-center/actions/resolve-sla-event")
def resolve_sla(
    payload: ResolveSlaPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    result = resolve_sla_event(db, tenant["tenant_id"], payload.event_id, payload.notes)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="command_center_resolve_sla_event",
        resource_type="governance_sla_event",
        resource_id=payload.event_id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/governance-command-center/actions/request-release")
def request_release_action(
    payload: RequestReleasePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == payload.packet_id,
            models.LeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Leadership packet not found")

    row = request_packet_release(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=packet.id,
        packet_title=packet.title,
        audience_type=packet.packet_type,
        requested_by=current_user["user_email"],
        requested_role=current_user["role_name"],
        attestation_required=True,
        attestation_text=payload.attestation_text,
    )

    result = {"release_id": row.id, "packet_id": packet.id, "status": row.status}

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="command_center_request_release",
        resource_type="packet_release",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/governance-command-center/actions/create-hold")
def create_hold_action(
    payload: HoldPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == payload.packet_id,
            models.LeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Leadership packet not found")

    row = models.PacketReleaseHold(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=payload.packet_id,
        hold_type=payload.hold_type,
        reason=payload.reason,
        placed_by=current_user["user_email"],
        placed_role=current_user["role_name"],
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = {"hold_id": row.id, "packet_id": row.packet_id, "is_active": row.is_active}

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="command_center_create_hold",
        resource_type="packet_release_hold",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result


@router.post("/governance-command-center/actions/emergency-override")
def emergency_override_action(
    payload: OverridePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    packet = (
        db.query(models.LeadershipPacket)
        .filter(
            models.LeadershipPacket.id == payload.packet_id,
            models.LeadershipPacket.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not packet:
        raise HTTPException(status_code=404, detail="Leadership packet not found")

    row = models.PacketReleaseOverride(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        packet_id=payload.packet_id,
        override_type=payload.override_type,
        justification=payload.justification,
        approved_by=current_user["user_email"],
        approved_role=current_user["role_name"],
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    result = {"override_id": row.id, "packet_id": row.packet_id, "status": row.status}

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="command_center_emergency_override",
        resource_type="packet_release_override",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )
    return result
