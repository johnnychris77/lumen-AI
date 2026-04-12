from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.deps import get_db
from app.db import models
from app.notification_templates import get_template, render_template
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["notification-templates"])


class NotificationTemplatePayload(BaseModel):
    template_key: str
    channel: str
    subject_template: str = ""
    body_template: str
    is_enabled: bool = True
    notes: str = ""


class NotificationTemplatePreviewPayload(BaseModel):
    template_key: str
    channel: str
    context: dict


def _row(row: models.NotificationTemplate) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "template_key": row.template_key,
        "channel": row.channel,
        "subject_template": row.subject_template,
        "body_template": row.body_template,
        "is_enabled": row.is_enabled,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/notification-templates")
def list_templates(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.NotificationTemplate)
        .filter(models.NotificationTemplate.tenant_id == tenant["tenant_id"])
        .order_by(models.NotificationTemplate.id.desc())
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.post("/notification-templates")
def create_template(
    payload: NotificationTemplatePayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin")),
):
    row = models.NotificationTemplate(
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        template_key=payload.template_key,
        channel=payload.channel,
        subject_template=payload.subject_template,
        body_template=payload.body_template,
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
        action_type="notification_template_create",
        resource_type="notification_template",
        resource_id=row.id,
        request=request,
        details=_row(row),
        compliance_flag=True,
    )

    return {"item": _row(row)}


@router.get("/notification-templates/{template_key}/{channel}")
def get_template_route(
    template_key: str,
    channel: str,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    return get_template(db, tenant["tenant_id"], tenant["tenant_name"], template_key, channel)


@router.post("/notification-templates/render")
def render_template_route(
    payload: NotificationTemplatePreviewPayload,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    merged = {"tenant_id": tenant["tenant_id"], "tenant_name": tenant["tenant_name"], **payload.context}
    return render_template(db, tenant["tenant_id"], tenant["tenant_name"], payload.template_key, payload.channel, merged)
