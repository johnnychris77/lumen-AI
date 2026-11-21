import os
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _get_protected_report_route(app) -> str:
    spec = app.openapi()
    # Prefer the canonical /api/reports list endpoint; fall back to any report route.
    for preferred in ("/api/reports", "/api/reports/history"):
        if preferred in spec.get("paths", {}):
            return preferred
    candidates = [
        path
        for path, methods in spec.get("paths", {}).items()
        if "get" in methods and "report" in path.lower() and "{" not in path
    ]
    if not candidates:
        raise AssertionError("No GET reports route found in OpenAPI spec.")
    return sorted(candidates)[0]



def _token(user_email: str) -> str:
    from app.routers.auth_simple import _make_token

    return _make_token(user_email)


def _ensure_tenant_membership_table():
    from app.db.base import Base
    from app.db.session import engine
    from app.db import models  # noqa: F401

    models.TenantMembership.__table__.drop(bind=engine, checkfirst=True)
    Base.metadata.create_all(bind=engine)


def _make_membership(db, *, tenant_id: str, user_email: str, role: str, is_enabled: bool = True):
    from app.db import models

    _ensure_tenant_membership_table()

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


def test_protected_reports_route_denies_user_without_membership():
    from app.main import app

    client = TestClient(app)

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"missing-{uuid.uuid4()}@example.com"

    with patch("app.tenant_authz._resolve_user_email_from_token", return_value=user_email):
        response = client.get(
            _get_protected_report_route(app),
            headers={
                # P472-03 batch 2: the tenant dependency authenticates the caller
                # itself, so the request carries a real signed token for this user
                # (the patch above only replaced one of the two identity lookups).
                "Authorization": f"Bearer {_token(user_email)}",
                "X-LumenAI-Tenant-ID": tenant_id,
                "X-LumenAI-Actor": user_email,
            },
        )

    assert response.status_code == 403


def test_protected_reports_route_denies_wrong_role():
    from app.db.session import SessionLocal
    from app.main import app

    tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"viewer-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=tenant_id,
            user_email=user_email,
            role="viewer",
            is_enabled=True,
        )
    finally:
        db.close()

    client = TestClient(app)

    with patch("app.tenant_authz._resolve_user_email_from_token", return_value=user_email):
        response = client.get(
            _get_protected_report_route(app),
            headers={
                # P472-03 batch 2: the tenant dependency authenticates the caller
                # itself, so the request carries a real signed token for this user
                # (the patch above only replaced one of the two identity lookups).
                "Authorization": f"Bearer {_token(user_email)}",
                "X-LumenAI-Tenant-ID": tenant_id,
                "X-LumenAI-Actor": user_email,
            },
        )

    assert response.status_code == 403


def test_protected_reports_route_denies_cross_tenant_user():
    from app.db.session import SessionLocal
    from app.main import app

    allowed_tenant_id = f"tenant-{uuid.uuid4()}"
    blocked_tenant_id = f"tenant-{uuid.uuid4()}"
    user_email = f"cross-{uuid.uuid4()}@example.com"

    db = SessionLocal()
    try:
        _make_membership(
            db,
            tenant_id=allowed_tenant_id,
            user_email=user_email,
            role="tenant_admin",
            is_enabled=True,
        )
    finally:
        db.close()

    client = TestClient(app)

    with patch("app.tenant_authz._resolve_user_email_from_token", return_value=user_email):
        response = client.get(
            _get_protected_report_route(app),
            headers={
                # P472-03 batch 2: the tenant dependency authenticates the caller
                # itself, so the request carries a real signed token for this user
                # (the patch above only replaced one of the two identity lookups).
                "Authorization": f"Bearer {_token(user_email)}",
                "X-LumenAI-Tenant-ID": blocked_tenant_id,
                "X-LumenAI-Actor": user_email,
            },
        )

    assert response.status_code == 403
