from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import session as db_session
from app.enterprise_access_control import (
    access_governance_narrative,
    access_rollup,
    evaluate_access,
    list_access_decisions,
    policy_matrix,
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


router = APIRouter(prefix="/enterprise-access-control", tags=["enterprise-access-control"])


@router.get("/decisions")
def get_access_decisions(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return list_access_decisions(db)


@router.get("/rollup")
def get_access_rollup(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return access_rollup(db)


@router.get("/narrative")
def get_access_narrative(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    get_current_user(authorization)
    return access_governance_narrative(db)


@router.get("/policies")
def get_policy_matrix(
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    get_current_user(authorization)
    return policy_matrix()


@router.get("/check")
def check_policy(
    resource_type: str,
    action: str,
    x_lumenai_role: str | None = Header(default="viewer", alias="X-LumenAI-Role"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    get_current_user(authorization)
    return evaluate_access(x_lumenai_role or "viewer", resource_type, action)
