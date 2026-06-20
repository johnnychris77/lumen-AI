from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.tenant_remediations import (
    create_remediations_from_tenant_insight,
    create_tenant_remediation,
    get_tenant_remediation,
    list_tenant_remediations,
    remediation_rollup,
    update_tenant_remediation,
)


def get_db():
    if hasattr(db_session, "get_db"):
        yield from db_session.get_db()
        return

    if hasattr(db_session, "get_session"):
        yield from db_session.get_session()
        return

    if hasattr(db_session, "SessionLocal"):
        db = db_session.SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    raise RuntimeError("No database session provider found in app.db.session")


router = APIRouter(prefix="/tenant-remediations", tags=["tenant-remediations"])


class TenantRemediationCreatePayload(BaseModel):
    tenant_id: int
    action_title: str
    action_description: str = ""
    owner: str = ""
    due_date: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    status: Literal["open", "in_progress", "blocked", "escalated", "closed"] = "open"
    escalation_level: int = Field(default=0, ge=0)
    risk_source: str = "manual"


class TenantRemediationUpdatePayload(BaseModel):
    action_title: str | None = None
    action_description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    status: Literal["open", "in_progress", "blocked", "escalated", "closed"] | None = None
    escalation_level: int | None = None
    risk_source: str | None = None


@router.post("")
def create_remediation(
    request: Request,
    payload: TenantRemediationCreatePayload,
    db: Session = Depends(get_db),
):
    get_current_user(request)

    try:
        return create_tenant_remediation(db=db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
def list_remediations(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return list_tenant_remediations(db)


@router.get("/rollup")
def get_remediation_rollup(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return remediation_rollup(db)


@router.get("/open")
def list_open_remediations(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return list_tenant_remediations(db, status="open")


@router.get("/overdue")
def list_overdue_remediations(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return list_tenant_remediations(db, overdue_only=True)


@router.post("/from-insight/{tenant_id}")
def create_from_insight(
    request: Request,
    tenant_id: int,
    db: Session = Depends(get_db),
):
    get_current_user(request)

    try:
        return create_remediations_from_tenant_insight(db, tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{remediation_id}")
def get_remediation(
    request: Request,
    remediation_id: int,
    db: Session = Depends(get_db),
):
    get_current_user(request)

    remediation = get_tenant_remediation(db, remediation_id)
    if not remediation:
        raise HTTPException(status_code=404, detail="Tenant remediation not found")

    return remediation


@router.patch("/{remediation_id}")
def update_remediation(
    request: Request,
    remediation_id: int,
    payload: TenantRemediationUpdatePayload,
    db: Session = Depends(get_db),
):
    get_current_user(request)

    updates: dict[str, Any] = {
        key: value
        for key, value in payload.model_dump().items()
        if value is not None
    }

    remediation = update_tenant_remediation(db, remediation_id, updates)
    if not remediation:
        raise HTTPException(status_code=404, detail="Tenant remediation not found")

    return remediation


@router.post("/{remediation_id}/close")
def close_remediation(
    request: Request,
    remediation_id: int,
    db: Session = Depends(get_db),
):
    get_current_user(request)

    remediation = update_tenant_remediation(db, remediation_id, {"status": "closed"})
    if not remediation:
        raise HTTPException(status_code=404, detail="Tenant remediation not found")

    return remediation
