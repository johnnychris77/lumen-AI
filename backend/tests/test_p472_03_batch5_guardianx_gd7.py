"""P472-03 Batch 5 — B5.4 GuardianX evidence ledger (GD-7).

``guardianx_evidence_ledger_entries`` has no tenant column; whether the ledger is
platform-wide or tenant-owned is governance decision **GD-7 — unsigned**.

* ``TestControls`` — already enforced.
* ``TestIntegrity`` — policy-independent integrity defects, FIXED in this batch:
  the paired audit event hashed the source and versions but NOT the evidence
  content, and ``verify`` never compared the ledger's stored signature with the
  audit chain — so evidence or signatures edited in the database still
  "verified". (Reproduced before the fix: these tests failed.)
* ``TestOpenOwnershipFindings`` — cross-tenant ledger exposures, STRICT expected
  failures (tripwires = open findings = release blockers) until GD-7 is signed.
* ``TestOwnershipClassificationDryRun`` — the read-only classifier that a
  GD-7-approved migration would use. It attributes nothing; it only reports
  which historical rows are attributable and which must be quarantined.
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.audit_log import AuditImmutabilityError, AuditLog
from app.models.guardianx_assurance import EvidenceLedgerEntry
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token
from app.services import guardianx_ledger_ownership as ownership

RUN = uuid.uuid4().hex[:8]
TENANT_A, TENANT_B = f"b54-a-{RUN}", f"b54-b-{RUN}"
USER_A, USER_B = f"b54-user-a-{RUN}@example.com", f"b54-user-b-{RUN}@example.com"
BASE = "/api/guardianx/evidence"

client = TestClient(app, raise_server_exceptions=False)


def _gd7(finding: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding} (pending GD-7): {summary}")


def _h(user: str, tenant: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}", "X-Tenant-Id": tenant}


@pytest.fixture(scope="module", autouse=True)
def _users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user in (USER_A, USER_B):
            db.add(UserRoleAssignment(username=user, role="admin", assigned_by="p472-03-batch5"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memberships(_users):
    db = SessionLocal()
    try:
        for tenant, user in ((TENANT_A, USER_A), (TENANT_B, USER_B)):
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="admin", is_enabled=True))
        db.commit()
    finally:
        db.close()


def _record(user=USER_A, tenant=TENANT_A, source_id=None, evidence=None) -> dict:
    body = {"source_type": "capa_suggestion", "source_id": source_id or f"src-{uuid.uuid4().hex[:8]}",
            "evidence": evidence or ["finding-1", "finding-2"], "knowledge_version": "kb-v3",
            "model_version": "1.0.0", "workflow_version": "2"}
    response = client.post(BASE, headers=_h(user, tenant), json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _verify(entry_id: int, user=USER_A, tenant=TENANT_A) -> dict:
    response = client.get(f"{BASE}/{entry_id}/verify", headers=_h(user, tenant))
    assert response.status_code == 200, response.text
    return response.json()


def _sql(statement: str, **params) -> None:
    db = SessionLocal()
    try:
        db.execute(text(statement), params)
        db.commit()
    finally:
        db.close()


class TestControls:
    def test_unauthenticated_callers_are_refused(self):
        assert client.get(f"{BASE}/1").status_code == 401
        assert client.post(BASE, json={"source_type": "x", "source_id": "y"}).status_code == 401

    def test_the_audit_event_is_attributed_to_the_verified_tenant(self):
        entry = _record()
        db = SessionLocal()
        try:
            event = db.query(AuditLog).filter(AuditLog.resource_type == ownership.RESOURCE_TYPE,
                                              AuditLog.resource_id == str(entry["id"])).one()
        finally:
            db.close()
        assert event.tenant_id == TENANT_A

    def test_a_fresh_entry_verifies(self):
        result = _verify(_record()["id"])
        assert result["verified"] is True

    def test_the_application_refuses_to_modify_an_audit_record(self):
        entry = _record()
        db = SessionLocal()
        try:
            event = db.query(AuditLog).filter(AuditLog.resource_type == ownership.RESOURCE_TYPE,
                                              AuditLog.resource_id == str(entry["id"])).one()
            event.actor_email = "forged@example.com"
            with pytest.raises(AuditImmutabilityError):
                db.commit()
        finally:
            db.rollback()
            db.close()


class TestIntegrity:
    def test_editing_the_evidence_content_is_detected(self):
        entry = _record(evidence=["the original finding"])
        _sql("UPDATE guardianx_evidence_ledger_entries SET evidence_json = :e WHERE id = :i",
             e=json.dumps(["a substituted finding"]), i=entry["id"])
        result = _verify(entry["id"])
        assert result["verified"] is False
        assert result["evidence_digest_matches"] is False

    def test_editing_the_stored_signature_is_detected(self):
        entry = _record()
        _sql("UPDATE guardianx_evidence_ledger_entries SET digital_signature = :s WHERE id = :i",
             s="0" * 64, i=entry["id"])
        result = _verify(entry["id"])
        assert result["verified"] is False
        assert result["signature_matches"] is False

    def test_editing_the_versions_is_detected(self):
        entry = _record()
        _sql("UPDATE guardianx_evidence_ledger_entries SET model_version = '9.9.9' WHERE id = :i", i=entry["id"])
        assert _verify(entry["id"])["verified"] is False

    def test_a_legacy_entry_without_a_sealed_digest_does_not_verify(self):
        # Simulate an entry written before this batch: its audit details carry no evidence digest.
        db = SessionLocal()
        try:
            row = EvidenceLedgerEntry(source_type="capa_suggestion", source_id=f"legacy-{RUN}",
                                      evidence_json=json.dumps(["x"]), reviewer="legacy@example.com")
            db.add(row)
            db.commit()
            from app.services.enterprise_audit_service import record_enterprise_audit_event
            audit = record_enterprise_audit_event(
                db, action_type="guardianx.evidence_recorded", resource_type=ownership.RESOURCE_TYPE,
                resource_id=str(row.id), actor="legacy@example.com", tenant_id=TENANT_A,
                details={"source_type": "capa_suggestion", "source_id": f"legacy-{RUN}",
                         "knowledge_version": "", "model_version": "", "workflow_version": ""})
            details = audit.details if isinstance(audit.details, dict) else json.loads(audit.details or "{}")
            row.digital_signature = details.get("event_hash", "")
            db.commit()
            legacy_id = row.id
        finally:
            db.close()
        result = _verify(legacy_id)
        assert result["verified"] is False
        assert result["evidence_digest_matches"] is None
        assert result["integrity"] == "legacy_unsealed_evidence"


class TestOpenOwnershipFindings:
    @_gd7("GD7-01", "another tenant can read a ledger entry by id")
    def test_another_tenant_cannot_read_an_entry_by_id(self):
        entry = _record()
        assert client.get(f"{BASE}/{entry['id']}", headers=_h(USER_B, TENANT_B)).status_code == 404

    @_gd7("GD7-02", "listing by source returns every tenant's entries for that source key")
    def test_listing_by_source_returns_only_own_entries(self):
        source = f"shared-{uuid.uuid4().hex[:8]}"
        _record(source_id=source)
        listed = client.get(BASE, headers=_h(USER_B, TENANT_B),
                            params={"source_type": "capa_suggestion", "source_id": source}).json()["entries"]
        assert listed == []

    @_gd7("GD7-03", "another tenant can run verification of an entry (chain metadata), contrary to GD-2")
    def test_another_tenant_cannot_verify_an_entry(self):
        entry = _record()
        assert client.get(f"{BASE}/{entry['id']}/verify", headers=_h(USER_B, TENANT_B)).status_code == 404

    @_gd7("GD7-04", "the reviewer's user identity (email) is disclosed to other tenants")
    def test_reviewer_identity_is_not_disclosed_cross_tenant(self):
        entry = _record()
        response = client.get(f"{BASE}/{entry['id']}", headers=_h(USER_B, TENANT_B))
        assert USER_A not in response.text

    @_gd7("GD7-05", "a tenant can append evidence under another tenant's source key (ledger contamination)")
    def test_another_tenant_cannot_contaminate_a_source(self):
        source = f"victim-{uuid.uuid4().hex[:8]}"
        _record(source_id=source)
        _record(user=USER_B, tenant=TENANT_B, source_id=source, evidence=["injected"])
        listed = client.get(BASE, headers=_h(USER_A, TENANT_A),
                            params={"source_type": "capa_suggestion", "source_id": source}).json()["entries"]
        assert all("injected" not in json.dumps(e) for e in listed)


class TestOwnershipClassificationDryRun:
    def _classify(self, entry_id: int) -> dict:
        db = SessionLocal()
        try:
            return {r["entry_id"]: r for r in ownership.classify_entries(db)}[entry_id]
        finally:
            db.close()

    def test_an_entry_with_a_verified_single_tenant_audit_trail_is_attributable(self):
        entry = _record()
        result = self._classify(entry["id"])
        assert result["classification"] == "attributable" and result["tenant_id"] == TENANT_A

    def test_an_entry_attributed_to_the_shared_default_tenant_is_quarantined(self):
        db = SessionLocal()
        try:
            row = EvidenceLedgerEntry(source_type="capa_suggestion", source_id=f"pooled-{RUN}", reviewer="x@example.com")
            db.add(row)
            db.commit()
            from app.services.enterprise_audit_service import record_enterprise_audit_event
            record_enterprise_audit_event(db, action_type="guardianx.evidence_recorded",
                                          resource_type=ownership.RESOURCE_TYPE, resource_id=str(row.id),
                                          actor="x@example.com", tenant_id="default-tenant", details={})
            entry_id = row.id
        finally:
            db.close()
        result = self._classify(entry_id)
        assert result["classification"] == "quarantine" and result["reason"] == "unattributed"

    def test_an_entry_with_no_audit_event_is_quarantined(self):
        db = SessionLocal()
        try:
            row = EvidenceLedgerEntry(source_type="capa_suggestion", source_id=f"orphan-{RUN}", reviewer="x@example.com")
            db.add(row)
            db.commit()
            entry_id = row.id
        finally:
            db.close()
        result = self._classify(entry_id)
        assert result["classification"] == "quarantine" and result["reason"] == "no_audit_event"

    def test_a_tampered_entry_is_quarantined_not_attributed(self):
        entry = _record()
        _sql("UPDATE guardianx_evidence_ledger_entries SET evidence_json = '[]' WHERE id = :i", i=entry["id"])
        result = self._classify(entry["id"])
        assert result["classification"] == "quarantine" and result["reason"] == "integrity_failure"

    def test_the_dry_run_writes_nothing(self):
        _record()
        db = SessionLocal()
        try:
            before = (db.query(EvidenceLedgerEntry).count(), db.query(AuditLog).count())
            ownership.classify_entries(db)
            db.rollback()
            after = (db.query(EvidenceLedgerEntry).count(), db.query(AuditLog).count())
        finally:
            db.close()
        assert before == after
