import base64
import json
import os
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.context import AuthContext, build_dev_auth_context, build_oidc_auth_context
from app.auth.jwks_validator import (
    JWKSSignatureValidationError,
    validate_jwt_signature_with_jwks,
)
from app.auth.jwt_validator import (
    JWTValidationError,
    map_claims_to_auth_context_payload,
    validate_jwt_claims,
)
from app.auth.tenant_membership import require_enabled_tenant_membership
from app.core.environment import is_production


DEFAULT_DEV_TOKEN = "dev-token"
DEMO_TOKEN = "demo-token"


def is_demo_mode() -> bool:
    # PA-1: demo credentials never apply in production (canonical determination).
    return os.getenv("DEMO_MODE", "0").strip() == "1" and not is_production()


def get_auth_mode() -> str:
    return os.getenv("AUTH_MODE", "dev").strip().lower() or "dev"


def get_dev_token() -> str:
    return os.getenv("DEV_AUTH_TOKEN", DEFAULT_DEV_TOKEN)


def get_oidc_issuer() -> str:
    return os.getenv("OIDC_ISSUER_URL", "").strip()


def get_oidc_audience() -> str:
    return os.getenv("OIDC_AUDIENCE", "").strip()


def get_request_actor(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-actor")
        or request.headers.get("x-lumenai-user-email")
        or request.headers.get("x-user-email")
        or "unknown"
    )


def get_request_role(request: Request) -> str:
    return request.headers.get("x-lumenai-role", "")


def get_request_tenant_id(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-tenant-id")
        or request.headers.get("x-tenant-id")
        or "default-tenant"
    )


def get_request_tenant_name(request: Request) -> str:
    return (
        request.headers.get("x-lumenai-tenant-name")
        or request.headers.get("x-tenant-name")
        or get_request_tenant_id(request)
    )


def _verified_user_tenant(request: Request, db: Session, username: str) -> str:
    """The tenant a signed per-user JWT acts in. Fails closed (P472-03 AW-03/AW-06M).

    A tenant named in EITHER request header (``X-Tenant-Id`` or
    ``X-LumenAI-Tenant-Id``) is the caller's explicit selection and is honoured
    only when the user is an enabled member of it; two headers that disagree are
    refused. Previously only ``X-Tenant-Id`` counted as a selection, so a tenant
    named in ``X-LumenAI-Tenant-Id`` was never verified here, yet handlers later
    re-read that header and acted in it.

    With no tenant named, the user acts in their sole enabled membership. A user
    with no membership, or several and none selected, is refused: nothing is
    served from a header alone or from a shared ``default-tenant``. (Previously a
    multi-member user who sent no header passed a ``default-tenant`` membership
    check and was handed ``tenant_id=None``.)
    """
    from app.auth.tenant_membership import resolve_effective_tenant
    from app.auth.tenant_scope import NO_VERIFIED_TENANT_DETAIL, named_tenant

    explicit = named_tenant(request)
    if explicit:
        require_enabled_tenant_membership(db, tenant_id=explicit, user_email=username)
        return explicit
    effective = resolve_effective_tenant(db, user_email=username, requested_tenant_id=None)
    if not effective:
        raise HTTPException(status_code=403, detail=NO_VERIFIED_TENANT_DETAIL)
    return effective


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return token


def _decode_unverified_jwt_claims(token: str) -> dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT must have three segments.")

        payload_segment = parts[1]
        padded = payload_segment + "=" * (-len(payload_segment) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded.encode("utf-8"))
        claims = json.loads(payload_bytes.decode("utf-8"))

        if not isinstance(claims, dict):
            raise ValueError("JWT payload must decode to an object.")

        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid JWT.") from exc


def _require_dev_auth_context(
    request: Request,
    db: Session | None = None,
) -> AuthContext:
    authorization = request.headers.get("authorization", "")
    expected = f"Bearer {get_dev_token()}"

    # PA-1 (defence in depth): the static development token trusts client-supplied
    # actor / role / tenant headers. A production process refuses to start with
    # AUTH_MODE=dev (app.core.environment); if this path is reached in production
    # anyway (a worker or script that skipped app.main), the static token and the
    # demo token are never honoured. A signed per-user JWT (below) still is.
    if authorization == expected and not is_production():
        return build_dev_auth_context(
            actor=get_request_actor(request),
            role=get_request_role(request),
            tenant_id=get_request_tenant_id(request),
            tenant_name=get_request_tenant_name(request),
        )

    # Allow demo-token when DEMO_MODE=1
    if is_demo_mode() and authorization == f"Bearer {DEMO_TOKEN}":
        return build_dev_auth_context(
            actor="demo@lumenai.com",
            role=get_request_role(request) or "demo",
            tenant_id="demo",
            tenant_name="Demo Tenant",
        )

    # A real per-user JWT issued by /auth/login. Without this, no deployment
    # that hasn't explicitly configured AUTH_MODE=oidc can ever authenticate a
    # real logged-in user against enterprise-scoped routes — only the shared
    # dev/demo token works, which silently locks every real account out.
    # Role is resolved server-side from the validated `sub` claim, never from
    # a client-supplied header.
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        from app.deps import _decode_jwt

        payload = _decode_jwt(token)
        if payload and payload.get("sub"):
            username = str(payload["sub"])
            role = "viewer"
            try:
                from app.routers.auth_simple import _user_role

                role = _user_role(username) or "viewer"
            except Exception:
                pass

            tenant_id = get_request_tenant_id(request)
            if db is not None:
                tenant_id = _verified_user_tenant(request, db, username)

            return build_dev_auth_context(
                actor=username,
                role=role,
                tenant_id=tenant_id,
                tenant_name=get_request_tenant_name(request),
            )

    raise HTTPException(status_code=401, detail="Authentication required.")


def _require_oidc_auth_context(
    request: Request,
    db: Session | None = None,
) -> AuthContext:
    issuer = get_oidc_issuer()
    audience = get_oidc_audience()

    token = _extract_bearer_token(request)
    oidc_error: HTTPException | None = None

    if issuer and audience:
        try:
            claims = validate_jwt_signature_with_jwks(token)
            validated_claims = validate_jwt_claims(
                claims,
                expected_issuer=issuer,
                expected_audience=audience,
            )
            payload = map_claims_to_auth_context_payload(validated_claims)

            if db is not None:
                require_enabled_tenant_membership(
                    db,
                    tenant_id=payload["tenant_id"],
                    user_email=payload["actor"],
                )

            return build_oidc_auth_context(
                actor=payload["actor"],
                role=payload["role"],
                tenant_id=payload["tenant_id"],
                tenant_name=payload["tenant_name"],
                subject=payload["subject"],
                issuer=payload["issuer"],
                raw_claims=payload["raw_claims"],
            )
        except (JWKSSignatureValidationError, JWTValidationError) as exc:
            # Not a token issued by the configured OIDC provider -- remember
            # the specific reason and check whether it's instead a real
            # per-user JWT issued by /auth/login, below. If that check also
            # fails, this original OIDC error is what gets raised, so a
            # genuinely malformed/malicious OIDC token still gets a precise
            # rejection reason rather than a generic one.
            oidc_error = HTTPException(status_code=401, detail=str(exc))

    # A real per-user JWT issued by /auth/login. Without this fallback, a
    # deployment running AUTH_MODE=oidc rejects every logged-in user's own
    # token the instant a request reaches a route that resolves auth via
    # get_auth_context (e.g. the Atlas enterprise audit routes) -- even
    # though /auth/login just issued that exact token and every other route
    # (app/deps.py's get_current_user) accepts it fine. That mismatch is what
    # silently signs a user back out moments after a successful login: the
    # dashboard's other widgets succeed, one of these routes 401s, and the
    # frontend's global 401 handler tears down an otherwise-valid session.
    # This still requires a signature verified against the app's own signing
    # secret (see app.deps._decode_jwt) -- it does not weaken OIDC's own
    # verification, it only recognizes a second, already-real credential the
    # same way _require_dev_auth_context already does for AUTH_MODE=dev.
    from app.deps import _decode_jwt

    fallback_payload = _decode_jwt(token)
    if fallback_payload and fallback_payload.get("sub"):
        username = str(fallback_payload["sub"])
        role = "viewer"
        try:
            from app.routers.auth_simple import _user_role

            role = _user_role(username) or "viewer"
        except Exception:
            pass

        tenant_id = get_request_tenant_id(request)
        if db is not None:
            tenant_id = _verified_user_tenant(request, db, username)

        return build_dev_auth_context(
            actor=username,
            role=role,
            tenant_id=tenant_id,
            tenant_name=get_request_tenant_name(request),
        )

    if oidc_error is not None:
        raise oidc_error

    if not issuer or not audience:
        raise HTTPException(
            status_code=500,
            detail="OIDC authentication mode requires OIDC_ISSUER_URL and OIDC_AUDIENCE.",
        )

    raise HTTPException(status_code=401, detail="Invalid or unrecognized authentication token.")


def get_auth_context(
    request: Request,
    db: Session | None = None,
) -> AuthContext:
    auth_mode = get_auth_mode()

    if auth_mode == "dev":
        return _require_dev_auth_context(request, db=db)

    if auth_mode == "oidc":
        return _require_oidc_auth_context(request, db=db)

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported AUTH_MODE: {auth_mode}",
    )


# PA-1 (RB-T40): the JWT-shape check follows the canonical production
# determination (APP_ENV or ENVIRONMENT, case-insensitive), not
# ENVIRONMENT == "production" exactly. ``_AUTH_ENV`` is kept for existing readers.
_AUTH_ENV = "production" if is_production() else (os.getenv("ENVIRONMENT", "development").strip().lower()
                                                 or "development")


def require_enterprise_auth(
    request: Request,
    db: Session | None = None,
) -> AuthContext:
    # In production, reject non-JWT tokens (dev shortcuts like dev-token/test-token)
    if _AUTH_ENV == "production" or is_production():
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        parts = token.split(".")
        if len(parts) != 3:
            raise HTTPException(
                status_code=401,
                detail="Invalid token format. Production requires a signed JWT.",
            )

    if db is not None:
        return get_auth_context(request, db=db)

    # Callers across the codebase are inconsistent about threading their
    # request-scoped `db` session through to this function — dozens of
    # cross-hospital intelligence routes call require_enterprise_auth(request)
    # with no `db=`, which used to mean the TenantMembership check was
    # silently skipped and a client-supplied X-Tenant-Id header was trusted
    # outright. Rather than depend on every call site remembering to pass
    # `db=`, open a session here so the tenant-membership check always runs.
    from app.db import SessionLocal

    owned_db = SessionLocal()
    try:
        return get_auth_context(request, db=owned_db)
    finally:
        owned_db.close()


def require_enterprise_role(
    request: Request,
    *,
    allowed_roles: set[str],
    detail: str = "Access denied.",
    db: Session | None = None,
) -> AuthContext:
    auth_context = require_enterprise_auth(request, db=db)

    if not auth_context.has_role(allowed_roles):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context


def require_hospital_or_enterprise_admin(
    request: Request,
    *,
    detail: str = "Hospital or enterprise administrator access required.",
    db: Session | None = None,
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"hospital_admin", "enterprise_admin"},
        detail=detail,
        db=db,
    )


def require_vendor(
    request: Request,
    *,
    detail: str = "Vendor access required.",
    db: Session | None = None,
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"vendor"},
        detail=detail,
        db=db,
    )


def require_permission(
    request: Request,
    *,
    permission: str,
    detail: str = "Permission denied.",
    db: Session | None = None,
) -> AuthContext:
    auth_context = require_enterprise_auth(request, db=db)

    if not auth_context.has_permission(permission):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context


def require_governance_packet_export(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="governance_packet:export",
        detail="Governance packet export permission required.",
    )


def require_governance_packet_verify(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="governance_packet:verify",
        detail="Governance packet verification permission required.",
    )


def require_governance_packet_certificate(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="governance_packet:certificate",
        detail="Governance packet certificate permission required.",
    )


def require_vendor_baseline_submit(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="vendor_baseline:submit",
        detail="Vendor baseline submission permission required.",
    )


def require_vendor_baseline_approve(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="vendor_baseline:approve",
        detail="Vendor baseline approval permission required.",
    )


def require_vendor_baseline_audit_read(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="vendor_baseline:audit_read",
        detail="Vendor baseline audit-read permission required.",
    )


def require_vendor_baseline_library_read(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="vendor_baseline:library_read",
        detail="Vendor baseline library-read permission required.",
    )


MANUFACTURER_DENIED_DETAIL = "Access to the requested manufacturer is not permitted."
NO_MANUFACTURER_MEMBERSHIP_DETAIL = "No verified manufacturer membership for this request."


def _enabled_manufacturer_ids(user_email: str) -> set[str]:
    """The manufacturer / repair-partner organizations the user is an ENABLED,
    verified member of (P472-03 AW-07). Empty when the user has no membership."""
    user = (user_email or "").strip()
    if not user:
        return set()
    from app.db import SessionLocal
    from app.db.models import ManufacturerMembership

    from datetime import datetime, timezone

    from sqlalchemy import or_

    db = SessionLocal()
    try:
        rows = (
            db.query(ManufacturerMembership.manufacturer_id, ManufacturerMembership.expires_at)
            .filter(
                ManufacturerMembership.user_email == user,
                ManufacturerMembership.is_enabled.is_(True),
                # B5.2: an expired membership is no membership (fail closed).
                or_(ManufacturerMembership.expires_at.is_(None),
                    ManufacturerMembership.expires_at > datetime.now(timezone.utc)),
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        live = set()
        for manufacturer_id, expires_at in rows:
            if not manufacturer_id:
                continue
            # Re-check in Python: SQLite returns naive datetimes and compares them as text.
            if expires_at is not None:
                aware = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
                if aware <= now:
                    continue
            live.add(manufacturer_id)
        return live
    finally:
        db.close()


def require_manufacturer_auth(request: Request) -> str:
    """Auth for manufacturer / repair-partner portal endpoints (P472-03 AW-07).

    The manufacturer identity a request acts under is ALWAYS one the authenticated
    user is a verified, enabled member of — exactly as ``principal_tenant`` governs
    the tenant identity:

    * an ``X-Manufacturer-ID`` header is honoured only when the user is an enabled
      member of that organization; any other claimed organization is refused (403),
      never served from a different one;
    * with no header, the user acts in their sole manufacturer membership;
    * a user with no manufacturer membership, or several with none selected, is
      refused. The header is never trusted on its own, so a hospital user (or any
      user without a manufacturer relationship) can no longer assume a manufacturer
      identity by sending the header.

    Fails closed (403) for a missing, revoked or disabled membership — a disabled
    membership is no membership, since the query filters on ``is_enabled``.
    """
    # Authenticate the bearer token (401 on an invalid/missing token). This also
    # runs the tenant-membership check for the user's hospital identity.
    ctx = require_enterprise_auth(request)
    user = (getattr(ctx, "actor", "") or "").strip()

    claimed = request.headers.get("X-Manufacturer-ID", "").strip()
    memberships = _enabled_manufacturer_ids(user)

    if claimed:
        if claimed not in memberships:
            raise HTTPException(status_code=403, detail=MANUFACTURER_DENIED_DETAIL)
        return claimed
    if len(memberships) == 1:
        return next(iter(memberships))
    raise HTTPException(status_code=403, detail=NO_MANUFACTURER_MEMBERSHIP_DETAIL)


def require_audit_chain_verify(request: Request) -> AuthContext:
    return require_permission(
        request,
        permission="audit:verify_chain",
        detail="Audit chain verification permission required.",
    )
