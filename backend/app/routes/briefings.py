from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.audit import log_audit_event
from app.briefing_generator import generate_briefing
from app.deps import get_db
from app.db import models
from app.tenant import resolve_tenant
from app.tenant_authz import require_tenant_roles

router = APIRouter(tags=["briefings"])


class BriefingPayload(BaseModel):
    briefing_type: str = "board_packet"
    audience: str = "executive"
    period_label: str = ""
    days: int = 30


def _row(row: models.GeneratedBriefing) -> dict:
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "tenant_name": row.tenant_name,
        "briefing_type": row.briefing_type,
        "audience": row.audience,
        "period_label": row.period_label,
        "title": row.title,
        "slide_outline_json": row.slide_outline_json,
        "memo_text": row.memo_text,
        "summary_json": row.summary_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.get("/briefings")
def list_briefings(
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    rows = (
        db.query(models.GeneratedBriefing)
        .filter(models.GeneratedBriefing.tenant_id == tenant["tenant_id"])
        .order_by(models.GeneratedBriefing.id.desc())
        .limit(100)
        .all()
    )
    return {"items": [_row(r) for r in rows]}


@router.post("/briefings/generate")
def generate_briefing_route(
    payload: BriefingPayload,
    request: Request,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    period_label = payload.period_label or f"Last {payload.days} Days"
    row = generate_briefing(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        briefing_type=payload.briefing_type,
        audience=payload.audience,
        period_label=period_label,
        days=payload.days,
    )

    result = _row(row)

    log_audit_event(
        db,
        tenant_id=tenant["tenant_id"],
        tenant_name=tenant["tenant_name"],
        actor_email=current_user["user_email"],
        actor_role=current_user["role_name"],
        action_type="briefing_generate",
        resource_type="generated_briefing",
        resource_id=row.id,
        request=request,
        details=result,
        compliance_flag=True,
    )

    return result


@router.get("/briefings/{briefing_id}")
def get_briefing(
    briefing_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.GeneratedBriefing)
        .filter(
            models.GeneratedBriefing.id == briefing_id,
            models.GeneratedBriefing.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return _row(row)


@router.get("/briefings/{briefing_id}/slide-outline")
def get_briefing_slides(
    briefing_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.GeneratedBriefing)
        .filter(
            models.GeneratedBriefing.id == briefing_id,
            models.GeneratedBriefing.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Briefing not found")

    return JSONResponse({
        "id": row.id,
        "title": row.title,
        "slides": json.loads(row.slide_outline_json or "[]"),
    })


@router.get("/briefings/{briefing_id}/memo")
def get_briefing_memo(
    briefing_id: int,
    tenant: dict = Depends(resolve_tenant),
    db: Session = Depends(get_db),
    current_user=Depends(require_tenant_roles("tenant_admin", "site_admin")),
):
    row = (
        db.query(models.GeneratedBriefing)
        .filter(
            models.GeneratedBriefing.id == briefing_id,
            models.GeneratedBriefing.tenant_id == tenant["tenant_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Briefing not found")

    return {
        "id": row.id,
        "title": row.title,
        "memo": row.memo_text,
    }
