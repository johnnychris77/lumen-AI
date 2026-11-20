from __future__ import annotations

import logging
import os

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.security.principal import (
    METHOD_DEVELOPMENT,
    METHOD_JWT,
    AuthenticatedPrincipal,
    TenantMembershipView,
)

from app.core.environment import is_production as _is_production  # noqa: E402

_ENABLE_DEV_AUTH = os.getenv("ENABLE_DEV_AUTH", "false").strip().lower() in {"1", "true", "yes"}

# Dev auth is only active in non-production environments when explicitly enabled.
# PA-1 (RB-T38): "production" is the canonical determination — APP_ENV **or**
# ENVIRONMENT names production — not APP_ENV alone.
_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and not _is_production()

_DEV_ROLE_MAP: dict[str, str] = {
    os.getenv("DEV_AUTH_TOKEN", ""): "admin",
    os.getenv("DEV_SPD_MANAGER_TOKEN", ""): "spd_manager",
    os.getenv("DEV_OPERATOR_TOKEN", ""): "operator",
    os.getenv("DEV_VENDOR_TOKEN", ""): "vendor_user",
    os.getenv("DEV_VIEWER_TOKEN", ""): "viewer",
} if _DEV_AUTH_ACTIVE else {}

# Remove blank-key entries that result from unset env vars
_DEV_ROLE_MAP = {k: v for k, v in _DEV_ROLE_MAP.items() if k}


def dev_token_role(token: str) -> str | None:
    """The development role for ``token``, or None.

    Every dev-token check goes through here. It re-reads the canonical production
    determination at call time, so a process whose environment says production
    never honours a development token, even if this module was imported earlier.
    """
    if not _DEV_AUTH_ACTIVE or _is_production():
        return None
    return _DEV_ROLE_MAP.get(token)


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


def _load_tenant_memberships(db: Session, email: str) -> tuple[TenantMembershipView, ...]:
    """Resolve a user's enabled tenant memberships from the database.

    This is the ONLY source of tenant authority for the principal — no client
    header can populate it. Reads the live model
    (``app.db.models.TenantMembership``: ``tenant_id`` / ``user_email`` /
    ``role`` / ``is_enabled``) directly — no phantom ``tenant_name``/``role_name``
    columns. Genuine operational failures (e.g. the table not yet created) fail
    CLOSED to no memberships — which ``resolve_verified_tenant`` then turns into a
    403 — but are LOGGED rather than swallowed silently, so a schema/programming
    error is visible instead of masquerading as "user has no tenants".
    """
    if not email:
        return ()
    from app.db import models

    try:
        rows = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == email,
                models.TenantMembership.is_enabled.is_(True),
            )
            .all()
        )
    except Exception:
        logging.getLogger(__name__).exception(
            "tenant-membership load failed; failing closed to no memberships",
        )
        return ()

    # The live model has no `tenant_name` column; surface the tenant_id as the
    # display name. `role` is the membership's role column.
    return tuple(
        TenantMembershipView(
            tenant_id=r.tenant_id,
            tenant_name=r.tenant_id,
            role_name=r.role,
        )
        for r in rows
    )


def _active_tenant(memberships: tuple[TenantMembershipView, ...]) -> str | None:
    """Deterministic active tenant when a user belongs to exactly one tenant.

    With multiple memberships the active tenant must be selected explicitly
    per-request (verified against membership by the tenant-context resolver);
    we do not guess one here.
    """
    tenant_ids = {m.tenant_id for m in memberships}
    if len(tenant_ids) == 1:
        return next(iter(tenant_ids))
    return None


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.split(" ", 1)[1].strip()

    # Dev token map — only active in development with ENABLE_DEV_AUTH=true.
    # Production disables this branch entirely (dev_token_role is None whenever
    # APP_ENV or ENVIRONMENT is production), so a dev token can never
    # authenticate in prod.
    role = dev_token_role(token)
    if role is not None:
        email = f"{role}@local.dev"
        memberships = _load_tenant_memberships(db, email)
        return AuthenticatedPrincipal(
            subject=email,
            email=email,
            username=email,
            role=role,
            authentication_method=METHOD_DEVELOPMENT,
            tenant_memberships=memberships,
            active_tenant_id=_active_tenant(memberships),
        )

    # JWT validation path (tokens issued by /auth/login in auth_simple)
    payload = _decode_jwt(token)
    if payload:
        username = payload.get("sub")
        if username:
            # Resolve the real role from the admin-managed assignment table
            # (falls back to users.role, then viewer).
            try:
                from app.routers.auth_simple import _user_role
                role = _user_role(username)
            except Exception:
                role = "viewer"
            memberships = _load_tenant_memberships(db, username)
            return AuthenticatedPrincipal(
                subject=username,
                email=username,
                username=username,
                role=role,
                authentication_method=METHOD_JWT,
                tenant_memberships=memberships,
                active_tenant_id=_active_tenant(memberships),
                token_id=payload.get("jti"),
                issued_at=payload.get("iat"),
                expires_at=payload.get("exp"),
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
