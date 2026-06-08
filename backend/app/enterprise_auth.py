import base64
import json
import os
from typing import Any

from fastapi import HTTPException, Request

from app.auth.context import AuthContext, build_dev_auth_context, build_oidc_auth_context
from app.auth.jwt_validator import (
    JWTValidationError,
    map_claims_to_auth_context_payload,
    validate_jwt_claims,
)


DEFAULT_DEV_TOKEN = "dev-token"


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


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return token


def _decode_unverified_jwt_claims(token: str) -> dict[str, Any]:
    """
    Decode JWT claims without signature verification.

    This is an interim bridge for AUTH_MODE=oidc. Full JWKS signature validation
    is the next hardening step. Do not use this as final production validation.
    """
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


def _require_dev_auth_context(request: Request) -> AuthContext:
    authorization = request.headers.get("authorization", "")
    expected = f"Bearer {get_dev_token()}"

    if authorization != expected:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return build_dev_auth_context(
        actor=get_request_actor(request),
        role=get_request_role(request),
        tenant_id=get_request_tenant_id(request),
        tenant_name=get_request_tenant_name(request),
    )


def _require_oidc_auth_context(request: Request) -> AuthContext:
    issuer = get_oidc_issuer()
    audience = get_oidc_audience()

    if not issuer or not audience:
        raise HTTPException(
            status_code=500,
            detail="OIDC authentication mode requires OIDC_ISSUER_URL and OIDC_AUDIENCE.",
        )

    token = _extract_bearer_token(request)
    claims = _decode_unverified_jwt_claims(token)

    try:
        validated_claims = validate_jwt_claims(
            claims,
            expected_issuer=issuer,
            expected_audience=audience,
        )
    except JWTValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    payload = map_claims_to_auth_context_payload(validated_claims)

    return build_oidc_auth_context(
        actor=payload["actor"],
        role=payload["role"],
        tenant_id=payload["tenant_id"],
        tenant_name=payload["tenant_name"],
        subject=payload["subject"],
        issuer=payload["issuer"],
        raw_claims=payload["raw_claims"],
    )


def get_auth_context(request: Request) -> AuthContext:
    auth_mode = get_auth_mode()

    if auth_mode == "dev":
        return _require_dev_auth_context(request)

    if auth_mode == "oidc":
        return _require_oidc_auth_context(request)

    raise HTTPException(
        status_code=500,
        detail=f"Unsupported AUTH_MODE: {auth_mode}",
    )


def require_enterprise_auth(request: Request) -> AuthContext:
    return get_auth_context(request)


def require_enterprise_role(
    request: Request,
    *,
    allowed_roles: set[str],
    detail: str = "Access denied.",
) -> AuthContext:
    auth_context = require_enterprise_auth(request)

    if not auth_context.has_role(allowed_roles):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context


def require_hospital_or_enterprise_admin(
    request: Request,
    *,
    detail: str = "Hospital or enterprise administrator access required.",
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"hospital_admin", "enterprise_admin"},
        detail=detail,
    )


def require_vendor(
    request: Request,
    *,
    detail: str = "Vendor access required.",
) -> AuthContext:
    return require_enterprise_role(
        request,
        allowed_roles={"vendor"},
        detail=detail,
    )


def require_permission(
    request: Request,
    *,
    permission: str,
    detail: str = "Permission denied.",
) -> AuthContext:
    auth_context = require_enterprise_auth(request)

    if not auth_context.has_permission(permission):
        raise HTTPException(status_code=403, detail=detail)

    return auth_context
