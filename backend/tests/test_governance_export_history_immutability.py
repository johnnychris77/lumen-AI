import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _pdf_exports(history: dict) -> list[dict]:
    return [
        item
        for item in history.get("exports", [])
        if item.get("export_format") == "pdf" and item.get("packet_hash")
    ]


def test_governance_export_history_is_append_only_and_hashes_remain_stable():
    from app.main import app

    client = TestClient(app)

    headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "export-history-immutability-reviewer",
    }

    finding_id = 1

    first_pdf = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert first_pdf.status_code == 200, first_pdf.text
    assert first_pdf.content.startswith(b"%PDF")

    first_history_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-export-history",
        headers=headers,
    )

    assert first_history_response.status_code == 200, first_history_response.text

    first_history = first_history_response.json()
    first_exports = _pdf_exports(first_history)

    assert first_exports

    # The export-history endpoint may return only a recent window, so track the
    # newest export from the first response rather than every historical export.
    first_latest_export = first_exports[0]
    first_latest_event_id = first_latest_export["event_id"]
    first_latest_fingerprint = (
        first_latest_export["event_id"],
        first_latest_export["action_type"],
        first_latest_export["export_format"],
        first_latest_export["filename"],
        first_latest_export["packet_hash_algorithm"],
        first_latest_export["packet_hash"],
        first_latest_export["tamper_evident"],
        first_latest_export["created_at"],
    )

    second_pdf = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert second_pdf.status_code == 200, second_pdf.text
    assert second_pdf.content.startswith(b"%PDF")

    second_history_response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-export-history",
        headers=headers,
    )

    assert second_history_response.status_code == 200, second_history_response.text

    second_history = second_history_response.json()
    second_exports = _pdf_exports(second_history)

    second_export_ids = [item["event_id"] for item in second_exports]

    # The second export should create a new latest record.
    assert second_exports[0]["event_id"] != first_latest_event_id

    # The immediately previous export should still be present and unchanged.
    assert first_latest_event_id in second_export_ids

    second_fingerprints = {
        item["event_id"]: (
            item["event_id"],
            item["action_type"],
            item["export_format"],
            item["filename"],
            item["packet_hash_algorithm"],
            item["packet_hash"],
            item["tamper_evident"],
            item["created_at"],
        )
        for item in second_exports
    }

    assert second_fingerprints[first_latest_event_id] == first_latest_fingerprint

    latest_export = second_exports[0]

    assert latest_export["action_type"] == "governance_packet_exported_pdf"
    assert latest_export["export_format"] == "pdf"
    assert latest_export["packet_hash_algorithm"] == "SHA-256"
    assert latest_export["packet_hash"]
    assert latest_export["tamper_evident"] is True
