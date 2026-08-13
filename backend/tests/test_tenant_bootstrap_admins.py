"""ensure_bootstrap_admins — pilot membership provisioning.

Closes the gap where a logged-in operator has no tenant membership and every
/api/enterprise/* route 403s "Enabled tenant membership required". The bootstrap
is an explicit env allow-list — it must provision ONLY the configured emails and
never grant membership to anyone else.
"""

from app.db.session import SessionLocal
from app.db import models
from app.services.tenant_bootstrap import ensure_bootstrap_admins
from app.auth.tenant_membership import get_enabled_tenant_membership


def _clear(db, email, tenant_id):
    db.query(models.TenantMembership).filter(
        models.TenantMembership.user_email == email,
        models.TenantMembership.tenant_id == tenant_id,
    ).delete()
    db.commit()


def test_no_env_grants_nothing(monkeypatch):
    monkeypatch.delenv("BOOTSTRAP_TENANT_ADMINS", raising=False)
    db = SessionLocal()
    try:
        assert ensure_bootstrap_admins(db) == []
    finally:
        db.close()


def test_provisions_enabled_membership_in_default_tenant(monkeypatch):
    email = "pilot-admin@example.com"
    monkeypatch.setenv("BOOTSTRAP_TENANT_ADMINS", f"  {email.upper()} , ")  # trims + lowercases
    monkeypatch.delenv("BOOTSTRAP_TENANT_ID", raising=False)  # -> default-tenant
    db = SessionLocal()
    try:
        _clear(db, email, "default-tenant")
        granted = ensure_bootstrap_admins(db)
        assert granted == [email]
        m = get_enabled_tenant_membership(db, tenant_id="default-tenant", user_email=email)
        assert m is not None
        assert m.role == "tenant_admin"
        assert m.is_enabled is True
    finally:
        _clear(db, email, "default-tenant")
        db.close()


def test_idempotent_and_reenables(monkeypatch):
    email = "pilot-admin2@example.com"
    monkeypatch.setenv("BOOTSTRAP_TENANT_ADMINS", email)
    monkeypatch.setenv("BOOTSTRAP_TENANT_ID", "default-tenant")
    db = SessionLocal()
    try:
        _clear(db, email, "default-tenant")
        ensure_bootstrap_admins(db)
        # Disable it, then re-run: the bootstrap must re-enable, not duplicate.
        m = get_enabled_tenant_membership(db, tenant_id="default-tenant", user_email=email)
        m.is_enabled = False
        db.commit()
        ensure_bootstrap_admins(db)
        rows = (
            db.query(models.TenantMembership)
            .filter(
                models.TenantMembership.user_email == email,
                models.TenantMembership.tenant_id == "default-tenant",
            )
            .all()
        )
        assert len(rows) == 1
        assert rows[0].is_enabled is True
    finally:
        _clear(db, email, "default-tenant")
        db.close()


def test_only_listed_emails_provisioned(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_TENANT_ADMINS", "listed@example.com")
    monkeypatch.setenv("BOOTSTRAP_TENANT_ID", "default-tenant")
    db = SessionLocal()
    try:
        _clear(db, "listed@example.com", "default-tenant")
        ensure_bootstrap_admins(db)
        # An unlisted user must NOT get a membership from the bootstrap.
        assert (
            get_enabled_tenant_membership(
                db, tenant_id="default-tenant", user_email="unlisted@example.com"
            )
            is None
        )
    finally:
        _clear(db, "listed@example.com", "default-tenant")
        db.close()


def test_membership_response_does_not_500_on_live_model():
    """Regression: _membership_response read row.tenant_name/row.role_name which
    don't exist on the live model → AttributeError 500 on list/create/toggle."""
    from app.routes.tenant_admin import _membership_response

    db = SessionLocal()
    email = "resp-probe@example.com"
    try:
        _clear(db, email, "default-tenant")
        row = models.TenantMembership(
            user_email=email, tenant_id="default-tenant", role="spd_manager", is_enabled=True
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        resp = _membership_response(row)
        assert resp["user_email"] == email
        assert resp["tenant_id"] == "default-tenant"
        assert resp["role"] == "spd_manager"
        assert resp["role_name"] == "spd_manager"  # alias preserved for old clients
    finally:
        _clear(db, email, "default-tenant")
        db.close()
