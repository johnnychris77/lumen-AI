import json
import os
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./lumenai.db")



def _details(event) -> dict:
    raw_details = getattr(event, "details", {}) or {}

    if isinstance(raw_details, str):
        return json.loads(raw_details)

    return raw_details

def _get_value(event, key):
    if hasattr(event, key):
        return getattr(event, key)

    details = _details(event)
    return details.get(key)


def test_record_enterprise_audit_event_appends_standardized_event():
    from app.db.session import SessionLocal
    from app.models.audit_log import AuditLog
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        unique = str(uuid.uuid4())

        event = record_enterprise_audit_event(
            db,
            action_type="test_enterprise_audit_event_created",
            resource_type="test_resource",
            resource_id=unique,
            actor="audit-service-test",
            actor_role="hospital_admin",
            tenant_id="tenant-audit-test",
            finding_id=101,
            baseline_id=202,
            packet_hash="abc123",
            packet_hash_algorithm="SHA-256",
            details={
                "workflow_status": "created",
                "none_value_should_be_removed": None,
            },
        )

        assert event.id is not None
        assert _get_value(event, "action_type") == "test_enterprise_audit_event_created"
        assert _get_value(event, "resource_type") == "test_resource"
        assert _get_value(event, "resource_id") == unique
        assert _get_value(event, "actor") == "audit-service-test"
        assert _get_value(event, "actor_role") == "hospital_admin"
        assert _get_value(event, "tenant_id") == "tenant-audit-test"
        assert _get_value(event, "finding_id") == 101
        assert _get_value(event, "baseline_id") == 202
        assert _get_value(event, "packet_hash") == "abc123"
        assert _get_value(event, "packet_hash_algorithm") == "SHA-256"

        details = _details(event)
        assert details["workflow_status"] == "created"
        assert "none_value_should_be_removed" not in details

        persisted = (
            db.query(AuditLog)
            .filter(
                AuditLog.action_type == "test_enterprise_audit_event_created",
                AuditLog.resource_id == unique,
            )
            .first()
        )

        assert persisted is not None
        assert persisted.id == event.id
    finally:
        db.close()


def test_record_enterprise_audit_event_is_append_only_for_same_resource():
    from app.db.session import SessionLocal
    from app.models.audit_log import AuditLog
    from app.services.enterprise_audit_service import record_enterprise_audit_event

    db = SessionLocal()
    try:
        unique = str(uuid.uuid4())

        first_event = record_enterprise_audit_event(
            db,
            action_type="test_append_first",
            resource_type="test_append_resource",
            resource_id=unique,
            actor="audit-service-test",
            actor_role="system",
            details={"step": 1},
        )

        second_event = record_enterprise_audit_event(
            db,
            action_type="test_append_second",
            resource_type="test_append_resource",
            resource_id=unique,
            actor="audit-service-test",
            actor_role="system",
            details={"step": 2},
        )

        events = (
            db.query(AuditLog)
            .filter(
                AuditLog.resource_type == "test_append_resource",
                AuditLog.resource_id == unique,
            )
            .order_by(AuditLog.id.asc())
            .all()
        )

        assert len(events) == 2
        assert events[0].id == first_event.id
        assert events[1].id == second_event.id
        assert _get_value(events[0], "action_type") == "test_append_first"
        assert _get_value(events[1], "action_type") == "test_append_second"
        assert _details(events[0])["step"] == 1
        assert _details(events[1])["step"] == 2
    finally:
        db.close()
