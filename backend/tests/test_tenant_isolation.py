import os
import uuid

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _ensure_tenant_membership_table():
    from app.db.base import Base
    from app.db.session import engine
    from app.db import models  # noqa: F401

    # This test owns the tenant_memberships table shape. Drop/recreate it so
    # stale local SQLite tables from earlier experiments do not break the test.
    models.TenantMembership.__table__.drop(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)



def _make_membership(db, *, tenant_id: str, user_email: str, is_enabled: bool):
    _ensure_tenant_membership_table()

    from app.db import models

    membership = models.TenantMembership(
        tenant_id=tenant_id,
        user_email=user_email,
        role="viewer",
        is_enabled=is_enabled,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    return membership


def test_tenant_authorization_denies_missing_user_email():
    from app.db.session import SessionLocal
    from app.tenant_authz import assert_tenant_membership

    _ensure_tenant_membership_table()

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            assert_tenant_membership(
                db,
                tenant_id="tenant-a",
                user_email="",
            )

        assert exc.value.status_code == 403
    finally:
        db.close()


def test_tenant_authorization_denies_user_without_membership():
    from app.db.session import SessionLocal
    from app.tenant_authz import assert_tenant_membership

    _ensure_tenant_membership_table()

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc:
            assert_tenant_membership(
                db,
                tenant_id=f"tenant-{uuid.uuid4()}",
                user_email=f"missing-{uuid.uuid4()}@example.com",
            )

        assert exc.value.status_code == 403
    finally:
        db.close()


def test_tenant_authorization_denies_disabled_membership():
    from app.db.session import SessionLocal
    from app.tenant_authz import assert_tenant_membership

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"disabled-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
            is_enabled=False,
        )

        with pytest.raises(HTTPException) as exc:
            assert_tenant_membership(
                db,
                tenant_id=tenant_id,
                user_email=user_email,
            )

        assert exc.value.status_code == 403
    finally:
        db.close()


def test_tenant_authorization_allows_valid_enabled_membership():
    from app.db.session import SessionLocal
    from app.tenant_authz import assert_tenant_membership

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"allowed-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
            is_enabled=True,
        )

        assert (
            assert_tenant_membership(
                db,
                tenant_id=tenant_id,
                user_email=user_email,
            )
            is True
        )
    finally:
        db.close()


def test_tenant_authorization_denies_cross_tenant_access():
    from app.db.session import SessionLocal
    from app.tenant_authz import assert_tenant_membership

    allowed_tenant_id = f"tenant-{uuid.uuid4()}"
    blocked_tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"cross-tenant-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=allowed_tenant_id,
            user_email=user_email,
            is_enabled=True,
        )

        with pytest.raises(HTTPException) as exc:
            assert_tenant_membership(
                db,
                tenant_id=blocked_tenant_id,
                user_email=user_email,
            )

        assert exc.value.status_code == 403
    finally:
        db.close()


def test_tenant_role_dependency_allows_authorized_role():
    from starlette.requests import Request

    from app.db.session import SessionLocal
    from app.tenant_authz import require_tenant_roles

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"role-allowed-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
            is_enabled=True,
        )

        membership = (
            db.query(__import__("app.db.models", fromlist=["TenantMembership"]).TenantMembership)
            .filter_by(tenant_id=tenant_id, user_email=user_email)
            .first()
        )
        membership.role = "tenant_admin"
        db.commit()

        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [
                    (b"x-lumenai-tenant-id", tenant_id.encode()),
                    (b"x-lumenai-actor", user_email.encode()),
                ],
            }
        )

        dependency = require_tenant_roles("tenant_admin", "site_admin")
        result = dependency(request=request, db=db)

        assert result["tenant_id"] == tenant_id
        assert result["user_email"] == user_email
        assert result["role"] == "tenant_admin"
    finally:
        db.close()


def test_tenant_role_dependency_denies_wrong_role():
    from starlette.requests import Request

    from app.db.session import SessionLocal
    from app.tenant_authz import require_tenant_roles

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"role-denied-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
            is_enabled=True,
        )

        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [
                    (b"x-lumenai-tenant-id", tenant_id.encode()),
                    (b"x-lumenai-actor", user_email.encode()),
                ],
            }
        )

        dependency = require_tenant_roles("tenant_admin", "site_admin")

        with pytest.raises(HTTPException) as exc:
            dependency(request=request, db=db)

        assert exc.value.status_code == 403
    finally:
        db.close()
