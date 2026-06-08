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


def test_audit_export_manifest_verification_service_returns_verified_match():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_export_service import (
        export_audit_events_csv,
        record_audit_export_event,
    )
    from app.services.audit_export_verification_service import verify_audit_export_manifest_hash
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="manifest-verify@example.com",
            role="enterprise_admin",
            tenant_id="tenant-manifest-verify",
            tenant_name="Tenant Manifest Verify",
        )

        request = _request(
            [
                (b"x-request-id", b"req-manifest-verify"),
                (b"x-correlation-id", b"corr-manifest-verify"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_manifest_verify_test",
            resource_type="audit_manifest_verify_resource",
            resource_id="manifest-verify-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-manifest-verify"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-manifest-verify",
            action_type="audit_manifest_verify_test",
        )

        record_audit_export_event(
            db,
            actor=context.actor,
            actor_role=context.role,
            export_result=export,
        )

        result = verify_audit_export_manifest_hash(
            db,
            manifest_hash=export["manifest_hash"],
        )

        assert result["status"] == "success"
        assert result["verified"] is True
        assert result["manifest_hash"] == export["manifest_hash"]
        assert result["manifest_hash_algorithm"] == "SHA-256"
        assert result["audit_export_hash"] == export["audit_export_hash"]
        assert result["manifest"]["csv_hash"] == export["audit_export_hash"]
        assert result["event_id"] is not None
        assert result["tamper_evident"] is True
    finally:
        db.close()


def test_audit_export_manifest_verification_service_returns_false_for_unknown_hash():
    from app.db.session import SessionLocal
    from app.services.audit_export_verification_service import verify_audit_export_manifest_hash

    db = SessionLocal()
    try:
        result = verify_audit_export_manifest_hash(
            db,
            manifest_hash="1" * 64,
        )

        assert result["status"] == "success"
        assert result["verified"] is False
        assert result["event_id"] is None
    finally:
        db.close()


def test_audit_export_manifest_verification_endpoint_requires_admin_and_verifies_hash():
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
            actor="manifest-endpoint-verify@example.com",
            role="enterprise_admin",
            tenant_id="tenant-manifest-endpoint-verify",
            tenant_name="Tenant Manifest Endpoint Verify",
        )

        request = _request(
            [
                (b"x-request-id", b"req-manifest-endpoint-verify"),
                (b"x-correlation-id", b"corr-manifest-endpoint-verify"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_manifest_endpoint_verify_test",
            resource_type="audit_manifest_endpoint_verify_resource",
            resource_id="manifest-endpoint-verify-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-manifest-endpoint-verify"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-manifest-endpoint-verify",
            action_type="audit_manifest_endpoint_verify_test",
        )

        record_audit_export_event(
            db,
            actor=context.actor,
            actor_role=context.role,
            export_result=export,
        )

        manifest_hash = export["manifest_hash"]
        csv_hash = export["audit_export_hash"]
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/events/export/manifest/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "audit-manifest-verify-admin",
        },
        params={"manifest_hash": manifest_hash},
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["verified"] is True
    assert payload["manifest_hash"] == manifest_hash
    assert payload["audit_export_hash"] == csv_hash
    assert payload["event_id"] is not None

    vendor_response = client.get(
        "/api/enterprise/audit/events/export/manifest/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "audit-manifest-verify-vendor",
        },
        params={"manifest_hash": manifest_hash},
    )

    assert vendor_response.status_code in {401, 403}
