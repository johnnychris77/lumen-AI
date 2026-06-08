import csv
import os
from io import StringIO

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


def _admin_headers():
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "enterprise_admin",
        "X-LumenAI-Actor": "audit-csv-admin",
    }


def test_audit_csv_export_service_returns_csv_with_filtered_event():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_export_service import export_audit_events_csv
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="csv-filter@example.com",
            role="enterprise_admin",
            tenant_id="tenant-csv-filter",
            tenant_name="Tenant CSV Filter",
        )

        request = _request(
            [
                (b"x-request-id", b"req-csv-filter"),
                (b"x-correlation-id", b"corr-csv-filter"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_csv_export_test",
            resource_type="audit_csv_resource",
            resource_id="csv-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "csv-export"},
        )

        export = export_audit_events_csv(
            db,
            tenant_id="tenant-csv-filter",
            correlation_id="corr-csv-filter",
            action_type="audit_csv_export_test",
        )

        assert export["status"] == "success"
        assert export["content_type"] == "text/csv"
        assert export["count"] >= 1
        assert "audit_csv_export_test" in export["csv"]

        rows = list(csv.DictReader(StringIO(export["csv"])))

        assert rows[0]["tenant_id"] == "tenant-csv-filter"
        assert rows[0]["correlation_id"] == "corr-csv-filter"
        assert rows[0]["action_type"] == "audit_csv_export_test"
        assert rows[0]["event_hash"]
    finally:
        db.close()


def test_audit_csv_export_endpoint_returns_csv_and_requires_admin_permission():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="csv-endpoint@example.com",
            role="enterprise_admin",
            tenant_id="tenant-csv-endpoint",
            tenant_name="Tenant CSV Endpoint",
        )

        request = _request(
            [
                (b"x-request-id", b"req-csv-endpoint"),
                (b"x-correlation-id", b"corr-csv-endpoint"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_csv_endpoint_test",
            resource_type="audit_csv_endpoint_resource",
            resource_id="csv-endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "csv-endpoint"},
        )
    finally:
        db.close()

    response = client.get(
        "/api/enterprise/audit/events/export.csv",
        headers=_admin_headers(),
        params={
            "tenant_id": "tenant-csv-endpoint",
            "correlation_id": "corr-csv-endpoint",
            "action_type": "audit_csv_endpoint_test",
        },
    )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert int(response.headers["x-lumenai-audit-export-count"]) >= 1
    assert "audit_csv_endpoint_test" in response.text

    rows = list(csv.DictReader(StringIO(response.text)))

    assert rows[0]["tenant_id"] == "tenant-csv-endpoint"
    assert rows[0]["correlation_id"] == "corr-csv-endpoint"

    vendor_response = client.get(
        "/api/enterprise/audit/events/export.csv",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "audit-csv-vendor",
        },
    )

    assert vendor_response.status_code in {401, 403}
