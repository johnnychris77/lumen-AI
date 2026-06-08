import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _client():
    from app.main import app

    return TestClient(app)


def _headers(role: str, actor: str):
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": role,
        "X-LumenAI-Actor": actor,
    }


def test_governance_packet_export_uses_permission_guard():
    client = _client()

    admin_response = client.get(
        "/api/enterprise/intake/1/governance-packet.pdf",
        headers=_headers("hospital_admin", "permission-route-admin"),
    )

    assert admin_response.status_code == 200, admin_response.text

    vendor_response = client.get(
        "/api/enterprise/intake/1/governance-packet.pdf",
        headers=_headers("vendor", "permission-route-vendor"),
    )

    assert vendor_response.status_code in {401, 403}


def test_governance_packet_hash_verify_uses_permission_guard():
    client = _client()

    vendor_response = client.get(
        "/api/enterprise/intake/1/governance-packet/verify-hash",
        headers=_headers("vendor", "permission-route-vendor"),
        params={"packet_hash": "0" * 64},
    )

    assert vendor_response.status_code in {401, 403}


def test_governance_packet_certificate_uses_permission_guard():
    client = _client()

    vendor_response = client.get(
        "/api/enterprise/intake/1/governance-packet/certificate",
        headers=_headers("vendor", "permission-route-vendor"),
    )

    assert vendor_response.status_code in {401, 403}


def test_vendor_baseline_library_uses_permission_guard():
    client = _client()

    admin_response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_headers("hospital_admin", "permission-route-admin"),
    )

    assert admin_response.status_code == 200, admin_response.text

    vendor_response = client.get(
        "/api/enterprise/vendor-baseline-subscription/baselines",
        headers=_headers("vendor", "permission-route-vendor"),
    )

    assert vendor_response.status_code in {401, 403}


def test_audit_chain_verify_uses_permission_guard():
    client = _client()

    vendor_response = client.get(
        "/api/enterprise/audit/verify-chain",
        headers=_headers("vendor", "permission-route-vendor"),
        params={
            "resource_type": "nonexistent",
            "resource_id": "none",
        },
    )

    assert vendor_response.status_code in {401, 403}
