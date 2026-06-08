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


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        return json.loads(raw)

    return raw


def test_audit_csv_export_service_includes_sha256_hash():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_export_service import export_audit_events_csv
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="hash-export@example.com",
            role="enterprise_admin",
            tenant_id="tenant-export-hash",
            tenant_name="Tenant Export Hash",
        )

        request = _request(
            [
                (b"x-request-id", b"req-export-hash"),
                (b"x-correlation-id", b"corr-export-hash"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_hash_test",
            resource_type="audit_export_hash_resource",
            resource_id="export-hash-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-export-hash"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-export-hash",
            action_type="audit_export_hash_test",
        )

        expected_hash = hashlib.sha256(export["csv"].encode("utf-8")).hexdigest()

        assert export["audit_export_hash_algorithm"] == "SHA-256"
        assert export["audit_export_hash"] == expected_hash
        assert len(export["audit_export_hash"]) == 64
        assert export["exported_at"]
    finally:
        db.close()


def test_audit_csv_export_endpoint_returns_hash_headers_and_records_audit_event():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.models.audit_log import AuditLog
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="hash-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-export-hash-endpoint",
            tenant_name="Tenant Export Hash Endpoint",
        )

        request = _request(
            [
                (b"x-request-id", b"req-export-hash-endpoint"),
                (b"x-correlation-id", b"corr-export-hash-endpoint"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_hash_endpoint_test",
            resource_type="audit_export_hash_endpoint_resource",
            resource_id="export-hash-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-export-hash-endpoint"},
        )
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/events/export.csv",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "audit-export-hash-admin",
        },
        params={
            "tenant_id": "tenant-export-hash-endpoint",
            "action_type": "audit_export_hash_endpoint_test",
        },
    )

    assert response.status_code == 200, response.text

    export_hash = response.headers["x-lumenai-audit-export-hash"]
    expected_hash = hashlib.sha256(response.text.encode("utf-8")).hexdigest()

    assert response.headers["x-lumenai-audit-export-hash-algorithm"] == "SHA-256"
    assert export_hash == expected_hash
    assert len(export_hash) == 64
    assert response.headers["x-lumenai-audit-exported-at"]

    db = SessionLocal()
    try:
        event = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "audit_events_csv_exported",
                AuditLog.resource_type == "enterprise_audit_export",
                AuditLog.resource_id == export_hash,
            )
            .order_by(AuditLog.id.desc())
            .first()
        )

        assert event is not None

        details = _details(event)

        assert details["audit_export_hash"] == export_hash
        assert details["audit_export_hash_algorithm"] == "SHA-256"
        assert details["tamper_evident"] is True
        assert details["export_count"] >= 1
        assert details["event_hash_algorithm"] == "SHA-256"
    finally:
        db.close()
