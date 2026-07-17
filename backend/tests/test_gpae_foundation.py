"""Project Foundation Sprint 1 (GPAE) — verification tests.

Covers the genuinely new Foundation surfaces:
  * governed object storage registry (register, dedup, verify-on-read,
    integrity fail-closed, tenant isolation, supersession versioning),
  * audit record immutability guards (instance + bulk ORM),
  * GPAE deep health check and truthful alert delivery reporting.

Long-standing invariants (LCID permanence, frozen-dataset immutability,
Ground Truth / annotation versioning, baseline lifecycle) are covered by
their own suites — see docs/foundation/FOUNDATION_ACCEPTANCE.md for the
mapping — and are not re-tested here.
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import update

from app.db.session import SessionLocal
from app.models.audit_log import AuditImmutabilityError, AuditLog
from app.models.governed_object import STATUS_SUPERSEDED, GovernedObject
from app.services import governed_object_service as gos
from app.services.gpae_monitoring_service import (
    deep_health_check,
    dispatch_platform_alert,
    run_monitoring_sweep,
)


def _payload() -> bytes:
    # Unique per call so reruns against a persistent test.db never collide.
    return b"gpae-test-object-" + uuid.uuid4().hex.encode()


def _tenant() -> str:
    return f"gpae-tenant-{uuid.uuid4().hex[:8]}"


class TestGovernedObjectStore:
    def test_register_returns_full_governance_record(self):
        db = SessionLocal()
        try:
            data = _payload()
            record = gos.register_object(
                db,
                tenant_id=_tenant(),
                data=data,
                object_category="supporting_evidence",
                uploader="tester@example.org",
                original_filename="evidence.bin",
            )
            assert record["object_id"].startswith("GOBJ-")
            assert record["sha256"] and len(record["sha256"]) == 64
            assert record["size_bytes"] == len(data)
            assert record["uploader"] == "tester@example.org"
            assert record["retention_policy"] == "retain_indefinitely"
            assert record["storage_uri"]
            assert record["version"] == 1
            assert record["status"] == "ACTIVE"
            assert record["deduplicated"] is False
        finally:
            db.close()

    def test_registration_writes_audit_event(self):
        db = SessionLocal()
        try:
            record = gos.register_object(
                db, tenant_id=_tenant(), data=_payload(), object_category="report"
            )
            events = (
                db.query(AuditLog)
                .filter(
                    AuditLog.resource_type == "governed_object",
                    AuditLog.resource_id == record["object_id"],
                    AuditLog.action_type == "governed_object_registered",
                )
                .all()
            )
            assert len(events) == 1
        finally:
            db.close()

    def test_duplicate_bytes_are_deduplicated_not_restored(self):
        db = SessionLocal()
        try:
            tenant = _tenant()
            data = _payload()
            first = gos.register_object(
                db, tenant_id=tenant, data=data, object_category="pdf"
            )
            second = gos.register_object(
                db, tenant_id=tenant, data=data, object_category="pdf"
            )
            assert second["deduplicated"] is True
            assert second["object_id"] == first["object_id"]
            rows = (
                db.query(GovernedObject)
                .filter(GovernedObject.tenant_id == tenant, GovernedObject.sha256 == first["sha256"])
                .count()
            )
            assert rows == 1
        finally:
            db.close()

    def test_load_and_verify_roundtrip(self):
        db = SessionLocal()
        try:
            tenant = _tenant()
            data = _payload()
            record = gos.register_object(
                db, tenant_id=tenant, data=data, object_category="dataset_export"
            )
            loaded = gos.load_and_verify_object(db, tenant_id=tenant, object_id=record["object_id"])
            assert loaded == data
            refreshed = gos.get_object_record(db, tenant_id=tenant, object_id=record["object_id"])
            assert refreshed["last_verified_at"] is not None
            assert refreshed["integrity_intact"] is True
        finally:
            db.close()

    def test_corrupted_bytes_fail_closed_and_are_audited(self):
        db = SessionLocal()
        try:
            tenant = _tenant()
            record = gos.register_object(
                db, tenant_id=tenant, data=_payload(), object_category="model_artifact"
            )
            # Corrupt the stored file directly (local backend stores at storage_uri).
            with open(record["storage_uri"], "wb") as fh:
                fh.write(b"corrupted-bytes")

            with pytest.raises(gos.GovernedObjectIntegrityError):
                gos.load_and_verify_object(db, tenant_id=tenant, object_id=record["object_id"])

            refreshed = gos.get_object_record(db, tenant_id=tenant, object_id=record["object_id"])
            assert refreshed["integrity_intact"] is False
            events = (
                db.query(AuditLog)
                .filter(
                    AuditLog.resource_id == record["object_id"],
                    AuditLog.action_type == "governed_object_integrity_failed",
                )
                .count()
            )
            assert events == 1
        finally:
            db.close()

    def test_tenant_isolation(self):
        db = SessionLocal()
        try:
            tenant_a, tenant_b = _tenant(), _tenant()
            record = gos.register_object(
                db, tenant_id=tenant_a, data=_payload(), object_category="thumbnail"
            )
            with pytest.raises(gos.GovernedObjectNotFoundError):
                gos.get_object_record(db, tenant_id=tenant_b, object_id=record["object_id"])
            assert gos.list_objects(db, tenant_id=tenant_b) == []
        finally:
            db.close()

    def test_supersession_creates_new_version_never_edits(self):
        db = SessionLocal()
        try:
            tenant = _tenant()
            v1 = gos.register_object(
                db, tenant_id=tenant, data=_payload(), object_category="baseline_image"
            )
            v2 = gos.register_object(
                db,
                tenant_id=tenant,
                data=_payload(),
                object_category="baseline_image",
                supersedes_object_id=v1["object_id"],
            )
            assert v2["object_id"] != v1["object_id"]
            assert v2["version"] == 2
            assert v2["supersedes_object_id"] == v1["object_id"]
            old = gos.get_object_record(db, tenant_id=tenant, object_id=v1["object_id"])
            assert old["status"] == STATUS_SUPERSEDED
            assert old["sha256"] == v1["sha256"]  # prior evidence unchanged
        finally:
            db.close()

    def test_rejects_empty_and_unknown_category(self):
        db = SessionLocal()
        try:
            with pytest.raises(gos.GovernedObjectError):
                gos.register_object(db, tenant_id=_tenant(), data=b"", object_category="pdf")
            with pytest.raises(gos.GovernedObjectError):
                gos.register_object(
                    db, tenant_id=_tenant(), data=_payload(), object_category="not-a-category"
                )
        finally:
            db.close()


class TestAuditImmutability:
    def _write_event(self, db) -> AuditLog:
        from app.services.enterprise_audit_service import record_enterprise_audit_event

        return record_enterprise_audit_event(
            db,
            action_type="gpae_immutability_probe",
            resource_type="gpae_test",
            resource_id=uuid.uuid4().hex,
        )

    def test_instance_update_is_blocked(self):
        db = SessionLocal()
        try:
            event = self._write_event(db)
            event.details = "tampered"
            with pytest.raises(AuditImmutabilityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_instance_delete_is_blocked(self):
        db = SessionLocal()
        try:
            event = self._write_event(db)
            db.delete(event)
            with pytest.raises(AuditImmutabilityError):
                db.commit()
        finally:
            db.rollback()
            db.close()

    def test_bulk_update_is_blocked(self):
        db = SessionLocal()
        try:
            self._write_event(db)
            with pytest.raises(AuditImmutabilityError):
                db.execute(update(AuditLog).values(details="mass-tamper"))
        finally:
            db.rollback()
            db.close()

    def test_bulk_delete_is_blocked(self):
        db = SessionLocal()
        try:
            self._write_event(db)
            with pytest.raises(AuditImmutabilityError):
                db.query(AuditLog).delete()
        finally:
            db.rollback()
            db.close()


class TestGpaeMonitoring:
    def test_deep_health_check_reports_all_components(self):
        db = SessionLocal()
        try:
            report = deep_health_check(db)
            expected = {
                "database",
                "alembic_version",
                "object_storage",
                "audit_logging",
                "model_registry",
                "baseline_resolution",
                "governed_objects",
            }
            assert set(report["components"]) == expected
            assert report["components"]["database"]["status"] == "ok"
            assert report["components"]["object_storage"]["status"] == "ok"
            assert report["overall_status"] in ("ok", "degraded")
        finally:
            db.close()

    def test_alert_without_destination_is_recorded_not_claimed_delivered(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("ALERT_EMAIL_TO", raising=False)
        db = SessionLocal()
        try:
            outcome = dispatch_platform_alert(
                db, severity="SEV-2", component="unit-test", message="probe"
            )
            assert outcome["delivery"] == "no_destination_configured"
            event = (
                db.query(AuditLog)
                .filter(
                    AuditLog.action_type == "platform_alert_raised",
                    AuditLog.resource_id == "unit-test",
                )
                .order_by(AuditLog.id.desc())
                .first()
            )
            assert event is not None
            assert "no_destination_configured" in event.details
        finally:
            db.close()

    def test_monitoring_sweep_healthy_raises_no_alerts(self):
        db = SessionLocal()
        try:
            report = run_monitoring_sweep(db)
            if report["overall_status"] == "ok":
                assert report["alerts_raised"] == []
            else:
                assert len(report["alerts_raised"]) == len(report["failed_components"])
        finally:
            db.close()


class TestSingleActiveProductionModel:
    def test_second_production_promotion_is_blocked(self, monkeypatch):
        from app.models.model_registry import ModelRegistryEntry
        from app.services.ml import candidate_promotion as cp

        db = SessionLocal()
        try:
            suffix = uuid.uuid4().hex[:8]
            incumbent = ModelRegistryEntry(
                model_id=f"gpae-incumbent-{suffix}",
                model_version="1.0",
                model_type="abnormality_screen",
                candidate_stage="Production",
            )
            challenger = ModelRegistryEntry(
                model_id=f"gpae-challenger-{suffix}",
                model_version="1.0",
                model_type="abnormality_screen",
                candidate_stage="Pilot",
            )
            db.add_all([incumbent, challenger])
            db.commit()

            # Isolate the invariant under test from the evidence checklist
            # (which is covered by its own suite).
            monkeypatch.setattr(
                cp,
                "evaluate_candidate_promotion",
                lambda *a, **k: {"allowed": True},
            )
            outcome = cp.promote_candidate(
                db, model=challenger, target_stage="Production", approver="tester"
            )
            assert outcome["allowed"] is False
            assert "already at Production" in outcome["blocked_reason"]
            db.refresh(challenger)
            assert challenger.candidate_stage == "Pilot"
        finally:
            # Clean up so this test never leaves a stray Production model
            # that would block other suites against a persistent test.db.
            db.rollback()
            for row in (
                db.query(ModelRegistryEntry)
                .filter(ModelRegistryEntry.model_id.like(f"gpae-%-{suffix}"))
                .all()
            ):
                db.delete(row)
            db.commit()
            db.close()


class TestObjectStorageEnvIsolation:
    def test_storage_dir_is_configurable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LUMENAI_LOCAL_STORAGE_DIR", str(tmp_path / "objstore"))
        db = SessionLocal()
        try:
            record = gos.register_object(
                db, tenant_id=_tenant(), data=_payload(), object_category="report"
            )
            assert record["storage_uri"].startswith(str(tmp_path / "objstore"))
            assert os.path.exists(record["storage_uri"])
        finally:
            db.close()
