import base64
import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": headers,
        }
    )


def _b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _unsigned_test_jwt(**claim_overrides) -> str:
    now = datetime.now(UTC)

    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": "test-key",
    }

    claims = {
        "sub": "oidc-subject-123",
        "email": "oidc.user@example.com",
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "tenant-oidc",
        "tenant_name": "OIDC Tenant",
    }

    claims.update(claim_overrides)

    return f"{_b64url(header)}.{_b64url(claims)}.signature"


def test_oidc_auth_mode_maps_valid_claims_to_auth_context(monkeypatch):
    from app.enterprise_auth import get_auth_context
    from datetime import UTC, datetime, timedelta

    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    token = _unsigned_test_jwt()

    now = datetime.now(UTC)
    verified_claims = {
        "sub": "oidc-subject-123",
        "email": "oidc.user@example.com",
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "tenant-oidc",
        "tenant_name": "OIDC Tenant",
    }
    monkeypatch.setattr(
        "app.enterprise_auth.validate_jwt_signature_with_jwks",
        lambda t: verified_claims,
    )

    context = get_auth_context(
        _request(
            [
                (b"authorization", f"Bearer {token}".encode("utf-8")),
                (b"x-lumenai-role", b"vendor"),
                (b"x-lumenai-tenant-id", b"spoofed-tenant"),
            ]
        )
    )

    assert context.auth_provider == "oidc"
    assert context.actor == "oidc.user@example.com"
    assert context.subject == "oidc-subject-123"
    assert context.role == "hospital_admin"
    assert context.tenant_id == "tenant-oidc"
    assert context.tenant_name == "OIDC Tenant"
    assert context.issuer == "https://issuer.example.com/"
    assert context.has_permission("governance_packet:export") is True


def test_oidc_auth_mode_rejects_missing_configuration(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.delenv("OIDC_ISSUER_URL", raising=False)
    monkeypatch.delenv("OIDC_AUDIENCE", raising=False)
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)

    token = _unsigned_test_jwt()

    with pytest.raises(HTTPException) as exc:
        get_auth_context(
            _request(
                [
                    (b"authorization", f"Bearer {token}".encode("utf-8")),
                ]
            )
        )

    assert exc.value.status_code == 500


def test_oidc_auth_mode_rejects_wrong_issuer(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    token = _unsigned_test_jwt(iss="https://wrong.example.com/")

    with pytest.raises(HTTPException) as exc:
        get_auth_context(
            _request(
                [
                    (b"authorization", f"Bearer {token}".encode("utf-8")),
                ]
            )
        )

    assert exc.value.status_code == 401
    assert "Invalid JWT issuer" in exc.value.detail


def test_oidc_auth_mode_rejects_malformed_jwt(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")

    with pytest.raises(HTTPException) as exc:
        get_auth_context(
            _request(
                [
                    (b"authorization", b"Bearer not-a-valid-jwt"),
                ]
            )
        )

    assert exc.value.status_code == 401
    assert "JWT must have three segments" in exc.value.detail
