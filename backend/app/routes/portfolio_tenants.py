from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.portfolio_tenants import (
    create_portfolio_tenant,
    generate_board_briefing_from_portfolio_tenants,
    get_portfolio_tenant,
    list_portfolio_tenants,
    portfolio_tenant_rollup,
    rescore_portfolio_tenants,
    update_portfolio_tenant,
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


router = APIRouter(prefix="/portfolio-tenants", tags=["portfolio-tenants"])


class PortfolioTenantCreatePayload(BaseModel):
    tenant_name: str
    industry: str = "healthcare"
    go_live_status: str = "not_started"
    renewal_risk: bool = False
    implementation_risk: bool = False
    governance_exception_count: int = 0
    last_qbr_date: str | None = None
    next_qbr_date: str | None = None
    executive_owner: str = ""
    customer_success_owner: str = ""
    notes: str = ""


class PortfolioTenantUpdatePayload(BaseModel):
    tenant_name: str | None = None
    industry: str | None = None
    go_live_status: str | None = None
    renewal_risk: bool | None = None
    implementation_risk: bool | None = None
    governance_exception_count: int | None = None
    last_qbr_date: str | None = None
    next_qbr_date: str | None = None
    executive_owner: str | None = None
    customer_success_owner: str | None = None
    notes: str | None = None


class PortfolioTenantBoardBriefingPayload(BaseModel):
    period_label: str = Field(default="Customer Portfolio Board Review")
    audience: str = Field(default="board")


@router.post("")
def create_tenant(
    payload: PortfolioTenantCreatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return create_portfolio_tenant(db=db, **payload.model_dump())


@router.get("")
def list_tenants(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_portfolio_tenants(db)


@router.get("/rollup")
def get_tenant_rollup(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return portfolio_tenant_rollup(db)


@router.post("/rescore")
def rescore_tenants(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return rescore_portfolio_tenants(db)


@router.post("/generate-board-briefing")
def generate_tenant_board_briefing(
    payload: PortfolioTenantBoardBriefingPayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return generate_board_briefing_from_portfolio_tenants(
        db=db,
        period_label=payload.period_label,
        audience=payload.audience,
    )


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    tenant = get_portfolio_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Portfolio tenant not found")

    return tenant


@router.patch("/{tenant_id}")
def update_tenant(
    tenant_id: int,
    payload: PortfolioTenantUpdatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    updates: dict[str, Any] = {
        key: value
        for key, value in payload.model_dump().items()
        if value is not None
    }

    tenant = update_portfolio_tenant(db, tenant_id, updates)
    if not tenant:
        raise HTTPException(status_code=404, detail="Portfolio tenant not found")

    return tenant
