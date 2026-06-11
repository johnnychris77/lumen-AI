from __future__ import annotations

from typing import Iterable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth_config import get_auth_config
from app.core.principal import Principal


bearer_scheme = HTTPBearer(auto_error=False)


def _safe_unauthorized(message: str = "Authentication is required to access this resource.") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={
            "error": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": message,
                "status_code": 401,
            }
        },
    )


def _decode_hs256_jwt_without_external_dependency(token: str, secret: str | None) -> dict:
    """
    Decode and validate HS256 JWT tokens.

    This baseline supports signed-token validation for production authentication
    while keeping public-safe endpoints separate.
    """
    import jwt
    from jwt import InvalidTokenError

    if not token or token.count(".") != 2:
        raise _safe_unauthorized("Invalid authentication credentials.")

    if not secret:
        raise _safe_unauthorized("Authentication configuration is incomplete.")

    config = get_auth_config()

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": bool(config.jwt_audience),
        "verify_iss": bool(config.jwt_issuer),
    }

    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[config.jwt_algorithm],
            audience=config.jwt_audience,
            issuer=config.jwt_issuer,
            options=options,
        )
    except InvalidTokenError:
        raise _safe_unauthorized("Invalid authentication credentials.")


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Principal:
    config = get_auth_config()

    if not credentials or credentials.scheme.lower() != "bearer":
        raise _safe_unauthorized()

    token = credentials.credentials

    if config.auth_mode == "dev" and config.enable_dev_auth:
        return Principal(
            user_id=request.headers.get("X-LumenAI-Actor", "dev-user"),
            tenant_id=request.headers.get("X-LumenAI-Tenant", "dev-tenant"),
            roles=[request.headers.get("X-LumenAI-Role", "system_admin")],
            email=None,
            auth_mode="dev",
            claims={},
        )

    claims = _decode_hs256_jwt_without_external_dependency(token, config.jwt_secret)

    return Principal(
        user_id=str(claims.get("sub")),
        tenant_id=str(claims.get("tenant_id")),
        roles=list(claims.get("roles", [])),
        email=claims.get("email"),
        auth_mode="jwt",
        claims=claims,
    )


def require_any_role(allowed_roles: Iterable[str]):
    allowed = set(allowed_roles)

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any_role(allowed):
            raise HTTPException(
                status_code=403,
                detail={
                    "error": {
                        "code": "ACCESS_DENIED",
                        "message": "You do not have permission to access this resource.",
                        "status_code": 403,
                    }
                },
            )
        return principal

    return dependency


def require_authenticated_user(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    return principal
