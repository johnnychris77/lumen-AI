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


def _token(email="member@example.com", tenant_id="tenant-member") -> str:
    now = datetime.now(UTC)

    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": "test-key",
    }

    claims = {
        "sub": "oidc-member-subject",
        "email": email,
        "iss": "https://issuer.example.com/",
        "aud": "lumenai-api",
        "exp": int((now + timedelta(minutes=30)).timestamp()),
        "iat": int((now - timedelta(minutes=1)).timestamp()),
        "roles": ["hospital_admin"],
        "tenant_id": tenant_id,
        "tenant_name": "Tenant Member",
    }

    return f"{_b64url(header)}.{_b64url(claims)}.signature"


def _configure_oidc(monkeypatch):
    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER_URL", "https://issuer.example.com/")
    monkeypatch.setenv("OIDC_AUDIENCE", "lumenai-api")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://issuer.example.com/.well-known/jwks.json")
    monkeypatch.setenv("OIDC_ALGORITHMS", "RS256")
    import base64
    import json as _json

    def _mock_jwks(token):
        padded = token.split(".")[1] + "=="
        return _json.loads(base64.urlsafe_b64decode(padded).decode())

    monkeypatch.setattr("app.enterprise_auth.validate_jwt_signature_with_jwks", _mock_jwks)


def _reset_memberships(db):
    from app.db import models

    models.TenantMembership.__table__.drop(bind=db.get_bind(), checkfirst=True)
    models.TenantMembership.__table__.create(bind=db.get_bind(), checkfirst=True)


def _add_membership(db, *, tenant_id, user_email, role="hospital_admin", is_enabled=True):
    from app.db import models

    membership = models.TenantMembership(
        tenant_id=tenant_id,
        user_email=user_email,
        role=role,
        is_enabled=is_enabled,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


def test_oidc_auth_context_allows_enabled_tenant_membership(monkeypatch):
    from app.db.session import SessionLocal
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    db = SessionLocal()
    try:
        _reset_memberships(db)
        _add_membership(
            db,
            tenant_id="tenant-member",
            user_email="member@example.com",
            is_enabled=True,
        )

        context = get_auth_context(
            _request(_token()),
            db=db,
        )

        assert context.actor == "member@example.com"
        assert context.tenant_id == "tenant-member"
        assert context.role == "hospital_admin"
    finally:
        db.close()


def test_oidc_auth_context_denies_missing_tenant_membership(monkeypatch):
    from app.db.session import SessionLocal
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    db = SessionLocal()
    try:
        _reset_memberships(db)

        with pytest.raises(HTTPException) as exc:
            get_auth_context(
                _request(_token()),
                db=db,
            )

        assert exc.value.status_code == 403
        assert "Enabled tenant membership required" in exc.value.detail
    finally:
        db.close()


def test_oidc_auth_context_denies_disabled_tenant_membership(monkeypatch):
    from app.db.session import SessionLocal
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    db = SessionLocal()
    try:
        _reset_memberships(db)
        _add_membership(
            db,
            tenant_id="tenant-member",
            user_email="member@example.com",
            is_enabled=False,
        )

        with pytest.raises(HTTPException) as exc:
            get_auth_context(
                _request(_token()),
                db=db,
            )

        assert exc.value.status_code == 403
    finally:
        db.close()


def test_oidc_auth_context_denies_cross_tenant_membership(monkeypatch):
    from app.db.session import SessionLocal
    from app.enterprise_auth import get_auth_context

    _configure_oidc(monkeypatch)

    db = SessionLocal()
    try:
        _reset_memberships(db)
        _add_membership(
            db,
            tenant_id="tenant-other",
            user_email="member@example.com",
            is_enabled=True,
        )

        with pytest.raises(HTTPException) as exc:
            get_auth_context(
                _request(_token()),
                db=db,
            )

        assert exc.value.status_code == 403
    finally:
        db.close()
