"""Tenant-resolution contract — executable specification.

Pins the documented contract (docs/security/TENANT_RESOLUTION_CONTRACT.md) against
the CORRECTED membership loader, so the security boundary can never silently
regress. Cross-tenant access is impossible unless membership-verified; a
client-supplied requested tenant carries no authority on its own.

Cases (see the contract doc):
  A platform admin        → all tenants, or a specifically requested one
  B single-tenant user    → resolves to that tenant
  C multi-tenant user     → explicit selection required; only verified tenants
  D zero-tenant user      → fail closed (403)
  E requested ∉ memberships→ fail closed (403)
  F disabled membership   → not loaded → fail closed
  G forged header/tenant  → ignored unless it matches a verified membership
"""
import pytest
from fastapi import HTTPException

from app.db.session import SessionLocal
from app.db import models
from app.deps import _load_tenant_memberships
from app.security.principal import AuthenticatedPrincipal, METHOD_JWT
from app.security.tenant_context import resolve_verified_tenant


def _clear(db, email):
    db.query(models.TenantMembership).filter(models.TenantMembership.user_email == email).delete()
    db.commit()


def _grant(db, email, tenant_id, *, role="operator", enabled=True):
    db.add(models.TenantMembership(user_email=email, tenant_id=tenant_id, role=role, is_enabled=enabled))
    db.commit()


def _principal(db, email, *, role):
    """Build a principal exactly as get_current_user does — memberships come only
    from the DB via the loader, never from client input."""
    memberships = _load_tenant_memberships(db, email)
    ids = {m.tenant_id for m in memberships}
    active = next(iter(ids)) if len(ids) == 1 else None
    return AuthenticatedPrincipal(
        subject=email, email=email, username=email, role=role,
        authentication_method=METHOD_JWT, tenant_memberships=memberships,
        active_tenant_id=active,
    )


class TestLoaderPopulates:
    def test_enabled_membership_is_loaded_from_live_model(self):
        db = SessionLocal()
        email = "contract-loader@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a", role="tenant_admin")
            views = _load_tenant_memberships(db, email)
            assert [v.tenant_id for v in views] == ["tenant-a"]
            assert views[0].role_name == "tenant_admin"  # from the live `role` column
        finally:
            _clear(db, email)
            db.close()

    def test_disabled_membership_is_not_loaded(self):  # Case F
        db = SessionLocal()
        email = "contract-disabled@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a", enabled=False)
            assert _load_tenant_memberships(db, email) == ()
        finally:
            _clear(db, email)
            db.close()


class TestResolutionContract:
    def test_case_A_platform_admin_all_tenants(self):
        p = AuthenticatedPrincipal(subject="a", email="a", username="a", role="admin",
                                   authentication_method=METHOD_JWT, tenant_memberships=(), active_tenant_id=None)
        assert p.is_platform_admin is True
        assert resolve_verified_tenant(p).all_tenants is True
        # may target a specific tenant when asked
        scope = resolve_verified_tenant(p, requested_tenant_id="tenant-x")
        assert scope.all_tenants is False and scope.tenant_id == "tenant-x"

    def test_case_B_single_tenant_resolves(self):
        db = SessionLocal()
        email = "contract-single@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a")
            p = _principal(db, email, role="operator")
            scope = resolve_verified_tenant(p)
            assert scope.all_tenants is False and scope.tenant_id == "tenant-a"
        finally:
            _clear(db, email)
            db.close()

    def test_case_C_multi_tenant_requires_explicit_selection(self):
        db = SessionLocal()
        email = "contract-multi@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a")
            _grant(db, email, "tenant-b")
            p = _principal(db, email, role="operator")
            # No explicit selection with >1 membership → fail closed.
            with pytest.raises(HTTPException) as ei:
                resolve_verified_tenant(p)
            assert ei.value.status_code == 403
            # Explicit selection that IS a member → allowed.
            scope = resolve_verified_tenant(p, requested_tenant_id="tenant-b")
            assert scope.tenant_id == "tenant-b"
        finally:
            _clear(db, email)
            db.close()

    def test_case_D_zero_tenant_fails_closed(self):
        p = AuthenticatedPrincipal(subject="z", email="z", username="z", role="operator",
                                   authentication_method=METHOD_JWT, tenant_memberships=(), active_tenant_id=None)
        with pytest.raises(HTTPException) as ei:
            resolve_verified_tenant(p)
        assert ei.value.status_code == 403

    def test_case_E_requested_tenant_not_a_member_denied(self):
        db = SessionLocal()
        email = "contract-e@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a")
            p = _principal(db, email, role="operator")
            with pytest.raises(HTTPException) as ei:
                resolve_verified_tenant(p, requested_tenant_id="tenant-victim")
            assert ei.value.status_code == 403
        finally:
            _clear(db, email)
            db.close()

    def test_case_G_forged_tenant_request_confers_no_authority(self):
        # A non-member "requested tenant" (as a header/query would supply) is
        # rejected — membership is the only authority.
        db = SessionLocal()
        email = "contract-g@example.com"
        try:
            _clear(db, email)
            _grant(db, email, "tenant-a")
            p = _principal(db, email, role="operator")
            for forged in ("tenant-b", "default-tenant", "platform"):
                with pytest.raises(HTTPException):
                    resolve_verified_tenant(p, requested_tenant_id=forged)
        finally:
            _clear(db, email)
            db.close()
