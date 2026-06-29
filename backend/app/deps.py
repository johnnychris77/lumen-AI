from __future__ import annotations

import os
from types import SimpleNamespace

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.db import models

_ENABLE_DEV_AUTH = os.getenv("ENABLE_DEV_AUTH", "false").strip().lower() in {"1", "true", "yes"}
_APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

# Dev auth is only active in non-production environments when explicitly enabled.
_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and _APP_ENV not in {"production", "prod"}

_DEV_ROLE_MAP: dict[str, str] = {
    os.getenv("DEV_AUTH_TOKEN", ""): "admin",
    os.getenv("DEV_SPD_MANAGER_TOKEN", ""): "spd_manager",
    os.getenv("DEV_VENDOR_TOKEN", ""): "vendor_user",
    os.getenv("DEV_VIEWER_TOKEN", ""): "viewer",
} if _DEV_AUTH_ACTIVE else {}

# Remove blank-key entries that result from unset env vars
_DEV_ROLE_MAP = {k: v for k, v in _DEV_ROLE_MAP.items() if k}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _signing_secret() -> str | None:
    """Resolve the exact secret auth_simple uses to SIGN login tokens.

    auth_simple falls back to a fixed dev secret when SECRET_KEY is unset (in
    non-production). Decoding here must use the same value or every token it
    signs fails to decode — which silently 401s history/summary endpoints.
    """
    secret = os.getenv("SECRET_KEY")
    if secret:
        return secret
    try:
        # Import lazily to avoid import-time side effects / circular imports.
        from app.routers.auth_simple import SECRET_KEY as AUTH_SECRET
        return AUTH_SECRET or None
    except Exception:
        return None


def _decode_jwt(token: str):
    """Attempt to decode a JWT signed by auth_simple's SECRET_KEY."""
    try:
        import jwt as pyjwt
        secret = _signing_secret()
        if not secret:
            return None
        payload = pyjwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except Exception:
        return None


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()

    # Dev token map — only active in development with ENABLE_DEV_AUTH=true
    if _DEV_AUTH_ACTIVE and token in _DEV_ROLE_MAP:
        role = _DEV_ROLE_MAP[token]
        return SimpleNamespace(
            id=0,
            email=f"{role}@local.dev",
            role=role,
        )

    # JWT validation path (tokens issued by /auth/login in auth_simple)
    payload = _decode_jwt(token)
    if payload:
        username = payload.get("sub")
        if username:
            user = (
                db.query(models.User)
                .filter(models.User.username == username)
                .first()
            )
            if user:
                return user
            # Return a namespace if user row doesn't exist but JWT is valid
            return SimpleNamespace(id=0, email=username, role="viewer")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
