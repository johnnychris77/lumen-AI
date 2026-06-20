import os
import uuid

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _collect_all_routes_with_prefix(router_or_app, parent_prefix=""):
    from fastapi.routing import APIRoute
    routes = []
    obj = getattr(router_or_app, "router", router_or_app)
    for route in getattr(obj, "routes", []):
        ctx = getattr(route, "include_context", None)
        prefix = parent_prefix + (getattr(ctx, "prefix", "") or "")
        if isinstance(route, APIRoute):
            routes.append((parent_prefix + route.path, route.methods or set()))
        orig = getattr(route, "original_router", None)
        if orig:
            routes.extend(_collect_all_routes_with_prefix(orig, prefix))
    return routes


def _get_protected_report_route(app) -> str:
    for full_path, methods in _collect_all_routes_with_prefix(app):
        if "GET" in methods and "report" in full_path.lower() and "{" not in full_path:
            return full_path

    raise AssertionError("No GET reports route found in app routes.")


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

    response = client.get(
        _get_protected_report_route(app),
        headers={
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

    response = client.get(
        _get_protected_report_route(app),
        headers={
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

    response = client.get(
        _get_protected_report_route(app),
        headers={
            "X-LumenAI-Tenant-ID": blocked_tenant_id,
            "X-LumenAI-Actor": user_email,
        },
    )

    assert response.status_code == 403
