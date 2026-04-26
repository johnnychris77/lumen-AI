from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.executive_escalations import (
    executive_escalation_rollup,
    generate_governance_packet,
    list_executive_escalations,
    run_executive_escalation_scan,
    update_executive_escalation_status,
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


router = APIRouter(prefix="/executive-escalations", tags=["executive-escalations"])


@router.post("/run")
def run_escalation_scan(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return run_executive_escalation_scan(db)


@router.get("")
def list_escalations(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_executive_escalations(db)


@router.get("/open")
def list_open_escalations(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_executive_escalations(db, status="open")


@router.get("/rollup")
def get_escalation_rollup(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return executive_escalation_rollup(db)


@router.post("/generate-governance-packet")
def generate_packet(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return generate_governance_packet(db)


@router.post("/{escalation_id}/acknowledge")
def acknowledge_escalation(
    escalation_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    escalation = update_executive_escalation_status(db, escalation_id, "acknowledged")
    if not escalation:
        raise HTTPException(status_code=404, detail="Executive escalation not found")

    return escalation


@router.post("/{escalation_id}/close")
def close_escalation(
    escalation_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    escalation = update_executive_escalation_status(db, escalation_id, "closed")
    if not escalation:
        raise HTTPException(status_code=404, detail="Executive escalation not found")

    return escalation
