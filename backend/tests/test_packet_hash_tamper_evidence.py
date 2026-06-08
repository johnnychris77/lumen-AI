import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_governance_packet_hash_verification_is_tamper_evident():
    from app.main import app

    client = TestClient(app)

    headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "tamper-evidence-reviewer",
    }

    finding_id = 1

    pdf_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert pdf_response.status_code == 200, pdf_response.text
    assert pdf_response.content.startswith(b"%PDF")

    history_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-export-history",
        headers=headers,
    )

    assert history_response.status_code == 200, history_response.text

    history = history_response.json()
    assert history["status"] == "success"
    assert history["export_count"] >= 1

    latest_pdf_export = next(
        item
        for item in history["exports"]
        if item.get("export_format") == "pdf" and item.get("packet_hash")
    )

    packet_hash = latest_pdf_export["packet_hash"]

    valid_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet/verify-hash",
        headers=headers,
        params={"packet_hash": packet_hash},
    )

    assert valid_response.status_code == 200, valid_response.text

    valid_result = valid_response.json()

    assert valid_result["status"] == "success"
    assert valid_result["verified"] is True
    assert valid_result["verification_status"] == "hash_matched_export_record"
    assert valid_result["packet_hash"] == packet_hash
    assert valid_result["packet_hash_algorithm"] == "SHA-256"
    assert valid_result["matched_export"]["packet_hash"] == packet_hash
    assert valid_result["matched_export"]["tamper_evident"] is True

    tampered_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet/verify-hash",
        headers=headers,
        params={"packet_hash": "0" * 64},
    )

    assert tampered_response.status_code == 200, tampered_response.text

    tampered_result = tampered_response.json()

    assert tampered_result["status"] == "success"
    assert tampered_result["verified"] is False
    assert tampered_result["verification_status"] == "hash_not_found"
    assert tampered_result["packet_hash"] == "0" * 64
    assert "matched_export" not in tampered_result or tampered_result["matched_export"] in ({}, None)
