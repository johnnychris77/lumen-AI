from __future__ import annotations

import base64
import json
import os
from typing import Any


class JWKSSignatureValidationError(ValueError):
    pass


def get_allowed_algorithms() -> set[str]:
    raw = os.getenv("OIDC_ALGORITHMS", "RS256")
    return {item.strip() for item in raw.split(",") if item.strip()}


def get_jwks_url() -> str:
    return os.getenv("OIDC_JWKS_URL", "").strip()


def _decode_b64url_json(segment: str) -> dict[str, Any]:
    try:
        padded = segment + "=" * (-len(segment) % 4)
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        payload = json.loads(decoded.decode("utf-8"))
    except Exception as exc:
        raise JWKSSignatureValidationError("Invalid JWT segment encoding.") from exc

    if not isinstance(payload, dict):
        raise JWKSSignatureValidationError("JWT segment must decode to an object.")

    return payload


def parse_jwt_header(token: str) -> dict[str, Any]:
    parts = token.split(".")

    if len(parts) != 3:
        raise JWKSSignatureValidationError("JWT must have three segments.")

    return _decode_b64url_json(parts[0])


def validate_jwt_header_security(token: str) -> dict[str, Any]:
    header = parse_jwt_header(token)

    algorithm = header.get("alg")
    key_id = header.get("kid")

    if not algorithm:
        raise JWKSSignatureValidationError("JWT header missing alg.")

    if str(algorithm).lower() == "none":
        raise JWKSSignatureValidationError("Unsigned JWTs are not allowed.")

    if algorithm not in get_allowed_algorithms():
        raise JWKSSignatureValidationError("JWT algorithm is not allowed.")

    if not key_id:
        raise JWKSSignatureValidationError("JWT header missing kid.")

    return header


def validate_jwt_signature_with_jwks(token: str) -> dict[str, Any]:
    """
    Production signature-validation entry point.

    Current milestone validates JWT header security and JWKS configuration.
    Full cryptographic verification should be implemented with a JWKS-capable
    JWT library in the next hardening milestone.
    """
    header = validate_jwt_header_security(token)

    if not get_jwks_url():
        raise JWKSSignatureValidationError("OIDC_JWKS_URL is required for signature validation.")

    return {
        "signature_validation_status": "jwks_signature_validation_pending",
        "header": header,
        "jwks_url": get_jwks_url(),
    }
