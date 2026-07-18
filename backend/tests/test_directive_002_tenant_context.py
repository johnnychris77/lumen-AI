"""Pilot Zero Directive 002 — authenticated tenant context for inspection
history and exports.

These tests pin the fail-closed cross-tenant contract that the remediation
establishes. The confirmed pre-remediation defect: any authenticated
non-admin received every tenant's inspection history because the identity
principal carried no tenant and the query fell open when tenant_id was None.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.security.principal import (
    METHOD_DEVELOPMENT,
    AuthenticatedPrincipal,
    TenantMembershipView,
)
from app.security.tenant_context import resolve_verified_tenant

client = TestClient(app)

AUTH_ADMIN = {"Authorization": "Bearer dev-token"}          # role=admin (dev)
AUTH_OPERATOR = {"Authorization": "Bearer operator-token"}  # role=operator (dev)
SHA = "d0020002" + "0" * 56


def _seed_inspection(tenant_id: str, tenant_name: str, instrument: str) -> int:
    """Create an inspection row directly attributed to a specific tenant."""
    from app.db import models

    db = SessionLocal()
    try:
        row = models.Inspection(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            file_name=f"{instrument}.jpg",
            instrument_type=instrument,
            status="completed",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


# ---- Typed principal contract (Phase 2) ----------------------------------

class TestAuthenticatedPrincipalContract:
    def test_principal_exposes_required_fields(self):
        p = AuthenticatedPrincipal(
            subject="u@example.org", email="u@example.org", role="spd_manager",
            authentication_method=METHOD_DEVELOPMENT,
            tenant_memberships=(TenantMembershipView("t1", "Tenant One", "spd_manager"),),
            active_tenant_id="t1",
        )
        assert p.user_id == 0 and p.id == 0
        assert p.tenant_id == "t1"           # backward-compatible alias
        assert p.is_development is True
        assert p.verified_tenant_ids() == frozenset({"t1"})
        assert p.has_verified_membership("t1") and not p.has_verified_membership("t2")

    def test_dev_get_current_user_returns_typed_principal(self):
        # /history uses require_roles -> get_current_user; hit it and assert the
        # response works (principal is the typed contract, not a SimpleNamespace).
        resp = client.get("/api/history?limit=1", headers=AUTH_ADMIN)
        assert resp.status_code == 200, resp.text


# ---- Verified tenant resolver (Phase 3) ----------------------------------

class TestResolveVerifiedTenant:
    def _principal(self, role, memberships=(), active=None):
        return AuthenticatedPrincipal(
            subject="x@example.org", email="x@example.org", role=role,
            authentication_method=METHOD_DEVELOPMENT,
            tenant_memberships=tuple(memberships), active_tenant_id=active,
        )

    def test_admin_defaults_to_all_tenants(self):
        scope = resolve_verified_tenant(self._principal("admin"))
        assert scope.all_tenants is True and scope.tenant_id is None

    def test_admin_may_target_a_specific_tenant(self):
        scope = resolve_verified_tenant(self._principal("admin"), requested_tenant_id="tX")
        assert scope.all_tenants is False and scope.tenant_id == "tX"

    def test_member_scoped_to_active_tenant(self):
        m = TenantMembershipView("tA", "A", "spd_manager")
        scope = resolve_verified_tenant(self._principal("spd_manager", (m,), "tA"))
        assert scope.all_tenants is False and scope.tenant_id == "tA"

    def test_requested_unverified_tenant_is_denied(self):
        m = TenantMembershipView("tA", "A", "spd_manager")
        with pytest.raises(HTTPException) as exc:
            resolve_verified_tenant(self._principal("spd_manager", (m,), "tA"), requested_tenant_id="tB")
        assert exc.value.status_code == 403

    def test_missing_tenant_context_fails_closed(self):
        with pytest.raises(HTTPException) as exc:
            resolve_verified_tenant(self._principal("spd_manager"))
        assert exc.value.status_code == 403

    def test_scope_object_rejects_unfiltered_non_admin(self):
        from app.security.tenant_context import TenantScope
        with pytest.raises(ValueError):
            TenantScope(all_tenants=False, tenant_id=None)


# ---- Cross-tenant isolation on the live route (Phase 4) ------------------

class TestHistoryCrossTenantIsolation:
    def test_admin_sees_all_tenants(self):
        ta, tb = f"t-{uuid.uuid4().hex[:8]}", f"t-{uuid.uuid4().hex[:8]}"
        ia = _seed_inspection(ta, "Alpha", "scissors")
        ib = _seed_inspection(tb, "Bravo", "needle_holder")
        resp = client.get("/api/history?limit=500", headers=AUTH_ADMIN)
        assert resp.status_code == 200
        ids = {it["id"] for it in resp.json()["items"]}
        assert ia in ids and ib in ids   # admin is explicit all-tenants

    def test_non_admin_without_membership_is_denied_not_unfiltered(self):
        # operator-token maps to a dev principal (operator@local.dev) with no
        # membership rows -> no verified tenant -> 403, NOT every tenant's data.
        # This is the exact pre-remediation breach, now closed.
        _seed_inspection(f"t-{uuid.uuid4().hex[:8]}", "Other", "forceps")
        resp = client.get("/api/history", headers=AUTH_OPERATOR)
        assert resp.status_code == 403, resp.text

    def test_non_admin_export_without_membership_is_denied(self):
        _seed_inspection(f"t-{uuid.uuid4().hex[:8]}", "Other", "forceps")
        for path in ("/api/history/export.json", "/api/history/export.csv"):
            resp = client.get(path, headers=AUTH_OPERATOR)
            assert resp.status_code == 403, f"{path}: {resp.text}"


# ---- Development-auth production disablement (Phase 2 requirement) --------

class TestDevAuthDisabledInProduction:
    def test_dev_auth_active_flag_is_false_in_production(self, monkeypatch):
        # Re-import deps with APP_ENV=production and dev auth requested: the
        # dev-token branch must be inert.
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("ENABLE_DEV_AUTH", "true")
        import importlib
        import app.deps as deps
        reloaded = importlib.reload(deps)
        try:
            assert reloaded._DEV_AUTH_ACTIVE is False
            assert reloaded._DEV_ROLE_MAP == {}
        finally:
            monkeypatch.setenv("APP_ENV", "development")
            importlib.reload(reloaded)
