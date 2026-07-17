"""Integration tests for the audit-writer unification.

app.audit.log_audit_event() -- used by cross-hospital intelligence routes
(global_intelligence.py / P23 GSIN, federated_horizon.py / Project Horizon,
network_benchmark.py, p20_network_intelligence.py, recall_signals.py,
atlas_enterprise.py, and ~70 other route modules) -- previously wrote plain,
non-hash-chained audit_logs rows, leaving those events outside the
tamper-evidence coverage that app.services.enterprise_audit_service already
provided. log_audit_event() now delegates to that hash-chained writer
internally, with no call-site changes required.

These tests confirm: (a) federated/cross-hospital intelligence events
produced through real API endpoints are hash-chained and verifiable via
app.services.audit_chain_verification_service.verify_audit_chain(), and
(b) tampering with a migrated event's stored record is detected.
"""
from __future__ import annotations

import json
import os
import uuid
import warnings

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)

ADMIN_AUTH = {"Authorization": "Bearer dev-token"}


def _details(event) -> dict:
    raw = getattr(event, "details", {}) or {}
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _set_details(db, event, details: dict) -> None:
    """Tamper with a stored audit event OUT-OF-BAND via raw SQL.

    Audit rows are ORM-immutable (GPAE Foundation guards in
    app.models.audit_log), so the direct-table tampering this test
    simulates must bypass the ORM — exactly the threat the hash chain
    exists to detect.
    """
    from sqlalchemy import text

    payload = json.dumps(details, sort_keys=True, default=str)
    db.execute(
        text("UPDATE audit_logs SET details = :details WHERE id = :id"),
        {"details": payload, "id": event.id},
    )
    db.commit()
    db.expire(event)


class TestLogAuditEventDelegatesToHashChain:
    def test_log_audit_event_emits_deprecation_warning(self):
        from app.audit import log_audit_event

        db = SessionLocal()
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                log_audit_event(
                    db,
                    tenant_id="audit-migration-test-tenant",
                    tenant_name="Audit Migration Test",
                    actor_email="tester@example.com",
                    actor_role="admin",
                    action_type="audit_migration_deprecation_check",
                    resource_type="audit_migration_test_resource",
                    resource_id=str(uuid.uuid4()),
                )
            assert any(issubclass(w.category, DeprecationWarning) for w in caught)
        finally:
            db.close()

    def test_log_audit_event_produces_hash_chained_record(self):
        from app.audit import log_audit_event
        from app.models.audit_log import AuditLog

        resource_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            event = log_audit_event(
                db,
                tenant_id="audit-migration-test-tenant",
                tenant_name="Audit Migration Test",
                actor_email="tester@example.com",
                actor_role="admin",
                action_type="audit_migration_hash_check",
                resource_type="audit_migration_test_resource",
                resource_id=resource_id,
                compliance_flag=True,
            )
            details = _details(event)
            assert len(details["event_hash"]) == 64
            assert details["event_hash_algorithm"] == "SHA-256"
            assert details["previous_event_hash"] == ""

            # Real columns that log_audit_event's own callers/consumers rely
            # on (e.g. routes/audit_logs.py's admin viewer and CSV/XLSX
            # export) must still be populated after the migration.
            persisted = db.query(AuditLog).filter_by(id=event.id).first()
            assert persisted.tenant_id == "audit-migration-test-tenant"
            assert persisted.tenant_name == "Audit Migration Test"
            assert persisted.actor_email == "tester@example.com"
            assert persisted.compliance_flag is True
        finally:
            db.close()


class TestFederatedIntelligenceEventsAreHashChained:
    """Task requirement: federated intelligence events -- aggregation,
    publish, benchmark queries, and cross-hospital data access -- must
    produce hash-chained audit records."""

    def test_contribute_and_publish_signal_produces_verified_hash_chain(self):
        """P23 GSIN: contribute a signal (aggregation intake) then approve
        it for network publication (publish) -- both audit events land on
        the same resource and must chain + verify."""
        from app.services.audit_chain_verification_service import verify_audit_chain

        tenant_id = f"gsin-tenant-{uuid.uuid4()}"
        headers = {**ADMIN_AUTH, "X-Tenant-Id": tenant_id}

        contribute = client.post(
            "/api/global-intelligence/contribute",
            json={
                "signal_type": "corrosion_pattern",
                "instrument_category": "laparoscope",
                "finding_type": "corrosion",
                "region": "north_america",
                "facility_count": 12,
                "signal_strength": 0.7,
                "trend_direction": "increasing",
                "association_reason": "audit migration test",
            },
            headers=headers,
        )
        assert contribute.status_code == 200, contribute.text
        signal_id = contribute.json()["signal_record_id"]

        review = client.post(
            f"/api/global-intelligence/signals/{signal_id}/review",
            json={"decision": "approve", "reviewer_notes": "audit migration test approval"},
            headers=headers,
        )
        assert review.status_code == 200, review.text

        db = SessionLocal()
        try:
            result = verify_audit_chain(
                db,
                resource_type="global_intelligence_signals",
                resource_id=str(signal_id),
            )
        finally:
            db.close()

        assert result["verified"] is True
        assert result["event_count"] == 2
        assert result["broken_event_id"] is None

    def test_horizon_participation_events_are_hash_chained(self):
        """Project Horizon is the real cross-hospital federated intelligence
        pipeline (enroll/contribute/benchmark/withdraw). Its audit events
        went through app.audit.log_audit_event and must now be chained."""
        from app.db import models
        from app.services.audit_chain_verification_service import verify_audit_chain

        tenant_id = f"horizon-tenant-{uuid.uuid4()}"

        db = SessionLocal()
        try:
            db.add(models.TenantMembership(
                tenant_id=tenant_id, user_email="spd_manager@local.dev", role="spd_manager", is_enabled=True,
            ))
            db.commit()
        finally:
            db.close()

        headers = {"Authorization": "Bearer manager-token", "x-tenant-id": tenant_id}

        enroll = client.post(
            "/api/horizon/participation/enroll",
            json={"participant_type": "hospital", "region": "north_america", "contribution_categories": ["benchmark"]},
            headers=headers,
        )
        assert enroll.status_code == 200, enroll.text

        withdraw = client.post("/api/horizon/participation/withdraw", headers=headers)
        assert withdraw.status_code == 200, withdraw.text

        db = SessionLocal()
        try:
            result = verify_audit_chain(
                db,
                resource_type="gsin_participants",
                resource_id=tenant_id,
            )
        finally:
            db.close()

        assert result["verified"] is True
        assert result["event_count"] == 2
        assert result["broken_event_id"] is None


class TestVerificationDetectsTamperingInMigratedEvents:
    def test_tampering_with_a_migrated_event_is_detected(self):
        from app.audit import log_audit_event
        from app.services.audit_chain_verification_service import verify_audit_chain

        resource_id = str(uuid.uuid4())
        db = SessionLocal()
        try:
            first_event = log_audit_event(
                db,
                tenant_id="audit-tamper-tenant",
                tenant_name="Audit Tamper Test",
                actor_email="tamper-tester@example.com",
                actor_role="admin",
                action_type="audit_migration_tamper_first",
                resource_type="audit_migration_tamper_resource",
                resource_id=resource_id,
                details={"finding_count": 3},
            )
            log_audit_event(
                db,
                tenant_id="audit-tamper-tenant",
                tenant_name="Audit Tamper Test",
                actor_email="tamper-tester@example.com",
                actor_role="admin",
                action_type="audit_migration_tamper_second",
                resource_type="audit_migration_tamper_resource",
                resource_id=resource_id,
                details={"finding_count": 5},
            )

            valid_result = verify_audit_chain(
                db,
                resource_type="audit_migration_tamper_resource",
                resource_id=resource_id,
            )
            assert valid_result["verified"] is True
            assert valid_result["event_count"] == 2
            assert valid_result["broken_event_id"] is None

            # Tamper with the first (migrated) event's stored payload, the
            # way an attacker modifying the audit_logs table directly would.
            details = _details(first_event)
            details["finding_count"] = 999
            _set_details(db, first_event, details)

            tampered_result = verify_audit_chain(
                db,
                resource_type="audit_migration_tamper_resource",
                resource_id=resource_id,
            )
            assert tampered_result["verified"] is False
            assert tampered_result["broken_event_id"] == first_event.id
        finally:
            db.close()
