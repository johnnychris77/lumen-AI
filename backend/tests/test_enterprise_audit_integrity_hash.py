import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}

    if isinstance(raw, str):
        return json.loads(raw)

    return raw


def test_enterprise_audit_event_includes_integrity_hash():
    from app.db.session import SessionLocal
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        unique = str(uuid.uuid4())

        event = record_enterprise_audit_event(
            db,
            action_type="test_integrity_hash_created",
            resource_type="audit_integrity_resource",
            resource_id=unique,
            actor="audit-integrity-test",
            actor_role="system",
            details={"step": 1},
        )

        details = _details(event)

        assert details["event_hash_algorithm"] == "SHA-256"
        assert len(details["event_hash"]) == 64
        assert details["previous_event_hash"] == ""
    finally:
        db.close()


def test_enterprise_audit_event_hash_chain_links_to_previous_event():
    from app.db.session import SessionLocal
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        unique = str(uuid.uuid4())

        first_event = record_enterprise_audit_event(
            db,
            action_type="test_integrity_hash_first",
            resource_type="audit_integrity_chain",
            resource_id=unique,
            actor="audit-integrity-test",
            actor_role="system",
            details={"step": 1},
        )

        first_details = _details(first_event)
        first_hash = first_details["event_hash"]

        second_event = record_enterprise_audit_event(
            db,
            action_type="test_integrity_hash_second",
            resource_type="audit_integrity_chain",
            resource_id=unique,
            actor="audit-integrity-test",
            actor_role="system",
            details={"step": 2},
        )

        second_details = _details(second_event)

        assert second_details["previous_event_hash"] == first_hash
        assert second_details["event_hash"] != first_hash
        assert len(second_details["event_hash"]) == 64
    finally:
        db.close()
