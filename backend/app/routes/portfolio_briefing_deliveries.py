from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.portfolio_briefing_delivery_transport import (
    execute_delivery_transport,
    get_delivery,
    list_deliveries,
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


router = APIRouter(
    prefix="/portfolio-briefing-deliveries",
    tags=["portfolio-briefing-deliveries"],
)


@router.get("")
def list_all_deliveries(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_deliveries(db)


@router.get("/failed")
def list_failed_deliveries(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_deliveries(db, status="retry_pending")


@router.get("/{delivery_id}")
def get_delivery_record(
    delivery_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    delivery = get_delivery(db, delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Portfolio briefing delivery not found")
    return delivery


@router.post("/{delivery_id}/retry")
def retry_delivery(
    delivery_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    try:
        return execute_delivery_transport(db, delivery_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
