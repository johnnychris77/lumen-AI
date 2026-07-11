"""Security regression tests for the cross-hospital intelligence tenant-
isolation gap identified in a patent/security audit.

Before the fix: routes gated by app.enterprise_auth.require_enterprise_auth()
(global-intelligence, p25 industry infrastructure, network-benchmark, recall
signals, ...) and routes/federated_horizon.py's own _tenant() helper both
trusted the client-supplied X-Tenant-Id header outright for a real,
JWT-authenticated user -- no database check that the user actually belonged
to that tenant. A user authenticated as tenant A could set
X-Tenant-Id: tenant-b and read/act on tenant B's cross-hospital data.

After the fix: tenant_id is still read from the header, but it must
correspond to an enabled TenantMembership row for the authenticated user,
or the request is rejected with 403 -- and this holds even when a route
calls require_enterprise_auth(request) without threading its own `db`
session through (the exact gap the audit found).
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.routers.auth_simple import _make_token

client = TestClient(app)


def _add_membership(tenant_id: str, user_email: str, role: str = "viewer", is_enabled: bool = True) -> None:
    db = SessionLocal()
    try:
        db.add(models.TenantMembership(
            tenant_id=tenant_id, user_email=user_email, role=role, is_enabled=is_enabled,
        ))
        db.commit()
    finally:
        db.close()


def _jwt_headers(username: str) -> dict:
    """A real, signed per-user JWT -- the same kind /auth/login issues --
    not the shared dev-token/manager-token/viewer-token shortcuts."""
    return {"Authorization": f"Bearer {_make_token(username)}"}


class TestRequireEnterpriseAuthTenantIsolation:
    """require_enterprise_auth() is used by ~200 routes, including the
    cross-hospital intelligence routers (global_intelligence.py,
    p25_infrastructure.py, network_benchmark.py, recall_signals.py, ...)."""

    def test_user_in_tenant_a_cannot_read_tenant_b_via_spoofed_header(self):
        user = "audit-tenant-a-user@example.com"
        _add_membership("audit-tenant-a", user, role="viewer")

        # This user is only a member of audit-tenant-a. Spoof X-Tenant-Id to
        # claim a different hospital's tenant they have no relationship to.
        res = client.get(
            "/api/global-intelligence/signals",
            headers={**_jwt_headers(user), "X-Tenant-Id": "audit-tenant-b-not-a-member"},
        )
        assert res.status_code == 403

    def test_user_can_read_their_own_tenant(self):
        user = "audit-tenant-a-user-2@example.com"
        _add_membership("audit-tenant-a-2", user, role="viewer")

        res = client.get(
            "/api/global-intelligence/signals",
            headers={**_jwt_headers(user), "X-Tenant-Id": "audit-tenant-a-2"},
        )
        assert res.status_code == 200

    def test_authenticated_user_with_no_membership_anywhere_is_rejected(self):
        user = "audit-nobody@example.com"
        res = client.get(
            "/api/global-intelligence/signals",
            headers={**_jwt_headers(user), "X-Tenant-Id": "audit-tenant-nobody-belongs-to"},
        )
        assert res.status_code == 403

    def test_fix_applies_even_when_caller_omits_db_kwarg(self):
        """The audit's actual finding: dozens of routes call
        require_enterprise_auth(request) with no db= kwarg. Confirm the
        membership check still runs in that exact calling pattern, by
        calling the function directly the same way those routes do."""
        from app.enterprise_auth import require_enterprise_auth

        user = "audit-no-db-kwarg-user@example.com"
        # Deliberately no TenantMembership row created for this user/tenant.

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [
                (b"authorization", f"Bearer {_make_token(user)}".encode()),
                (b"x-tenant-id", b"audit-tenant-spoofed-no-db-kwarg"),
            ],
        }
        request = Request(scope)

        try:
            require_enterprise_auth(request)  # no db= kwarg, matching real call sites
        except HTTPException as exc:
            assert exc.status_code == 403
        else:
            raise AssertionError("expected require_enterprise_auth to raise 403")


class TestHorizonTenantIsolation:
    """routes/federated_horizon.py's own _tenant() helper -- fixed
    separately from require_enterprise_auth() because this router
    authenticates via app.authz.require_roles(), not
    require_enterprise_auth()."""

    def test_user_in_tenant_a_cannot_read_tenant_b_via_spoofed_header(self):
        res = client.get(
            "/api/horizon/participation/status",
            headers={"Authorization": "Bearer viewer-token", "x-tenant-id": "audit-horizon-tenant-spoofed"},
        )
        assert res.status_code == 403

    def test_user_can_read_their_own_tenant(self):
        tenant_id = "audit-horizon-tenant-real"
        _add_membership(tenant_id, "viewer@local.dev", role="viewer")

        res = client.get(
            "/api/horizon/participation/status",
            headers={"Authorization": "Bearer viewer-token", "x-tenant-id": tenant_id},
        )
        assert res.status_code == 200
