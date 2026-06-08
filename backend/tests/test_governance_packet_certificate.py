import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_governance_packet_certificate_returns_latest_export_proof():
    from app.main import app

    client = TestClient(app)

    headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "certificate-reviewer",
    }

    finding_id = 1

    export_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert export_response.status_code == 200, export_response.text
    assert export_response.content.startswith(b"%PDF")

    certificate_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet/certificate",
        headers=headers,
    )

    assert certificate_response.status_code == 200, certificate_response.text

    certificate = certificate_response.json()

    assert certificate["status"] == "success"
    assert certificate["certificate_type"] == "lumenai_governance_packet_certificate"
    assert certificate["finding_id"] == finding_id
    assert certificate["resource_type"] == "enterprise_governance_packet"
    assert certificate["resource_id"] == str(finding_id)
    assert certificate["filename"] == f"lumenai-governance-packet-finding-{finding_id}.pdf"
    assert certificate["export_format"] == "pdf"
    assert certificate["packet_hash_algorithm"] == "SHA-256"
    assert len(certificate["packet_hash"]) == 64
    assert certificate["tamper_evident"] is True
    assert certificate["exported_by"] in {"certificate-reviewer", "unknown"}
    assert certificate["verification_url"].endswith(certificate["packet_hash"])
    assert "Governance packet certificate generated" in certificate["message"]


def test_governance_packet_certificate_requires_admin_access():
    from app.main import app

    client = TestClient(app)

    vendor_response = client.get(
        "/api/enterprise/intake/1/governance-packet/certificate",
        headers={
            "Authorization": "Bearer dev-token",
            "X-LumenAI-Role": "vendor",
            "X-LumenAI-Actor": "vendor-certificate-viewer",
        },
    )

    assert vendor_response.status_code in {401, 403}

    missing_auth_response = client.get(
        "/api/enterprise/intake/1/governance-packet/certificate"
    )

    assert missing_auth_response.status_code in {401, 403}
