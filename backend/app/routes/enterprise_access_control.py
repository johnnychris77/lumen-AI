from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request
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
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return list_access_decisions(db)


@router.get("/rollup")
def get_access_rollup(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return access_rollup(db)


@router.get("/narrative")
def get_access_narrative(
    request: Request,
    db: Session = Depends(get_db),
):
    get_current_user(request)
    return access_governance_narrative(db)


@router.get("/policies")
def get_policy_matrix(
    request: Request,
):
    get_current_user(request)
    return policy_matrix()


@router.get("/check")
def check_policy(
    request: Request,
    resource_type: str,
    action: str,
    as_role: str | None = None,
    x_lumenai_role: str | None = Header(default=None, alias="X-LumenAI-Role"),
):
    """Policy preview. Defaults to the AUTHENTICATED user's role.

    `as_role` (or the legacy X-LumenAI-Role header) is a what-if simulation
    input only — the response is a decision object and gates nothing, so
    simulating other roles is safe for an authenticated caller.
    """
    current = get_current_user(request)
    simulated = (as_role or x_lumenai_role or "").strip()
    effective_role = simulated or current.get("role", "viewer")
    result = evaluate_access(effective_role, resource_type, action)
    result["simulated"] = bool(simulated)
    result["authenticated_role"] = current.get("role", "viewer")
    return result
