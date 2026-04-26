from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.executive_decisions import (
    create_decision_from_escalation,
    create_executive_decision,
    executive_decision_rollup,
    get_executive_decision,
    governance_decision_narrative,
    list_executive_decisions,
    update_executive_decision,
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


router = APIRouter(prefix="/executive-decisions", tags=["executive-decisions"])


class ExecutiveDecisionCreatePayload(BaseModel):
    decision_title: str
    decision_description: str = ""
    decision_owner: str = ""
    due_date: str | None = None
    priority: Literal["low", "medium", "high", "critical"] = "high"
    status: Literal["proposed", "approved", "in_progress", "blocked", "completed"] = "proposed"
    leadership_decision_required: bool = True
    source_type: str = "manual"
    source_id: int | None = None
    tenant_id: int | None = None
    escalation_id: int | None = None
    packet_id: int | None = None


class ExecutiveDecisionUpdatePayload(BaseModel):
    decision_title: str | None = None
    decision_description: str | None = None
    decision_owner: str | None = None
    due_date: str | None = None
    priority: Literal["low", "medium", "high", "critical"] | None = None
    status: Literal["proposed", "approved", "in_progress", "blocked", "completed"] | None = None
    leadership_decision_required: bool | None = None


@router.post("")
def create_decision(
    payload: ExecutiveDecisionCreatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return create_executive_decision(db=db, **payload.model_dump())


@router.get("")
def list_decisions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_executive_decisions(db)


@router.get("/open")
def list_open_decisions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return [
        item for item in list_executive_decisions(db)
        if item.get("status") != "completed"
    ]


@router.get("/overdue")
def list_overdue_decisions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_executive_decisions(db, overdue_only=True)


@router.get("/rollup")
def get_decision_rollup(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return executive_decision_rollup(db)


@router.get("/narrative")
def get_decision_narrative(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return governance_decision_narrative(db)


@router.post("/from-escalation/{escalation_id}")
def create_from_escalation(
    escalation_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    try:
        return create_decision_from_escalation(db, escalation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{decision_id}")
def get_decision(
    decision_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    decision = get_executive_decision(db, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Executive decision not found")

    return decision


@router.patch("/{decision_id}")
def update_decision(
    decision_id: int,
    payload: ExecutiveDecisionUpdatePayload,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    updates: dict[str, Any] = {
        key: value
        for key, value in payload.model_dump().items()
        if value is not None
    }

    decision = update_executive_decision(db, decision_id, updates)
    if not decision:
        raise HTTPException(status_code=404, detail="Executive decision not found")

    return decision


@router.post("/{decision_id}/approve")
def approve_decision(
    decision_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    decision = update_executive_decision(db, decision_id, {"status": "approved"})
    if not decision:
        raise HTTPException(status_code=404, detail="Executive decision not found")

    return decision


@router.post("/{decision_id}/complete")
def complete_decision(
    decision_id: int,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)

    decision = update_executive_decision(db, decision_id, {"status": "completed", "leadership_decision_required": False})
    if not decision:
        raise HTTPException(status_code=404, detail="Executive decision not found")

    return decision
