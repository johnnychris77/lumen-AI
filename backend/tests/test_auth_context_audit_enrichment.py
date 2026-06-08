import json
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        return json.loads(raw)

    return raw


def test_build_auth_audit_details_merges_extra_details():
    from app.auth.audit_context import build_auth_audit_details
    from app.auth.context import build_dev_auth_context

    context = build_dev_auth_context(
        actor="audit-admin@example.com",
        role="hospital_admin",
        tenant_id="tenant-audit",
        tenant_name="Tenant Audit",
    )

    details = build_auth_audit_details(
        context,
        extra_details={"workflow": "governance_packet_export"},
    )

    assert details["actor"] == "audit-admin@example.com"
    assert details["actor_role"] == "hospital_admin"
    assert details["tenant_id"] == "tenant-audit"
    assert details["tenant_name"] == "Tenant Audit"
    assert details["auth_provider"] == "dev"
    assert details["workflow"] == "governance_packet_export"
    assert "governance_packet:export" in details["permissions"]


def test_centralized_audit_event_accepts_auth_context():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="audit-context@example.com",
            role="enterprise_admin",
            tenant_id="tenant-context",
            tenant_name="Tenant Context",
        )

        event = record_enterprise_audit_event(
            db,
            action_type="auth_context_audit_test",
            resource_type="auth_context_test",
            resource_id="audit-context-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            details={"business_event": "test"},
        )

        details = _details(event)

        assert details["business_event"] == "test"
        assert details["actor"] == "audit-context@example.com"
        assert details["actor_role"] == "enterprise_admin"
        assert details["tenant_id"] == "tenant-context"
        assert details["tenant_name"] == "Tenant Context"
        assert details["auth_provider"] == "dev"
        assert "audit:verify_chain" in details["permissions"]
        assert details["event_hash_algorithm"] == "SHA-256"
        assert len(details["event_hash"]) == 64
    finally:
        db.close()


def test_auth_context_does_not_override_explicit_details():
    from app.auth.audit_context import merge_auth_context_into_details
    from app.auth.context import build_dev_auth_context

    context = build_dev_auth_context(
        actor="real@example.com",
        role="hospital_admin",
        tenant_id="real-tenant",
        tenant_name="Real Tenant",
    )

    details = merge_auth_context_into_details(
        {
            "actor": "explicit@example.com",
            "tenant_id": "explicit-tenant",
            "custom": "kept",
        },
        context,
    )

    assert details["actor"] == "explicit@example.com"
    assert details["tenant_id"] == "explicit-tenant"
    assert details["custom"] == "kept"
    assert details["actor_role"] == "hospital_admin"
    assert details["tenant_name"] == "Real Tenant"
