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


def test_audit_export_service_includes_manifest_and_manifest_hash():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_export_service import export_audit_events_csv
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="manifest-export@example.com",
            role="enterprise_admin",
            tenant_id="tenant-export-manifest",
            tenant_name="Tenant Export Manifest",
        )

        request = _request(
            [
                (b"x-request-id", b"req-export-manifest"),
                (b"x-correlation-id", b"corr-export-manifest"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_manifest_test",
            resource_type="audit_export_manifest_resource",
            resource_id="export-manifest-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-export-manifest"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-export-manifest",
            action_type="audit_export_manifest_test",
        )

        expected_csv_hash = hashlib.sha256(export["csv"].encode("utf-8")).hexdigest()
        expected_manifest_hash = hashlib.sha256(
            export["manifest_json"].encode("utf-8")
        ).hexdigest()

        assert export["audit_export_hash"] == expected_csv_hash
        assert export["manifest"]["csv_hash"] == expected_csv_hash
        assert export["manifest"]["manifest_type"] == "lumenai_audit_export_manifest"
        assert export["manifest"]["tamper_evident"] is True
        assert export["manifest_hash"] == expected_manifest_hash
        assert len(export["manifest_hash"]) == 64
        assert export["manifest_hash_algorithm"] == "SHA-256"
        assert export["manifest"]["verification_url"].endswith(expected_csv_hash)
    finally:
        db.close()


def test_audit_export_event_records_manifest_hash():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.models.audit_log import AuditLog
    from app.services.audit_export_service import (
        export_audit_events_csv,
        record_audit_export_event,
    )
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="manifest-event@example.com",
            role="enterprise_admin",
            tenant_id="tenant-export-manifest-event",
            tenant_name="Tenant Export Manifest Event",
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_manifest_event_test",
            resource_type="audit_export_manifest_event_resource",
            resource_id="export-manifest-event-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            details={"workflow": "audit-export-manifest-event"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-export-manifest-event",
            action_type="audit_export_manifest_event_test",
        )

        record_audit_export_event(
            db,
            actor=context.actor,
            actor_role=context.role,
            export_result=export,
        )

        event = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "audit_events_csv_exported",
                AuditLog.resource_type == "enterprise_audit_export",
                AuditLog.resource_id == export["audit_export_hash"],
            )
            .order_by(AuditLog.id.desc())
            .first()
        )

        assert event is not None

        details = _details(event)

        assert details["audit_export_hash"] == export["audit_export_hash"]
        assert details["manifest_hash"] == export["manifest_hash"]
        assert details["manifest_hash_algorithm"] == "SHA-256"
        assert details["manifest"]["csv_hash"] == export["audit_export_hash"]
        assert details["event_hash_algorithm"] == "SHA-256"
    finally:
        db.close()


def test_audit_csv_export_endpoint_returns_manifest_hash_headers():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="manifest-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-export-manifest-endpoint",
            tenant_name="Tenant Export Manifest Endpoint",
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_export_manifest_endpoint_test",
            resource_type="audit_export_manifest_endpoint_resource",
            resource_id="export-manifest-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            details={"workflow": "audit-export-manifest-endpoint"},
        )
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/events/export.csv",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "enterprise_admin",
            "X-LumenAI-Actor": "audit-export-manifest-admin",
        },
        params={
            "tenant_id": "tenant-export-manifest-endpoint",
            "action_type": "audit_export_manifest_endpoint_test",
        },
    )

    assert response.status_code == 200, response.text
    assert response.headers["x-lumenai-audit-export-hash"]
    assert response.headers["x-lumenai-audit-export-hash-algorithm"] == "SHA-256"
    assert response.headers["x-lumenai-audit-manifest-hash"]
    assert response.headers["x-lumenai-audit-manifest-hash-algorithm"] == "SHA-256"
    assert len(response.headers["x-lumenai-audit-manifest-hash"]) == 64
