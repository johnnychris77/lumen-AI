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


def test_enterprise_auth_denies_missing_token():
    from app.enterprise_auth import require_enterprise_auth

    with pytest.raises(HTTPException) as exc:
        require_enterprise_auth(_request([]))

    assert exc.value.status_code == 401


def test_enterprise_role_denies_wrong_role():
    from app.enterprise_auth import require_hospital_or_enterprise_admin

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"vendor"),
            (b"x-lumenai-actor", b"vendor-user"),
        ]
    )

    with pytest.raises(HTTPException) as exc:
        require_hospital_or_enterprise_admin(request)

    assert exc.value.status_code == 403


def test_enterprise_role_allows_hospital_admin():
    from app.enterprise_auth import require_hospital_or_enterprise_admin

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"hospital_admin"),
            (b"x-lumenai-actor", b"hospital-user"),
        ]
    )

    result = require_hospital_or_enterprise_admin(request)

    assert result.role == "hospital_admin"
    assert result.actor == "hospital-user"


def test_enterprise_role_allows_enterprise_admin():
    from app.enterprise_auth import require_hospital_or_enterprise_admin

    request = _request(
        [
            (b"authorization", b"Bearer dev-token"),
            (b"x-lumenai-role", b"enterprise_admin"),
            (b"x-lumenai-actor", b"enterprise-user"),
        ]
    )

    result = require_hospital_or_enterprise_admin(request)

    assert result.role == "enterprise_admin"
    assert result.actor == "enterprise-user"
