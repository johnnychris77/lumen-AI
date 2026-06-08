import os

from fastapi.testclient import TestClient
from starlette.requests import Request

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": headers,
        }
    )


def test_audit_export_hash_verification_service_returns_verified_match():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_export_service import (
        export_audit_events_csv,
        record_audit_export_event,
    )
    from app.services.audit_export_verification_service import verify_audit_export_hash
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="verify-export@example.com",
            role="enterprise_admin",
            tenant_id="tenant-verify-export",
            tenant_name="Tenant Verify Export",
        )

        request = _request(
            [
                (b"x-request-id", b"req-verify-export"),
                (b"x-correlation-id", b"corr-verify-export"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_verify_test",
            resource_type="audit_export_verify_resource",
            resource_id="verify-export-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-export-verify"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-verify-export",
            action_type="audit_export_verify_test",
        )

        record_audit_export_event(
            db,
            actor=context.actor,
            actor_role=context.role,
            export_result=export,
        )

        result = verify_audit_export_hash(
            db,
            audit_export_hash=export["audit_export_hash"],
        )

        assert result["status"] == "success"
        assert result["verified"] is True
        assert result["audit_export_hash"] == export["audit_export_hash"]
        assert result["audit_export_hash_algorithm"] == "SHA-256"
        assert result["event_id"] is not None
        assert result["tamper_evident"] is True
    finally:
        db.close()


def test_audit_export_hash_verification_service_returns_false_for_unknown_hash():
    from app.db.session import SessionLocal
    from app.services.audit_export_verification_service import verify_audit_export_hash

    db = SessionLocal()
    try:
        result = verify_audit_export_hash(
            db,
            audit_export_hash="0" * 64,
        )

        assert result["status"] == "success"
        assert result["verified"] is False
        assert result["event_id"] is None
    finally:
        db.close()


def test_audit_export_hash_verification_endpoint_requires_admin_and_verifies_hash():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.audit_export_service import (
        export_audit_events_csv,
        record_audit_export_event,
    )
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="verify-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-verify-endpoint",
            tenant_name="Tenant Verify Endpoint",
        )

        request = _request(
            [
                (b"x-request-id", b"req-verify-endpoint"),
                (b"x-correlation-id", b"corr-verify-endpoint"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_verify_endpoint_test",
            resource_type="audit_export_verify_endpoint_resource",
            resource_id="verify-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-export-verify-endpoint"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-verify-endpoint",
            action_type="audit_export_verify_endpoint_test",
        )

        record_audit_export_event(
            db,
            actor=context.actor,
            actor_role=context.role,
            export_result=export,
        )

        export_hash = export["audit_export_hash"]
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/events/export/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "audit-export-verify-admin",
        },
        params={"audit_export_hash": export_hash},
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["verified"] is True
    assert payload["audit_export_hash"] == export_hash
    assert payload["event_id"] is not None

    vendor_response = client.get(
        "/api/enterprise/audit/events/export/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "audit-export-verify-vendor",
        },
        params={"audit_export_hash": export_hash},
    )

    assert vendor_response.status_code in {401, 403}
