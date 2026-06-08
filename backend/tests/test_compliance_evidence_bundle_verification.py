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


def test_compliance_evidence_bundle_verification_service_returns_verified_match():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
    from app.services.compliance_evidence_bundle_verification_service import (
        verify_compliance_evidence_bundle_hash,
    )
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="bundle-verify@example.com",
            role="enterprise_admin",
            tenant_id="tenant-bundle-verify",
            tenant_name="Tenant Bundle Verify",
        )

        request = _request(
            [
                (b"x-request-id", b"req-bundle-verify"),
                (b"x-correlation-id", b"corr-bundle-verify"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_bundle_verify_test",
            resource_type="compliance_bundle_verify_resource",
            resource_id="bundle-verify-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-bundle-verify"},
        )

        bundle_result = build_compliance_evidence_bundle(
            db,
            actor=context.actor,
            actor_role=context.role,
            tenant_id="tenant-bundle-verify",
            action_type="compliance_bundle_verify_test",
        )

        result = verify_compliance_evidence_bundle_hash(
            db,
            bundle_hash=bundle_result["bundle_hash"],
        )

        assert result["status"] == "success"
        assert result["verified"] is True
        assert result["bundle_hash"] == bundle_result["bundle_hash"]
        assert result["bundle_hash_algorithm"] == "SHA-256"
        assert result["event_id"] == bundle_result["bundle_event_id"]
        assert result["audit_export_hash"]
        assert result["manifest_hash"]
        assert result["tamper_evident"] is True
    finally:
        db.close()


def test_compliance_evidence_bundle_verification_service_returns_false_for_unknown_hash():
    from app.db.session import SessionLocal
    from app.services.compliance_evidence_bundle_verification_service import (
        verify_compliance_evidence_bundle_hash,
    )

    db = SessionLocal()
    try:
        result = verify_compliance_evidence_bundle_hash(
            db,
            bundle_hash="2" * 64,
        )

        assert result["status"] == "success"
        assert result["verified"] is False
        assert result["event_id"] is None
    finally:
        db.close()


def test_compliance_evidence_bundle_verification_endpoint_requires_admin_and_verifies_hash():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="bundle-endpoint-verify@example.com",
            role="enterprise_admin",
            tenant_id="tenant-bundle-endpoint-verify",
            tenant_name="Tenant Bundle Endpoint Verify",
        )

        request = _request(
            [
                (b"x-request-id", b"req-bundle-endpoint-verify"),
                (b"x-correlation-id", b"corr-bundle-endpoint-verify"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_bundle_endpoint_verify_test",
            resource_type="compliance_bundle_endpoint_verify_resource",
            resource_id="bundle-endpoint-verify-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-bundle-endpoint-verify"},
        )

        bundle_result = build_compliance_evidence_bundle(
            db,
            actor=context.actor,
            actor_role=context.role,
            tenant_id="tenant-bundle-endpoint-verify",
            action_type="compliance_bundle_endpoint_verify_test",
        )

        bundle_hash = bundle_result["bundle_hash"]
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/evidence-bundle/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "bundle-verify-admin",
        },
        params={"bundle_hash": bundle_hash},
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["verified"] is True
    assert payload["bundle_hash"] == bundle_hash
    assert payload["event_id"] is not None
    assert payload["audit_export_hash"]
    assert payload["manifest_hash"]

    vendor_response = client.get(
        "/api/enterprise/audit/evidence-bundle/verify",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "bundle-verify-vendor",
        },
        params={"bundle_hash": bundle_hash},
    )

    assert vendor_response.status_code in {401, 403}
