from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class JWTValidationError(ValueError):
    pass


def _now_timestamp() -> int:
    return int(datetime.now(UTC).timestamp())


def _require_claim(claims: dict[str, Any], claim_name: str) -> Any:
    value = claims.get(claim_name)

    if value in (None, ""):
        raise JWTValidationError(f"Missing required JWT claim: {claim_name}")

    return value


def validate_jwt_claims(
    claims: dict[str, Any],
    *,
    expected_issuer: str,
    expected_audience: str,
    required_claims: tuple[str, ...] = ("sub", "email", "iss", "aud", "exp", "iat"),
    now_timestamp: int | None = None,
    clock_skew_seconds: int = 60,
) -> dict[str, Any]:
    """
    Validate decoded JWT claims.

    This function does not verify JWT signatures yet. Signature/JWKS validation
    will be added in the next auth milestone. This function validates the claim
    contract that LumenAI will require after signature verification.
    """

    for claim_name in required_claims:
        _require_claim(claims, claim_name)

    issuer = claims.get("iss")
    if issuer != expected_issuer:
        raise JWTValidationError("Invalid JWT issuer.")

    audience = claims.get("aud")
    if isinstance(audience, str):
        valid_audience = audience == expected_audience
    elif isinstance(audience, list):
        valid_audience = expected_audience in audience
    else:
        valid_audience = False

    if not valid_audience:
        raise JWTValidationError("Invalid JWT audience.")

    current_time = now_timestamp if now_timestamp is not None else _now_timestamp()

    exp = int(claims["exp"])
    if exp + clock_skew_seconds < current_time:
        raise JWTValidationError("JWT is expired.")

    iat = int(claims["iat"])
    if iat - clock_skew_seconds > current_time:
        raise JWTValidationError("JWT issued-at time is in the future.")

    return claims


def map_claims_to_auth_context_payload(
    claims: dict[str, Any],
    *,
    default_role: str = "viewer",
) -> dict[str, Any]:
    roles = claims.get("roles") or claims.get("groups") or []

    if isinstance(roles, str):
        roles = [roles]

    role = claims.get("lumenai_role") or (roles[0] if roles else default_role)

    tenant_id = (
        claims.get("tenant_id")
        or claims.get("lumenai_tenant_id")
        or claims.get("tid")
        or "default-tenant"
    )

    tenant_name = (
        claims.get("tenant_name")
        or claims.get("lumenai_tenant_name")
        or tenant_id
    )

    return {
        "actor": claims.get("email") or claims.get("sub") or "unknown",
        "subject": claims.get("sub") or "",
        "role": role,
        "tenant_id": tenant_id,
        "tenant_name": tenant_name,
        "auth_provider": "oidc",
        "issuer": claims.get("iss") or "",
        "raw_claims": claims,
    }
