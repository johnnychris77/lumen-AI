"""P472-03 Batch 7 — GuardianX source-object write authorization (GD7-05 follow-up).

RB-T28 (``test_another_tenant_cannot_contaminate_a_source``) passes because the
victim's *reads* are filtered by the B6.2 read gate. It never asserted that the
foreign *write* is refused. Reproduced at ``4667ab8``: tenant B's POST /evidence
under tenant A's inspection returned 201 and the row persisted; an explanation
written by B under A's inspection appeared in A's audit replay.

Tripwires (strict, release blockers until a non-author disposition):

* RB-T29 GD7-06 — ledger write under another tenant's owned source (inspection,
  workflow execution) or a non-existent one must be refused.
* RB-T30 GD7-07 — ledger write into an ownerless source key (e.g.
  ``capa_suggestion``) already used by another tenant, or by an unprovable
  owner, must be refused.
* RB-T31 GX-08 — explanation write under another tenant's owned source must be
  refused (it surfaced in the victim's audit replay).
* RB-T32 GX-09 — explainability records must not be disclosed cross-tenant
  (list, replay, audit-evidence package). **OPEN**: records have no owner
  column and no audit trail; ownership semantics depend on GD-7.
* RB-T33 GX-10 — ``tenant_id_for_digital_twin`` is a tenant claim; naming
  another tenant must be refused (AW-04 rule).

``TestControls`` — legitimate same-tenant writes keep working.
"""
from __future__ import annotations

import json
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
from app.models.workflow_forge import WorkflowDefinition, WorkflowExecution
from app.routers.auth_simple import _make_token

RUN = uuid.uuid4().hex[:8]
TENANT_A, TENANT_B = f"b7gx-a-{RUN}", f"b7gx-b-{RUN}"
USER_A, USER_B = f"b7gx-a-{RUN}@example.test", f"b7gx-b-{RUN}@example.test"
EVIDENCE = "/api/guardianx/evidence"
EXPLAIN = "/api/guardianx/explainability"

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
        for user in (USER_A, USER_B):
            db.add(UserRoleAssignment(username=user, role="admin", assigned_by="p472-03-batch7"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memberships(_users):
    # The shared conftest resets tenant memberships between tests (as in the GD-7 file).
    db = SessionLocal()
    try:
        for user, tenant in ((USER_A, TENANT_A), (USER_B, TENANT_B)):
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="admin", is_enabled=True))
        db.commit()
    finally:
        db.close()


def _inspection(tenant: str = TENANT_A) -> str:
    db = SessionLocal()
    try:
        row = Inspection(file_name=f"b7-{uuid.uuid4().hex[:6]}.png", tenant_id=tenant)
        db.add(row)
        db.commit()
        return str(row.id)
    finally:
        db.close()


def _execution(tenant: str = TENANT_A) -> str:
    db = SessionLocal()
    try:
        wf = WorkflowDefinition(workflow_ref=f"b7-wf-{uuid.uuid4().hex[:8]}", name="b7")
        db.add(wf)
        db.commit()
        db.refresh(wf)
        row = WorkflowExecution(workflow_id=wf.id, tenant_id=tenant)
        db.add(row)
        db.commit()
        return str(row.id)
    finally:
        db.close()


def _write(user, tenant, source_type, source_id, evidence=("e",)):
    return client.post(EVIDENCE, headers=_h(user, tenant),
                       json={"source_type": source_type, "source_id": source_id, "evidence": list(evidence)})


def _ledger_rows(source_type: str, source_id: str) -> list[dict]:
    db = SessionLocal()
    try:
        rows = db.query(EvidenceLedgerEntry).filter(EvidenceLedgerEntry.source_type == source_type,
                                                    EvidenceLedgerEntry.source_id == source_id).all()
        return [{"evidence": json.loads(r.evidence_json), "reviewer": r.reviewer} for r in rows]
    finally:
        db.close()


def _explanations(source_type: str, source_id: str) -> list[str]:
    db = SessionLocal()
    try:
        return [r.created_by for r in db.query(AIExplainabilityRecord).filter(
            AIExplainabilityRecord.source_type == source_type, AIExplainabilityRecord.source_id == source_id)]
    finally:
        db.close()


class TestOpenFindings:
    # GD7-06 / RB-T29: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_another_tenant_cannot_write_evidence_under_an_owned_inspection(self):
        source = _inspection(TENANT_A)
        response = _write(USER_B, TENANT_B, "inspection", source, evidence=["injected"])
        assert response.status_code == 404
        assert all(USER_B != r["reviewer"] for r in _ledger_rows("inspection", source))

    # GD7-06 / RB-T29: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_another_tenant_cannot_write_evidence_under_an_owned_workflow_execution(self):
        source = _execution(TENANT_A)
        response = _write(USER_B, TENANT_B, "workflow_execution", source)
        assert response.status_code == 404
        assert _ledger_rows("workflow_execution", source) == []

    # GD7-06 / RB-T29: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_evidence_for_a_missing_owned_source_is_refused_like_a_foreign_one(self):
        response = _write(USER_B, TENANT_B, "inspection", "987654321")
        assert response.status_code == 404
        assert _ledger_rows("inspection", "987654321") == []

    # GD7-07 / RB-T30: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_another_tenant_cannot_write_into_an_ownerless_key_in_use(self):
        key = f"capa-{uuid.uuid4().hex[:8]}"
        assert _write(USER_A, TENANT_A, "capa_suggestion", key).status_code == 201
        response = _write(USER_B, TENANT_B, "capa_suggestion", key, evidence=["injected"])
        assert response.status_code == 403
        assert [r["reviewer"] for r in _ledger_rows("capa_suggestion", key)] == [USER_A]

    # GX-08 / RB-T31: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_another_tenant_cannot_attach_an_explanation_to_an_owned_inspection(self):
        source = _inspection(TENANT_A)
        response = client.post(EXPLAIN, headers=_h(USER_B, TENANT_B),
                               json={"source_type": "inspection", "source_id": source, "input_summary": "injected"})
        assert response.status_code == 404
        assert USER_B not in _explanations("inspection", source)

    @_tripwire("GX-09 / RB-T32", "explainability records are listed, replayed and packaged cross-tenant "
                                 "(no owner column, no audit trail; pending GD-7)")
    def test_explanations_are_not_disclosed_to_another_tenant(self):
        key = f"capa-{uuid.uuid4().hex[:8]}"
        created = client.post(EXPLAIN, headers=_h(USER_A, TENANT_A),
                              json={"source_type": "capa_suggestion", "source_id": key,
                                    "input_summary": f"private-{key}"})
        assert created.status_code == 201
        params = {"source_type": "capa_suggestion", "source_id": key}
        for path in (EXPLAIN, "/api/guardianx/audit-replay/recommendations",
                     "/api/guardianx/reports/audit-evidence-package"):
            response = client.get(path, headers=_h(USER_B, TENANT_B), params=params)
            assert f"private-{key}" not in response.text, path
        by_id = client.get(f"{EXPLAIN}/{created.json()['id']}", headers=_h(USER_B, TENANT_B))
        assert f"private-{key}" not in by_id.text

    # GX-10 / RB-T33: strict tripwire reproduced at 4667ab8; converted in Batch 7 (assertion unchanged).
    def test_digital_twin_context_cannot_name_another_tenant(self):
        response = client.post(EXPLAIN, headers=_h(USER_B, TENANT_B),
                               json={"source_type": "capa_suggestion", "source_id": f"dt-{uuid.uuid4().hex[:6]}",
                                     "tenant_id_for_digital_twin": TENANT_A})
        assert response.status_code == 403


class TestControls:
    def test_owner_writes_evidence_for_its_inspection(self):
        source = _inspection(TENANT_A)
        assert _write(USER_A, TENANT_A, "inspection", source).status_code == 201
        listed = client.get(EVIDENCE, headers=_h(USER_A, TENANT_A),
                            params={"source_type": "inspection", "source_id": source}).json()["entries"]
        assert len(listed) == 1

    def test_owner_writes_evidence_for_its_workflow_execution(self):
        source = _execution(TENANT_A)
        assert _write(USER_A, TENANT_A, "workflow_execution", source).status_code == 201

    def test_owner_can_write_repeatedly_to_its_own_ownerless_key(self):
        key = f"capa-{uuid.uuid4().hex[:8]}"
        assert _write(USER_A, TENANT_A, "capa_suggestion", key).status_code == 201
        assert _write(USER_A, TENANT_A, "capa_suggestion", key).status_code == 201
        assert len(_ledger_rows("capa_suggestion", key)) == 2

    def test_a_fresh_ownerless_key_is_writable(self):
        assert _write(USER_B, TENANT_B, "rca_suggestion", f"rca-{uuid.uuid4().hex[:8]}").status_code == 201

    def test_owner_attaches_an_explanation_to_its_inspection(self):
        source = _inspection(TENANT_A)
        response = client.post(EXPLAIN, headers=_h(USER_A, TENANT_A),
                               json={"source_type": "inspection", "source_id": source, "input_summary": "own"})
        assert response.status_code == 201

    def test_digital_twin_context_for_the_callers_own_tenant_still_works(self):
        response = client.post(EXPLAIN, headers=_h(USER_A, TENANT_A),
                               json={"source_type": "capa_suggestion", "source_id": f"dt-{uuid.uuid4().hex[:6]}",
                                     "tenant_id_for_digital_twin": TENANT_A})
        assert response.status_code == 201
        assert response.json()["digital_twin_context"]

    def test_unauthenticated_writes_are_refused(self):
        response = client.post(EVIDENCE, json={"source_type": "inspection", "source_id": "1", "evidence": []})
        assert response.status_code in (401, 403)
