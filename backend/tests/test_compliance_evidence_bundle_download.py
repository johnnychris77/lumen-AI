import hashlib
import json
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


def test_compliance_evidence_bundle_download_returns_json_with_hash_headers():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="bundle-download@example.com",
            role="enterprise_admin",
            tenant_id="tenant-bundle-download",
            tenant_name="Tenant Bundle Download",
        )

        request = _request(
            [
                (b"x-request-id", b"req-bundle-download"),
                (b"x-correlation-id", b"corr-bundle-download"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="compliance_bundle_download_test",
            resource_type="compliance_bundle_download_resource",
            resource_id="bundle-download-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "compliance-bundle-download"},
        )
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/evidence-bundle/download.json",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "bundle-download-admin",
        },
        params={
            "tenant_id": "tenant-bundle-download",
            "action_type": "compliance_bundle_download_test",
        },
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]

    bundle_hash = response.headers["x-lumenai-bundle-hash"]

    assert response.headers["x-lumenai-bundle-hash-algorithm"] == "SHA-256"
    assert len(bundle_hash) == 64
    assert response.headers["x-lumenai-bundle-event-id"]

    payload = json.loads(response.text)

    assert payload["bundle_type"] == "lumenai_compliance_evidence_bundle"
    assert payload["bundle_hash"] == bundle_hash
    assert payload["bundle_hash_algorithm"] == "SHA-256"
    assert payload["audit_export"]["count"] >= 1
    assert payload["manifest"]["manifest_hash"]

    # Hash header should match the embedded bundle hash.
    assert payload["bundle_hash"] == bundle_hash


def test_compliance_evidence_bundle_download_requires_admin_permission():
    from app.main import app

    client = TestClient(app)

    response = client.get(
        "/api/enterprise/audit/evidence-bundle/download.json",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "bundle-download-vendor",
        },
    )

    assert response.status_code in {401, 403}
