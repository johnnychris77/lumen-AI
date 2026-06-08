import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _client():
    from app.main import app

    return TestClient(app)


def _admin_headers():
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "access-control-admin",
    }


def _vendor_headers():
    return {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "vendor",
        "X-LumenAI-Actor": "access-control-vendor",
    }


def test_hospital_admin_can_export_governance_packet_pdf():
    client = _client()

    response = client.get(
        "/api/enterprise/intake/1/governance-packet.pdf",
        headers=_admin_headers(),
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")


def test_vendor_cannot_export_governance_packet_pdf():
    client = _client()

    response = client.get(
        "/api/enterprise/intake/1/governance-packet.pdf",
        headers=_vendor_headers(),
    )

    assert response.status_code in {401, 403}


def test_missing_auth_cannot_export_governance_packet_pdf():
    client = _client()

    response = client.get("/api/enterprise/intake/1/governance-packet.pdf")

    assert response.status_code in {401, 403}


def test_vendor_cannot_view_governance_export_history():
    client = _client()

    response = client.get(
        "/api/enterprise/intake/1/governance-export-history",
        headers=_vendor_headers(),
    )

    assert response.status_code in {401, 403}


def test_vendor_cannot_verify_governance_packet_hash():
    client = _client()

    response = client.get(
        "/api/enterprise/intake/1/governance-packet/verify-hash",
        headers=_vendor_headers(),
        params={"packet_hash": "0" * 64},
    )

    assert response.status_code in {401, 403}
