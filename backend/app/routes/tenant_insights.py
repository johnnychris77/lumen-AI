from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.tenant_insights import (
    get_tenant_insight,
    get_top_risk_tenant_insights,
    portfolio_insight_rollup,
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


router = APIRouter(prefix="/tenant-insights", tags=["tenant-insights"])


@router.get("/top-risks")
def top_risk_insights(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return get_top_risk_tenant_insights(db)


@router.get("/rollup")
def tenant_insight_rollup(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return portfolio_insight_rollup(db)


@router.get("/{tenant_id}")
def tenant_insight(
    tenant_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    insight = get_tenant_insight(db, tenant_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Tenant insight not found")

    return insight
