import base64
import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _request(token: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))],
        }
    )


def _b64url(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _token(header: dict, claims: dict | None = None) -> str:
    now = datetime.now(UTC)
    claims = claims or {
        "sub": "oidc-subject",
        "email": "oidc@example.com",
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "tenant-oidc",
    }

    return f"{_b64url(header)}.{_b64url(claims)}.signature"


def _configure_oidc(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")


def test_oidc_auth_mode_rejects_alg_none(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request(_token({"alg": "none", "kid": "test-key"})))

    assert exc.value.status_code == 401
    assert "Unsigned JWTs are not allowed" in exc.value.detail


def test_oidc_auth_mode_rejects_disallowed_algorithm(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request(_token({"alg": "HS256", "kid": "test-key"})))

    assert exc.value.status_code == 401
    assert "JWT algorithm is not allowed" in exc.value.detail


def test_oidc_auth_mode_rejects_missing_kid(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request(_token({"alg": "RS256"})))

    assert exc.value.status_code == 401
    assert "JWT header missing kid" in exc.value.detail


def test_oidc_auth_mode_rejects_missing_jwks_url(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request(_token({"alg": "RS256", "kid": "test-key"})))

    assert exc.value.status_code == 401
    assert "OIDC_JWKS_URL is required" in exc.value.detail
