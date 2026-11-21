"""P472-03 Batch 8 — GuardianX explanation ownership (RB-T32 follow-through, GX-11..GX-14).

Reproduced at ``83dbf70`` on SQLite and PostgreSQL 16.15
(``scripts/p472_03_gx_explanation_repro.py``):

* tenant B read tenant A's explanations by list, by id, through the
  recommendation replay and through the audit-evidence package (RB-T32, in the
  Batch 7 file);
* B appended a human override to A's explanation by id: 200, persisted (GX-11);
* B's explanation written under A's ownerless key appeared in A's list (GX-12);
* explanation rows carried no owner and no audit event, so a legacy row was
  served to every tenant (GX-13);
* the generic replay verified the audit chain of any resource the caller named,
  without the GD-2 tenant scope (GX-14).

Tripwires RB-T34 GX-11, RB-T35 GX-12, RB-T36 GX-13, RB-T37 GX-14: each failed at 83dbf70 on
its own assertion (strict xfail, evidence/p472-03-batch8/explanations-before/) and was
converted with the assertion unchanged. Author conversions: release blockers until a
non-author disposition.

``TestControls`` — the owning tenant keeps full use of its explanations;
multi-membership, role, deleted-source, concurrent-write and replay consumers.
"""
from __future__ import annotations

import json
import threading
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.guardianx_assurance import AIExplainabilityRecord, EvidenceLedgerEntry
from app.models.inspection import Inspection
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token

RUN = uuid.uuid4().hex[:8]
TENANT_A, TENANT_B, TENANT_C = f"b8gx-a-{RUN}", f"b8gx-b-{RUN}", f"b8gx-c-{RUN}"
USER_A, USER_B = f"b8gx-a-{RUN}@example.test", f"b8gx-b-{RUN}@example.test"
USER_MULTI = f"b8gx-m-{RUN}@example.test"          # member of A and C
USER_VIEWER = f"b8gx-v-{RUN}@example.test"         # tenant A, least-privileged role
EXPLAIN = "/api/guardianx/explainability"
REPLAY = "/api/guardianx/audit-replay/recommendations"
PACKAGE = "/api/guardianx/reports/audit-evidence-package"

client = TestClient(app, raise_server_exceptions=False)


def _tripwire(finding: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding}: {summary}")


def _h(user: str, tenant: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}", "X-Tenant-Id": tenant}


@pytest.fixture(scope="module", autouse=True)
def _users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user in (USER_A, USER_B, USER_MULTI):
            db.add(UserRoleAssignment(username=user, role="admin", assigned_by="p472-03-batch8"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memberships(_users):
    db = SessionLocal()
    try:
        for user, tenant, role in ((USER_A, TENANT_A, "admin"), (USER_B, TENANT_B, "admin"),
                                   (USER_MULTI, TENANT_A, "admin"), (USER_MULTI, TENANT_C, "admin"),
                                   (USER_VIEWER, TENANT_A, "viewer")):
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role=role, is_enabled=True))
        db.commit()
    finally:
        db.close()


def _explain(user, tenant, source_type, source_id, summary):
    return client.post(EXPLAIN, headers=_h(user, tenant),
                       json={"source_type": source_type, "source_id": source_id, "input_summary": summary})


def _key() -> str:
    return f"capa-{uuid.uuid4().hex[:8]}"


def _inspection(tenant: str = TENANT_A) -> str:
    db = SessionLocal()
    try:
        row = Inspection(file_name=f"b8-{uuid.uuid4().hex[:6]}.png", tenant_id=tenant)
        db.add(row)
        db.commit()
        return str(row.id)
    finally:
        db.close()


def _row(record_id: int) -> AIExplainabilityRecord | None:
    db = SessionLocal()
    try:
        row = db.query(AIExplainabilityRecord).filter(AIExplainabilityRecord.id == record_id).first()
        if row is not None:
            db.expunge(row)
        return row
    finally:
        db.close()


def _legacy_row(summary: str, source_type: str = "capa_suggestion", source_id: str | None = None) -> int:
    """A row as written before Batch 8: no audit event, so no provable owner."""
    db = SessionLocal()
    try:
        row = AIExplainabilityRecord(source_type=source_type, source_id=source_id or _key(), input_summary=summary,
                                     created_by="legacy@example.test")
        db.add(row)
        db.commit()
        return row.id
    finally:
        db.close()


class TestOpenFindings:
    # GX-11 / RB-T34: strict tripwire, failed at 83dbf70; converted in Batch 8 (assertion unchanged).
    def test_another_tenant_cannot_override_an_explanation(self):
        created = _explain(USER_A, TENANT_A, "capa_suggestion", _key(), "a-own")
        assert created.status_code == 201
        record_id = created.json()["id"]
        response = client.post(f"{EXPLAIN}/{record_id}/human-override", headers=_h(USER_B, TENANT_B),
                               json={"override_note": "foreign"})
        assert response.status_code == 404
        assert json.loads(_row(record_id).human_overrides_json) == []

    # GX-12 / RB-T35: strict tripwire, failed at 83dbf70; converted in Batch 8 (assertion unchanged).
    def test_another_tenant_cannot_write_an_explanation_into_a_key_in_use(self):
        key = _key()
        assert _explain(USER_A, TENANT_A, "capa_suggestion", key, "a-own").status_code == 201
        response = _explain(USER_B, TENANT_B, "capa_suggestion", key, f"injected-{key}")
        assert response.status_code == 403
        listed = client.get(EXPLAIN, headers=_h(USER_A, TENANT_A),
                            params={"source_type": "capa_suggestion", "source_id": key})
        assert f"injected-{key}" not in listed.text

    # GX-13 / RB-T36: strict tripwire, failed at 83dbf70; converted in Batch 8 (assertion unchanged).
    def test_an_unattributable_explanation_is_served_to_no_tenant(self):
        marker = f"legacy-{uuid.uuid4().hex[:8]}"
        record_id = _legacy_row(marker)
        for user, tenant in ((USER_A, TENANT_A), (USER_B, TENANT_B)):
            assert marker not in client.get(f"{EXPLAIN}/{record_id}", headers=_h(user, tenant)).text

    # GX-14 / RB-T37: strict tripwire, failed at 83dbf70; converted in Batch 8 (assertion unchanged).
    def test_replay_does_not_report_another_tenants_audit_chain(self):
        written = client.post("/api/guardianx/evidence", headers=_h(USER_A, TENANT_A),
                              json={"source_type": "capa_suggestion", "source_id": _key(), "evidence": ["e"]})
        assert written.status_code == 201
        params = {"source_type": "guardianx_evidence_ledger_entry", "source_id": str(written.json()["id"])}
        response = client.get(REPLAY, headers=_h(USER_B, TENANT_B), params=params)
        assert response.status_code in (200, 403)
        if response.status_code == 200:
            assert response.json()["audit_chain"]["event_count"] == 0


class TestControls:
    def test_owner_lists_reads_and_overrides_its_explanation(self):
        key = _key()
        created = _explain(USER_A, TENANT_A, "capa_suggestion", key, f"own-{key}")
        record_id = created.json()["id"]
        listed = client.get(EXPLAIN, headers=_h(USER_A, TENANT_A),
                            params={"source_type": "capa_suggestion", "source_id": key}).json()["explanations"]
        assert [e["id"] for e in listed] == [record_id]
        assert client.get(f"{EXPLAIN}/{record_id}", headers=_h(USER_A, TENANT_A)).status_code == 200
        override = client.post(f"{EXPLAIN}/{record_id}/human-override", headers=_h(USER_A, TENANT_A),
                               json={"override_note": "reviewed"})
        assert override.status_code == 200
        assert override.json()["human_overrides"][0]["overridden_by"] == USER_A

    def test_owner_can_add_several_explanations_to_its_own_key(self):
        key = _key()
        for n in range(2):
            assert _explain(USER_A, TENANT_A, "capa_suggestion", key, f"own-{n}").status_code == 201
        listed = client.get(EXPLAIN, headers=_h(USER_A, TENANT_A),
                            params={"source_type": "capa_suggestion", "source_id": key}).json()["explanations"]
        assert len(listed) == 2

    def test_owner_sees_its_inspection_explanation_in_replay_and_package(self):
        source = _inspection(TENANT_A)
        assert _explain(USER_A, TENANT_A, "inspection", source, f"insp-{source}").status_code == 201
        replay = client.get(f"/api/guardianx/audit-replay/inspections/{source}", headers=_h(USER_A, TENANT_A))
        assert replay.status_code == 200 and f"insp-{source}" in replay.text
        key = _key()
        assert _explain(USER_A, TENANT_A, "capa_suggestion", key, f"pkg-{key}").status_code == 201
        params = {"source_type": "capa_suggestion", "source_id": key}
        for path in (REPLAY, PACKAGE):
            response = client.get(path, headers=_h(USER_A, TENANT_A), params=params)
            assert response.status_code == 200 and f"pkg-{key}" in response.text, path

    def test_owner_replay_reports_its_own_audit_chain(self):
        written = client.post("/api/guardianx/evidence", headers=_h(USER_A, TENANT_A),
                              json={"source_type": "capa_suggestion", "source_id": _key(), "evidence": ["e"]})
        params = {"source_type": "guardianx_evidence_ledger_entry", "source_id": str(written.json()["id"])}
        response = client.get(REPLAY, headers=_h(USER_A, TENANT_A), params=params)
        assert response.status_code == 200 and response.json()["audit_chain"]["event_count"] == 1

    def test_a_least_privileged_member_of_the_owner_reads_it(self):
        key = _key()
        record_id = _explain(USER_A, TENANT_A, "capa_suggestion", key, f"v-{key}").json()["id"]
        response = client.get(f"{EXPLAIN}/{record_id}", headers=_h(USER_VIEWER, TENANT_A))
        assert response.status_code == 200

    def test_explanation_for_a_deleted_source_is_refused(self):
        source = _inspection(TENANT_A)
        db = SessionLocal()
        try:
            db.query(Inspection).filter(Inspection.id == int(source)).delete()
            db.commit()
        finally:
            db.close()
        assert _explain(USER_A, TENANT_A, "inspection", source, "stale").status_code == 404

    def test_unauthenticated_explanation_reads_are_refused(self):
        assert client.get(f"{EXPLAIN}/1").status_code in (401, 403)
        assert client.get(EXPLAIN, params={"source_type": "capa_suggestion", "source_id": "x"}).status_code in (401, 403)


class TestNegative:
    """New with Batch 8 (not tripwires). Each FAILED on 83dbf70 for the defect it names
    (multi-member read of A while selecting C: 200; concurrent writer read the other
    tenant's explanation; ledger write into a key holding A's explanation: 201)."""

    def test_multi_member_sees_an_explanation_only_while_selecting_its_tenant(self):
        key = _key()
        created = _explain(USER_A, TENANT_A, "capa_suggestion", key, f"m-{key}")
        record_id = created.json()["id"]
        assert client.get(f"{EXPLAIN}/{record_id}", headers=_h(USER_MULTI, TENANT_A)).status_code == 200
        assert client.get(f"{EXPLAIN}/{record_id}", headers=_h(USER_MULTI, TENANT_C)).status_code == 404

    def test_concurrent_first_writes_to_a_fresh_key_never_disclose_across_tenants(self):
        key = _key()
        results: dict = {}

        def write(user, tenant):
            results[tenant] = _explain(user, tenant, "capa_suggestion", key, f"{tenant}-{key}").status_code

        threads = [threading.Thread(target=write, args=pair) for pair in ((USER_A, TENANT_A), (USER_B, TENANT_B))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(results.values()) in ([201, 201], [201, 403])
        params = {"source_type": "capa_suggestion", "source_id": key}
        a = client.get(EXPLAIN, headers=_h(USER_A, TENANT_A), params=params).text
        b = client.get(EXPLAIN, headers=_h(USER_B, TENANT_B), params=params).text
        assert f"{TENANT_B}-{key}" not in a and f"{TENANT_A}-{key}" not in b

    def test_a_ledger_write_into_a_key_holding_another_tenants_explanation_is_refused(self):
        key = _key()
        assert _explain(USER_A, TENANT_A, "capa_suggestion", key, "a").status_code == 201
        response = client.post("/api/guardianx/evidence", headers=_h(USER_B, TENANT_B),
                               json={"source_type": "capa_suggestion", "source_id": key, "evidence": ["x"]})
        assert response.status_code == 403
        db = SessionLocal()
        try:
            assert db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.source_id == key).count() == 0
        finally:
            db.close()

    def test_refused_explanation_writes_persist_nothing(self):
        from app.models.audit_log import AuditLog

        def counts():
            db = SessionLocal()
            try:
                rows = db.query(AIExplainabilityRecord).filter(AIExplainabilityRecord.created_by == USER_B).count()
                events = (db.query(AuditLog).filter(AuditLog.resource_type == "guardianx_explainability_record",
                                                    AuditLog.tenant_id == TENANT_B).count())
                return rows, events
            finally:
                db.close()

        key = _key()
        created = _explain(USER_A, TENANT_A, "capa_suggestion", key, "a-own").json()["id"]
        foreign_inspection = _inspection(TENANT_A)
        before = counts()
        assert _explain(USER_B, TENANT_B, "capa_suggestion", key, "b").status_code == 403
        assert _explain(USER_B, TENANT_B, "inspection", foreign_inspection, "b").status_code == 404
        assert client.post(f"{EXPLAIN}/{created}/human-override", headers=_h(USER_B, TENANT_B),
                           json={"override_note": "b"}).status_code == 404
        assert counts() == before
        assert json.loads(_row(created).human_overrides_json) == []
