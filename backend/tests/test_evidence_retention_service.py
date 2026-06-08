import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        return json.loads(raw)

    return raw


def test_retention_status_allows_deletion_after_expiration_without_legal_hold():
    from app.services.evidence_retention_service import (
        enforce_retention_deletion_allowed,
        evaluate_retention_status,
    )

    created_at = datetime.now(UTC) - timedelta(days=400)

    status = evaluate_retention_status(
        created_at=created_at,
        retention_days=365,
        legal_hold_enabled=False,
    )

    assert status["expired"] is True
    assert status["deletion_allowed"] is True
    assert status["deletion_blocked_reason"] == ""

    assert enforce_retention_deletion_allowed(retention_status=status) is True


def test_retention_status_blocks_deletion_when_legal_hold_enabled():
    from app.services.evidence_retention_service import (
        enforce_retention_deletion_allowed,
        evaluate_retention_status,
    )

    created_at = datetime.now(UTC) - timedelta(days=400)

    status = evaluate_retention_status(
        created_at=created_at,
        retention_days=365,
        legal_hold_enabled=True,
    )

    assert status["expired"] is True
    assert status["deletion_allowed"] is False
    assert status["deletion_blocked_reason"] == "legal_hold"

    with pytest.raises(HTTPException) as exc:
        enforce_retention_deletion_allowed(retention_status=status)

    assert exc.value.status_code == 423


def test_retention_status_blocks_deletion_before_expiration():
    from app.services.evidence_retention_service import (
        enforce_retention_deletion_allowed,
        evaluate_retention_status,
    )

    created_at = datetime.now(UTC) - timedelta(days=30)

    status = evaluate_retention_status(
        created_at=created_at,
        retention_days=365,
        legal_hold_enabled=False,
    )

    assert status["expired"] is False
    assert status["deletion_allowed"] is False

    with pytest.raises(HTTPException) as exc:
        enforce_retention_deletion_allowed(retention_status=status)

    assert exc.value.status_code == 409


def test_retention_decision_is_recorded_to_centralized_audit_service():
    from app.db.session import SessionLocal
    from app.services.evidence_retention_service import (
        evaluate_retention_status,
        record_retention_decision,
    )

    db = SessionLocal()
    try:
        created_at = datetime.now(UTC) - timedelta(days=400)

        status = evaluate_retention_status(
            created_at=created_at,
            retention_days=365,
            legal_hold_enabled=True,
        )

        event = record_retention_decision(
            db,
            resource_type="enterprise_governance_packet",
            resource_id="retention-test-packet",
            actor="retention-policy-test",
            actor_role="hospital_admin",
            retention_status=status,
            decision="deletion_blocked",
        )

        details = _details(event)

        assert event.action_type == "evidence_retention_decision_recorded"
        assert event.resource_type == "enterprise_governance_packet"
        assert event.resource_id == "retention-test-packet"
        assert details["decision"] == "deletion_blocked"
        assert details["legal_hold_enabled"] is True
        assert details["deletion_allowed"] is False
        assert details["deletion_blocked_reason"] == "legal_hold"
        assert details["event_hash_algorithm"] == "SHA-256"
        assert len(details["event_hash"]) == 64
    finally:
        db.close()
