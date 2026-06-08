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


def test_audit_query_service_filters_by_tenant_actor_and_correlation_id():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.audit_query_service import query_audit_events
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="filter-user@example.com",
            role="hospital_admin",
            tenant_id="tenant-filter",
            tenant_name="Tenant Filter",
        )

        request = _request(
            [
                (b"x-request-id", b"req-filter-1"),
                (b"x-correlation-id", b"corr-filter-1"),
            ]
        )

        event = record_enterprise_audit_event(
            db,
            action_type="audit_filter_test",
            resource_type="audit_filter_resource",
            resource_id="filter-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "audit-filter"},
        )

        result = query_audit_events(
            db,
            tenant_id="tenant-filter",
            actor="filter-user@example.com",
            correlation_id="corr-filter-1",
            action_type="audit_filter_test",
            resource_type="audit_filter_resource",
            resource_id="filter-resource-1",
        )

        assert result["status"] == "success"
        assert result["count"] >= 1

        first = result["events"][0]

        assert first["id"] == event.id
        assert first["tenant_id"] == "tenant-filter"
        assert first["actor"] == "filter-user@example.com"
        assert first["correlation_id"] == "corr-filter-1"
        assert first["request_id"] == "req-filter-1"
        assert first["event_hash"]

        miss = query_audit_events(
            db,
            tenant_id="wrong-tenant",
            action_type="audit_filter_test",
        )

        assert miss["count"] == 0
    finally:
        db.close()


def test_audit_events_endpoint_requires_admin_permission_and_filters_results():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="endpoint-filter@example.com",
            role="enterprise_admin",
            tenant_id="tenant-endpoint-filter",
            tenant_name="Tenant Endpoint Filter",
        )

        request = _request(
            [
                (b"x-request-id", b"req-endpoint-filter"),
                (b"x-correlation-id", b"corr-endpoint-filter"),
            ]
        )

        record_enterprise_audit_event(
            db,
            action_type="audit_endpoint_filter_test",
            resource_type="audit_endpoint_resource",
            resource_id="endpoint-resource-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"workflow": "endpoint-filter"},
        )
    finally:
        db.close()

    admin_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "enterprise_admin",
        "X-LumenAI-Actor": "audit-query-admin",
    }

    response = client.get(
        "/api/enterprise/audit/events",
        headers=admin_headers,
        params={
            "tenant_id": "tenant-endpoint-filter",
            "correlation_id": "corr-endpoint-filter",
            "action_type": "audit_endpoint_filter_test",
        },
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["count"] >= 1
    assert payload["events"][0]["tenant_id"] == "tenant-endpoint-filter"
    assert payload["events"][0]["correlation_id"] == "corr-endpoint-filter"

    vendor_response = client.get(
        "/api/enterprise/audit/events",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "audit-query-vendor",
        },
    )

    assert vendor_response.status_code in {401, 403}
