import base64
import json
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _token(header: dict | None = None, payload: dict | None = None) -> str:
    header = header or {"alg": "RS256", "typ": "JWT", "kid": "test-key"}
    payload = payload or {"sub": "user-1"}
    return f"{_b64url(header)}.{_b64url(payload)}.signature"


def test_jwks_validator_accepts_allowed_secure_header(monkeypatch):
    from app.auth.jwks_validator import validate_jwt_header_security

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    header = validate_jwt_header_security(_token())

    assert header["alg"] == "RS256"
    assert header["kid"] == "test-key"


def test_jwks_validator_rejects_alg_none(monkeypatch):
    from app.auth.jwks_validator import (
        JWKSSignatureValidationError,
        validate_jwt_header_security,
    )

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    with pytest.raises(JWKSSignatureValidationError) as exc:
        validate_jwt_header_security(_token(header={"alg": "none", "kid": "test-key"}))

    assert "Unsigned JWTs are not allowed" in str(exc.value)


def test_jwks_validator_rejects_disallowed_algorithm(monkeypatch):
    from app.auth.jwks_validator import (
        JWKSSignatureValidationError,
        validate_jwt_header_security,
    )

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    with pytest.raises(JWKSSignatureValidationError) as exc:
        validate_jwt_header_security(_token(header={"alg": "HS256", "kid": "test-key"}))

    assert "JWT algorithm is not allowed" in str(exc.value)


def test_jwks_validator_rejects_missing_kid(monkeypatch):
    from app.auth.jwks_validator import (
        JWKSSignatureValidationError,
        validate_jwt_header_security,
    )

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    with pytest.raises(JWKSSignatureValidationError) as exc:
        validate_jwt_header_security(_token(header={"alg": "RS256"}))

    assert "JWT header missing kid" in str(exc.value)


def test_jwks_signature_validation_requires_jwks_url(monkeypatch):
    from app.auth.jwks_validator import (
        JWKSSignatureValidationError,
        validate_jwt_signature_with_jwks,
    )

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)

    with pytest.raises(JWKSSignatureValidationError) as exc:
        validate_jwt_signature_with_jwks(_token())

    assert "OIDC_JWKS_URL is required" in str(exc.value)


def test_jwks_signature_validation_rejects_unverifiable_token(monkeypatch):
    from app.auth.jwks_validator import (
        JWKSSignatureValidationError,
        validate_jwt_signature_with_jwks,
    )

    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")

    # A token with a fake signature must be rejected — the stub is gone.
    with pytest.raises(JWKSSignatureValidationError):
        validate_jwt_signature_with_jwks(_token())
