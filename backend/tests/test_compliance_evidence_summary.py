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


def test_compliance_evidence_summary_service_returns_safe_verified_summary():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
    from app.services.compliance_evidence_summary_service import (
        build_compliance_evidence_verification_summary,
    )
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="summary-service@example.com",
            role="enterprise_admin",
            tenant_id="tenant-summary-service",
            tenant_name="Tenant Summary Service",
        )

        request = _request(
            [
                (b"x-request-id", b"req-summary-service"),
                (b"x-correlation-id", b"corr-summary-service"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_summary_service_test",
            resource_type="compliance_summary_resource",
            resource_id="summary-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-summary-service"},
        )

        bundle_result = build_compliance_evidence_bundle(
            db,
            actor=context.actor,
            actor_role=context.role,
            tenant_id="tenant-summary-service",
            action_type="compliance_summary_service_test",
        )

        summary = build_compliance_evidence_verification_summary(
            db,
            bundle_hash=bundle_result["bundle_hash"],
        )

        assert summary["status"] == "success"
        assert summary["verified"] is True
        assert summary["summary_type"] == "lumenai_compliance_evidence_verification_summary"
        assert summary["bundle_hash"] == bundle_result["bundle_hash"]
        assert summary["bundle_hash_algorithm"] == "SHA-256"
        assert summary["bundle_type"] == "lumenai_compliance_evidence_bundle"
        assert summary["generated_by"] == "summary-service@example.com"
        assert summary["audit_export_hash"]
        assert summary["manifest_hash"]
        assert summary["tamper_evident"] is True
        assert summary["verification"]["bundle_verified"] is True
        assert summary["verification"]["audit_event_id"] is not None
        assert "centralized_audit_logging" in summary["compliance_controls"]

        # Public summary should not expose the full bundle object.
        assert "bundle" not in summary
    finally:
        db.close()


def test_compliance_evidence_summary_service_returns_false_for_unknown_hash():
    from app.db.session import SessionLocal
    from app.services.compliance_evidence_summary_service import (
        build_compliance_evidence_verification_summary,
    )

    db = SessionLocal()
    try:
        summary = build_compliance_evidence_verification_summary(
            db,
            bundle_hash="3" * 64,
        )

        assert summary["status"] == "success"
        assert summary["verified"] is False
        assert summary["bundle_hash"] == "3" * 64
    finally:
        db.close()


def test_compliance_evidence_summary_endpoint_requires_admin_and_returns_summary():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.compliance_evidence_bundle_service import build_compliance_evidence_bundle
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="summary-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-summary-endpoint",
            tenant_name="Tenant Summary Endpoint",
        )

        request = _request(
            [
                (b"x-request-id", b"req-summary-endpoint"),
                (b"x-correlation-id", b"corr-summary-endpoint"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_summary_endpoint_test",
            resource_type="compliance_summary_endpoint_resource",
            resource_id="summary-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-summary-endpoint"},
        )

        bundle_result = build_compliance_evidence_bundle(
            db,
            actor=context.actor,
            actor_role=context.role,
            tenant_id="tenant-summary-endpoint",
            action_type="compliance_summary_endpoint_test",
        )

        bundle_hash = bundle_result["bundle_hash"]
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/evidence-bundle/verification-summary",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "summary-admin",
        },
        params={"bundle_hash": bundle_hash},
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["verified"] is True
    assert payload["bundle_hash"] == bundle_hash
    assert payload["audit_export_hash"]
    assert payload["manifest_hash"]
    assert "bundle" not in payload

    vendor_response = client.get(
        "/api/enterprise/audit/evidence-bundle/verification-summary",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "summary-vendor",
        },
        params={"bundle_hash": bundle_hash},
    )

    assert vendor_response.status_code in {401, 403}
