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


def test_compliance_evidence_bundle_service_builds_tamper_evident_bundle():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="bundle-service@example.com",
            role="enterprise_admin",
            tenant_id="tenant-bundle-service",
            tenant_name="Tenant Bundle Service",
        )

        request = _request(
            [
                (b"x-request-id", b"req-bundle-service"),
                (b"x-correlation-id", b"corr-bundle-service"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_bundle_service_test",
            resource_type="compliance_bundle_resource",
            resource_id="bundle-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-bundle-service"},
        )

        result = build_compliance_evidence_bundle(
            db,
            actor=context.actor,
            actor_role=context.role,
            tenant_id="tenant-bundle-service",
            action_type="compliance_bundle_service_test",
        )

        assert result["status"] == "success"
        assert result["bundle_hash_algorithm"] == "SHA-256"
        assert len(result["bundle_hash"]) == 64

        bundle = result["bundle"]

        assert bundle["bundle_type"] == "lumenai_compliance_evidence_bundle"
        assert bundle["tamper_evident"] is True
        assert bundle["generated_by"] == "bundle-service@example.com"
        assert bundle["audit_export"]["count"] >= 1
        assert len(bundle["audit_export"]["audit_export_hash"]) == 64
        assert len(bundle["manifest"]["manifest_hash"]) == 64
        assert bundle["audit_event"]["event_id"] is not None
        assert "audit_export_hash" in bundle["audit_export"]["audit_export_verification_url"]
        assert "manifest_hash" in bundle["manifest"]["manifest_verification_url"]
        assert "centralized_audit_logging" in bundle["compliance_controls"]
    finally:
        db.close()


def test_compliance_evidence_bundle_endpoint_requires_admin_and_returns_bundle():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="bundle-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-bundle-endpoint",
            tenant_name="Tenant Bundle Endpoint",
        )

        request = _request(
            [
                (b"x-request-id", b"req-bundle-endpoint"),
                (b"x-correlation-id", b"corr-bundle-endpoint"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_bundle_endpoint_test",
            resource_type="compliance_bundle_endpoint_resource",
            resource_id="bundle-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-bundle-endpoint"},
        )
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/evidence-bundle",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "bundle-admin",
        },
        params={
            "tenant_id": "tenant-bundle-endpoint",
            "action_type": "compliance_bundle_endpoint_test",
        },
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert len(payload["bundle_hash"]) == 64
    assert payload["bundle"]["bundle_type"] == "lumenai_compliance_evidence_bundle"
    assert payload["bundle"]["audit_export"]["count"] >= 1

    vendor_response = client.get(
        "/api/enterprise/audit/evidence-bundle",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "bundle-vendor",
        },
    )

    assert vendor_response.status_code in {401, 403}
