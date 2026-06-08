import json
import os

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


def test_request_context_reads_request_and_correlation_headers():
    from app.auth.request_context import build_request_audit_details

    request = _request(
        [
            (b"x-request-id", b"req-123"),
            (b"x-correlation-id", b"corr-456"),
        ]
    )

    details = build_request_audit_details(request)

    assert details["request_id"] == "req-123"
    assert details["correlation_id"] == "corr-456"


def test_request_context_generates_fallback_ids():
    from app.auth.request_context import build_request_audit_details

    details = build_request_audit_details(None)

    assert details["request_id"].startswith("req-")
    assert details["correlation_id"].startswith("corr-")


def test_auth_audit_details_include_request_context():
    from app.auth.audit_context import build_auth_audit_details
    from app.auth.context import build_dev_auth_context

    request = _request(
        [
            (b"x-request-id", b"req-auth-1"),
            (b"x-correlation-id", b"corr-auth-1"),
        ]
    )

    context = build_dev_auth_context(
        actor="request-audit@example.com",
        role="hospital_admin",
        tenant_id="tenant-request",
        tenant_name="Tenant Request",
    )

    details = build_auth_audit_details(
        context,
        request=request,
        extra_details={"workflow": "request_context_test"},
    )

    assert details["actor"] == "request-audit@example.com"
    assert details["request_id"] == "req-auth-1"
    assert details["correlation_id"] == "corr-auth-1"
    assert details["workflow"] == "request_context_test"


def test_centralized_audit_event_records_request_and_correlation_ids():
    from app.auth.context import build_dev_auth_context
    from app.db.session import SessionLocal
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    request = _request(
        [
            (b"x-request-id", b"req-central-1"),
            (b"x-correlation-id", b"corr-central-1"),
        ]
    )

    db = SessionLocal()
    try:
        context = build_dev_auth_context(
            actor="central-request@example.com",
            role="enterprise_admin",
            tenant_id="tenant-central",
            tenant_name="Tenant Central",
        )

        event = record_enterprise_audit_event(
            db,
            action_type="request_correlation_audit_test",
            resource_type="request_context_test",
            resource_id="request-context-1",
            actor=context.actor,
            actor_role=context.role,
            auth_context=context,
            request=request,
            details={"business_event": "request-correlation"},
        )

        details = _details(event)

        assert details["business_event"] == "request-correlation"
        assert details["actor"] == "central-request@example.com"
        assert details["tenant_id"] == "tenant-central"
        assert details["request_id"] == "req-central-1"
        assert details["correlation_id"] == "corr-central-1"
        assert details["event_hash_algorithm"] == "SHA-256"
        assert len(details["event_hash"]) == 64
    finally:
        db.close()


def test_explicit_request_ids_are_not_overwritten():
    from app.auth.audit_context import merge_auth_context_into_details
    from app.auth.context import build_dev_auth_context

    request = _request(
        [
            (b"x-request-id", b"req-header"),
            (b"x-correlation-id", b"corr-header"),
        ]
    )

    context = build_dev_auth_context(
        actor="explicit@example.com",
        role="hospital_admin",
        tenant_id="tenant-explicit",
        tenant_name="Tenant Explicit",
    )

    details = merge_auth_context_into_details(
        {
            "request_id": "req-explicit",
            "correlation_id": "corr-explicit",
        },
        context,
        request=request,
    )

    assert details["request_id"] == "req-explicit"
    assert details["correlation_id"] == "corr-explicit"
    assert details["actor"] == "explicit@example.com"
