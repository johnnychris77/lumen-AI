from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from app.auth import get_current_user
from app.core.environment import is_production


GLOBAL_PORTFOLIO_ROLES = {"platform_admin", "portfolio_admin", "tenant_admin"}


def require_portfolio_access(
    current_user=Depends(get_current_user),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    user_email = (current_user or {}).get("user_email", "") or ""

    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()

    role_name = (current_user or {}).get("role_name", "") or ""

    allowed = False

    if role_name in GLOBAL_PORTFOLIO_ROLES:
        allowed = True

    # PA-1: the public literal development token never grants anything in
    # production. (The role/email checks above and below read keys the principal
    # does not carry, PA1-04; they are deliberately left as they are — "fixing"
    # them would activate all-tenant access, which needs a PA-1/GD-8 decision.)
    if token == "dev-token" and not is_production():
        allowed = True

    if user_email in {"admin@local", "portfolio@local", "platform@local"}:
        allowed = True

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"User '{user_email or 'unknown'}' is not authorized for portfolio access.",
        )

    return {
        "user_email": user_email,
        "role_name": role_name or "portfolio_admin",
        "portfolio_scope": "global",
    }
