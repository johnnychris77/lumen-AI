import json
import os

from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def test_governance_packet_pdf_export_writes_centralized_audit_event():
    from app.main import app
    from app.db.session import SessionLocal
    from app.models.audit_log import AuditLog

    client = TestClient(app)

    headers = {
        "Authorization": "Bearer dev-token",
        "X-LumenAI-Role": "hospital_admin",
        "X-LumenAI-Actor": "centralized-audit-export-reviewer",
    }

    finding_id = 1

    response = client.get(
        f"/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF")

    db = SessionLocal()
    try:
        event = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "centralized_governance_packet_exported_pdf",
                AuditLog.resource_type == "enterprise_governance_packet",
                AuditLog.resource_id == str(finding_id),
            )
            .order_by(AuditLog.id.desc())
            .first()
        )

        assert event is not None

        details = _details(event)

        assert details["legacy_action_type"] == "governance_packet_exported_pdf"
        assert details["packet_hash"]
        assert details["packet_hash_algorithm"] == "SHA-256"
        assert details["export_format"] == "pdf"
        assert details["tamper_evident"] is True
        assert details["workflow_status"] == "governance_packet_exported_pdf"
    finally:
        db.close()
