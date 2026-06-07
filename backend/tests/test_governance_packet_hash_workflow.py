import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def test_governance_packet_export_history_and_hash_verification():
    from app.main import app

    client = TestClient(app)

    headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "pytest-reviewer",
    }

    finding_id = 1

    pdf_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert pdf_response.status_code == 200, pdf_response.text
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    history_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-export-history",
        headers=headers,
    )

    assert history_response.status_code == 200, history_response.text

    history_data = history_response.json()

    assert history_data["status"] == "success"
    assert history_data["finding_id"] == finding_id
    assert history_data["export_count"] >= 1

    latest_export = history_data["exports"][0]

    assert latest_export["action_type"] == "governance_packet_exported_pdf"
    assert latest_export["export_format"] == "pdf"
    assert latest_export["filename"].endswith(".pdf")
    assert latest_export["included_vendor_baseline_audit_trail"] is True
    assert latest_export["packet_hash_algorithm"] == "SHA-256"
    assert latest_export["packet_hash"]
    assert latest_export["tamper_evident"] is True

    packet_hash = latest_export["packet_hash"]

    verify_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet/verify-hash",
        headers=headers,
        params={"packet_hash": packet_hash},
    )

    assert verify_response.status_code == 200, verify_response.text

    verify_data = verify_response.json()

    assert verify_data["status"] == "success"
    assert verify_data["finding_id"] == finding_id
    assert verify_data["verified"] is True
    assert verify_data["verification_status"] == "hash_matched_export_record"
    assert verify_data["packet_hash_algorithm"] == "SHA-256"
    assert verify_data["packet_hash"] == packet_hash
    assert verify_data["matched_export"]["packet_hash"] == packet_hash
    assert verify_data["matched_export"]["tamper_evident"] is True

    bad_hash_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet/verify-hash",
        headers=headers,
        params={"packet_hash": "bad123"},
    )

    assert bad_hash_response.status_code == 200, bad_hash_response.text

    bad_hash_data = bad_hash_response.json()

    assert bad_hash_data["status"] == "success"
    assert bad_hash_data["finding_id"] == finding_id
    assert bad_hash_data["verified"] is False
    assert bad_hash_data["verification_status"] == "hash_not_found"
