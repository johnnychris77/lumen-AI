import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_dev_auth_context_contains_actor_role_tenant_and_permissions():
    from app.auth.context import build_dev_auth_context

    context = build_dev_auth_context(
        actor="admin@example.com",
        role="hospital_admin",
        tenant_id="hospital-a",
        tenant_name="Hospital A",
    )

    assert context.actor == "admin@example.com"
    assert context.role == "hospital_admin"
    assert context.tenant_id == "hospital-a"
    assert context.tenant_name == "Hospital A"
    assert context.auth_provider == "dev"
    assert context.has_role({"hospital_admin"}) is True
    assert context.has_permission("governance_packet:export") is True
    assert context.has_permission("vendor_baseline:submit") is False


def test_auth_context_audit_details_are_normalized():
    from app.auth.context import build_dev_auth_context

    context = build_dev_auth_context(
        actor="audit@example.com",
        role="enterprise_admin",
        tenant_id="tenant-1",
        tenant_name="Tenant One",
    )

    details = context.to_audit_details()

    assert details["actor"] == "audit@example.com"
    assert details["actor_role"] == "enterprise_admin"
    assert details["tenant_id"] == "tenant-1"
    assert details["tenant_name"] == "Tenant One"
    assert details["auth_provider"] == "dev"
    assert "audit:verify_chain" in details["permissions"]
