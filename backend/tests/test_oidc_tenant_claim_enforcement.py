import base64
import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _request(token: str, extra_headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode("utf-8"))]
    headers.extend(extra_headers or [])

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


def _token(**claim_overrides) -> str:
    now = datetime.now(UTC)

    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": "test-key",
    }

    claims = {
        "sub": "oidc-subject-tenant",
        "email": "tenant.user@example.com",
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": "verified-tenant",
        "tenant_name": "Verified Tenant",
    }

    for key, value in claim_overrides.items():
        if value is None and key in claims:
            claims.pop(key)
        else:
            claims[key] = value

    return f"{_b64url(header)}.{_b64url(claims)}.signature"


def _configure_oidc(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")


def test_oidc_auth_context_requires_tenant_claim(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    token = _token(tenant_id=None, tenant_name=None)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(_request(token))

    assert exc.value.status_code == 401
    assert "Missing required JWT tenant claim" in exc.value.detail


def test_oidc_auth_context_uses_verified_tenant_claim_not_client_header(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    context = get_auth_context(
        _request(
            _token(),
            extra_headers=[
                (b"x-lumenai-tenant-id", b"spoofed-client-tenant"),
                (b"x-lumenai-tenant-name", b"Spoofed Client Tenant"),
            ],
        )
    )

    assert context.auth_provider == "oidc"
    assert context.tenant_id == "verified-tenant"
    assert context.tenant_name == "Verified Tenant"


def test_oidc_auth_context_accepts_lumenai_tenant_id_claim(monkeypatch):
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    token = _token(
        tenant_id=None,
        tenant_name=None,
        lumenai_tenant_id="custom-tenant",
        lumenai_tenant_name="Custom Tenant",
    )

    context = get_auth_context(_request(token))

    assert context.tenant_id == "custom-tenant"
    assert context.tenant_name == "Custom Tenant"
