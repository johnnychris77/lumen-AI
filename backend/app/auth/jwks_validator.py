from __future__ import annotations

import base64
import json
import os
import threading
from typing import Any

import jwt as pyjwt
from jwt import PyJWKClient, PyJWKClientError


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
    """Validate JWT header fields (alg allowlist, kid presence) before signature check."""
    header = parse_jwt_header(token)

    algorithm = header.get("alg", "")
    key_id = header.get("kid", "")

    if not algorithm:
        raise JWKSSignatureValidationError("JWT header missing alg.")

    if str(algorithm).lower() == "none":
        raise JWKSSignatureValidationError("Unsigned JWTs are not allowed.")

    if algorithm not in get_allowed_algorithms():
        raise JWKSSignatureValidationError(
            f"JWT algorithm is not allowed: '{algorithm}'."
        )

    if not key_id:
        raise JWKSSignatureValidationError("JWT header missing kid.")

    return header


# Module-level JWKS client with key caching. Protected by a lock for safe
# lazy initialisation under concurrent requests.
_jwks_client: PyJWKClient | None = None
_jwks_lock = threading.Lock()


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    global _jwks_client
    with _jwks_lock:
        if _jwks_client is None or _jwks_client.uri != jwks_url:
            _jwks_client = PyJWKClient(jwks_url, cache_keys=True, lifespan=300)
    return _jwks_client


def validate_jwt_signature_with_jwks(token: str) -> dict[str, Any]:
    """
    Cryptographically verify a JWT using JWKS and return the validated claims.

    Enforces:
    - Algorithm allowlist (OIDC_ALGORITHMS, default RS256)
    - kid presence in header
    - Signature via public key fetched from OIDC_JWKS_URL
    - Expiration (exp), iat, sub required claims
    - Issuer (iss) when OIDC_ISSUER_URL is set
    - Audience (aud) when OIDC_AUDIENCE is set

    Raises JWKSSignatureValidationError on any failure.
    Returns the verified claims dict on success.
    """
    validate_jwt_header_security(token)

    jwks_url = get_jwks_url()
    if not jwks_url:
        raise JWKSSignatureValidationError(
            "OIDC_JWKS_URL is required for signature validation."
        )

    issuer = os.getenv("OIDC_ISSUER_URL", "").strip() or None
    audience = os.getenv("OIDC_AUDIENCE", "").strip() or None
    algorithms = list(get_allowed_algorithms())

    # Pre-check issuer from unverified claims to give a clear error before
    # hitting the JWKS network call (which would fail with an opaque error).
    if issuer:
        try:
            unverified_payload = _decode_b64url_json(token.split(".")[1])
            token_iss = unverified_payload.get("iss", "")
            if token_iss != issuer:
                raise JWKSSignatureValidationError(
                    f"Invalid JWT issuer: expected '{issuer}', got '{token_iss}'."
                )
        except JWKSSignatureValidationError:
            raise
        except Exception as exc:
            raise JWKSSignatureValidationError("Malformed JWT payload.") from exc

    try:
        client = _get_jwks_client(jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientError as exc:
        raise JWKSSignatureValidationError(
            f"JWKS key fetch failed: {exc}"
        ) from exc
    except Exception as exc:
        raise JWKSSignatureValidationError(
            f"Unable to retrieve signing key: {exc}"
        ) from exc

    decode_kwargs: dict[str, Any] = {
        "algorithms": algorithms,
        "key": signing_key.key,
        "options": {"require": ["exp", "iat", "sub"]},
    }
    if issuer:
        decode_kwargs["issuer"] = issuer
    if audience:
        decode_kwargs["audience"] = audience

    try:
        claims: dict[str, Any] = pyjwt.decode(token, **decode_kwargs)
    except pyjwt.ExpiredSignatureError as exc:
        raise JWKSSignatureValidationError("Token has expired.") from exc
    except pyjwt.InvalidIssuerError as exc:
        raise JWKSSignatureValidationError("Invalid token issuer.") from exc
    except pyjwt.InvalidAudienceError as exc:
        raise JWKSSignatureValidationError("Invalid token audience.") from exc
    except pyjwt.MissingRequiredClaimError as exc:
        raise JWKSSignatureValidationError(f"Missing required claim: {exc}") from exc
    except pyjwt.InvalidSignatureError as exc:
        raise JWKSSignatureValidationError("Token signature is invalid.") from exc
    except pyjwt.InvalidAlgorithmError as exc:
        raise JWKSSignatureValidationError("Token algorithm is not allowed.") from exc
    except pyjwt.DecodeError as exc:
        raise JWKSSignatureValidationError(f"Token decode error: {exc}") from exc
    except pyjwt.InvalidTokenError as exc:
        raise JWKSSignatureValidationError(f"Token validation failed: {exc}") from exc

    return claims
