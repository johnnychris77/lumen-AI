import json
import os
import uuid

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        return json.loads(raw)

    return raw


def _set_details(event, details: dict):
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        event.details = json.dumps(details, sort_keys=True, default=str)
    else:
        event.details = details


def test_audit_chain_verification_service_detects_valid_and_tampered_chain():
    from app.db.session import SessionLocal
    from app.services.audit_chain_verification_service import verify_audit_chain
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        resource_id = str(uuid.uuid4())

        first_event = record_enterprise_audit_event(
            db,
            action_type="test_chain_first",
            resource_type="audit_chain_test",
            resource_id=resource_id,
            actor="chain-test",
            actor_role="system",
            details={"step": 1},
        )

        record_enterprise_audit_event(
            db,
            action_type="test_chain_second",
            resource_type="audit_chain_test",
            resource_id=resource_id,
            actor="chain-test",
            actor_role="system",
            details={"step": 2},
        )

        valid_result = verify_audit_chain(
            db,
            resource_type="audit_chain_test",
            resource_id=resource_id,
        )

        assert valid_result["verified"] is True
        assert valid_result["event_count"] == 2
        assert valid_result["broken_event_id"] is None

        details = _details(first_event)
        details["step"] = "tampered"
        _set_details(first_event, details)

        db.add(first_event)
        db.commit()

        tampered_result = verify_audit_chain(
            db,
            resource_type="audit_chain_test",
            resource_id=resource_id,
        )

        assert tampered_result["verified"] is False
        assert tampered_result["broken_event_id"] == first_event.id
    finally:
        db.close()


def test_audit_chain_verification_endpoint_requires_admin_and_returns_valid_result():
    from app.db.session import SessionLocal
    from app.main import app
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    client = TestClient(app)

    resource_id = str(uuid.uuid4())

    db = SessionLocal()
    try:
        record_enterprise_audit_event(
            db,
            action_type="test_chain_endpoint",
            resource_type="audit_chain_endpoint_test",
            resource_id=resource_id,
            actor="chain-endpoint-test",
            actor_role="system",
            details={"step": "endpoint"},
        )
    finally:
        db.close()

    admin_headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "audit-chain-verifier",
    }

    response = client.get(
        "/api/enterprise/audit/verify-chain",
        headers=admin_headers,
        params={
            "resource_type": "audit_chain_endpoint_test",
            "resource_id": resource_id,
        },
    )

    assert response.status_code == 200, response.text

    payload = response.json()

    assert payload["status"] == "success"
    assert payload["verified"] is True
    assert payload["event_count"] == 1
    assert payload["broken_event_id"] is None

    vendor_response = client.get(
        "/api/enterprise/audit/verify-chain",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "vendor-chain-viewer",
        },
        params={
            "resource_type": "audit_chain_endpoint_test",
            "resource_id": resource_id,
        },
    )

    assert vendor_response.status_code in {401, 403}
