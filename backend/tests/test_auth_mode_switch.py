import os

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


def test_dev_auth_mode_allows_valid_dev_token(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"hospital_admin"),
            (b"x-lumenai-actor", b"dev-admin"),
            (b"x-lumenai-tenant-id", b"tenant-dev"),
        ]
    )

    context = get_auth_context(request)

    assert context.auth_provider == "dev"
    assert context.actor == "dev-admin"
    assert context.role == "hospital_admin"
    assert context.tenant_id == "tenant-dev"


def test_dev_auth_mode_denies_wrong_token(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_TOKEN", "dev-token")

    request = _request(
        [
            (b"authorization", b"Bearer wrong-token"),
            (b"x-lumenai-role", b"hospital_admin"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        get_auth_context(request)

    assert exc.value.status_code == 401


def test_oidc_auth_mode_returns_not_implemented_until_jwt_validator_exists(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "oidc")

    request = _request(
        [
            (b"authorization", b"Bearer some.jwt.token"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        get_auth_context(request)

    assert exc.value.status_code == 501


def test_invalid_auth_mode_returns_server_error(monkeypatch):
    from app.enterprise_auth import get_auth_context

    monkeypatch.setenv("AUTH_MODE", "invalid-mode")

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        get_auth_context(request)

    assert exc.value.status_code == 500
