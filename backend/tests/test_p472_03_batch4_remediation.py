"""P472-03 remediation batch 4 — residual cross-tenant authorization (Issue #186).

Each section below is one remediation group, committed on its own. Every test
was run against the code BEFORE its group's fix and reproduced the finding; the
assertions are unchanged after the fix.

AW-03 / AW-06M — handlers re-read an unverified tenant header
---------------------------------------------------------------
Thirteen modules authenticated with ``require_enterprise_auth(request)``, which
verifies the caller's tenant membership, then DISCARDED the verified context and
re-read the tenant themselves with ``get_request_tenant_id(request)``:

* ``X-LumenAI-Tenant-Id`` was used as-is although the auth layer never verified
  it (it only verified ``X-Tenant-Id``) — a member of A naming B read and wrote
  B's records (AW-03);
* with no header the handler fell back to a shared ``default-tenant`` — every
  verified member of every tenant was pooled into one bucket (AW-06M).

Fix: handlers take the tenant from the verified context
(``app.auth.tenant_scope.request_tenant``) and refuse a header naming any other
tenant; the auth layer treats either header as the explicit selection and fails
closed when the caller has no single verified tenant.

The route-wide adversarial coverage of every converted handler (8 attack
variants, owner and selected-membership happy paths, SQL-binding oracle) is in
``tests/test_p472_03_batch2_remediation.py``, which discovers converted
handlers from source. This file holds the stored-record evidence.
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.mobile import OfflineInspectionSession
from app.models.patient_safety import InstrumentQualitySignal
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token

RUN = uuid.uuid4().hex[:8]
TENANT_A, TENANT_B, TENANT_C = f"b4-alpha-{RUN}", f"b4-bravo-{RUN}", f"b4-charlie-{RUN}"
DEFAULT = "default-tenant"
MEMBER_A = f"b4-member-a-{RUN}@example.com"
MEMBER_B = f"b4-member-b-{RUN}@example.com"
MULTI_AC = f"b4-multi-ac-{RUN}@example.com"
OUTSIDER = f"b4-outsider-{RUN}@example.com"
MEMBERSHIPS = [(TENANT_A, MEMBER_A), (TENANT_B, MEMBER_B), (TENANT_A, MULTI_AC), (TENANT_C, MULTI_AC)]
REFUSED = (401, 403)

client = TestClient(app, raise_server_exceptions=False)


def _h(user: str, **headers: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}", **headers}


@pytest.fixture(scope="module", autouse=True)
def _users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user in (MEMBER_A, MEMBER_B, MULTI_AC, OUTSIDER):
            db.add(UserRoleAssignment(username=user, role="spd_manager", assigned_by="p472-03-batch4"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memberships(_users):
    """conftest clears ``tenant_memberships`` before every test; put ours back."""
    db = SessionLocal()
    try:
        for tenant, user in MEMBERSHIPS:
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role="tenant_admin", is_enabled=True))
        db.commit()
    finally:
        db.close()


# ══ AW-03 / AW-06M ════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def sessions(_users):
    """One offline inspection session in each of A, B, C and the legacy default bucket."""
    db = SessionLocal()
    try:
        made = {}
        for tenant in (TENANT_A, TENANT_B, TENANT_C, DEFAULT):
            row = OfflineInspectionSession(tenant_id=tenant, technician_id=f"tech-{tenant}",
                                           started_at_device=datetime.utcnow())
            db.add(row)
            db.flush()
            made[tenant] = row.session_id
        db.commit()
        return made
    finally:
        db.close()


def _listed(response) -> set[str]:
    assert response.status_code == 200, response.text
    return {item["session_id"] for item in response.json()["sessions"]}


class TestMobileSessionsAW03:
    """``/api/mobile`` (22 routes) — the largest AW-03 module."""

    def test_a_member_naming_another_tenant_in_the_lumenai_header_is_refused(self, sessions):
        response = client.get("/api/mobile/sessions", headers=_h(MEMBER_A, **{"X-LumenAI-Tenant-Id": TENANT_B}))
        assert response.status_code == 403
        assert sessions[TENANT_B] not in response.text

    def test_object_id_substitution_with_a_forged_header_is_refused(self, sessions):
        response = client.get(f"/api/mobile/sessions/{sessions[TENANT_B]}",
                              headers=_h(MEMBER_A, **{"X-LumenAI-Tenant-Id": TENANT_B}))
        assert response.status_code == 403
        assert TENANT_B not in response.text

    def test_object_id_substitution_without_a_header_finds_nothing(self, sessions):
        response = client.get(f"/api/mobile/sessions/{sessions[TENANT_B]}", headers=_h(MEMBER_A))
        assert response.status_code == 404

    @pytest.mark.parametrize("headers", [
        {"X-Tenant-Id": "A", "X-LumenAI-Tenant-Id": "B"},
        {"X-LumenAI-Tenant-Id": "A", "X-Tenant-Id": "B"},
    ], ids=["tenant-id A + lumenai B", "lumenai A + tenant-id B"])
    def test_conflicting_tenant_headers_are_refused(self, sessions, headers):
        named = {k: {"A": TENANT_A, "B": TENANT_B}[v] for k, v in headers.items()}
        response = client.get("/api/mobile/sessions", headers=_h(MEMBER_A, **named))
        assert response.status_code == 403
        assert sessions[TENANT_B] not in response.text

    def test_a_forged_header_cannot_write_into_another_tenant(self, sessions):
        response = client.post("/api/mobile/sessions", json={"technician_id": f"forged-{RUN}"},
                               headers=_h(MEMBER_A, **{"X-LumenAI-Tenant-Id": TENANT_B}))
        assert response.status_code == 403
        db = SessionLocal()
        try:
            assert db.query(OfflineInspectionSession).filter_by(technician_id=f"forged-{RUN}").count() == 0
        finally:
            db.close()

    def test_the_same_tenant_happy_path_is_preserved(self, sessions):
        for headers in ({}, {"X-LumenAI-Tenant-Id": TENANT_A}, {"X-Tenant-Id": TENANT_A}):
            assert _listed(client.get("/api/mobile/sessions", headers=_h(MEMBER_A, **headers))) == {sessions[TENANT_A]}
        response = client.get(f"/api/mobile/sessions/{sessions[TENANT_A]}", headers=_h(MEMBER_A))
        assert response.status_code == 200 and response.json()["tenant_id"] == TENANT_A


class TestMobileSessionsAW06M:
    def test_a_member_without_a_header_is_served_their_own_tenant_not_a_shared_pool(self, sessions):
        listed = _listed(client.get("/api/mobile/sessions", headers=_h(MEMBER_A)))
        assert sessions[DEFAULT] not in listed
        assert listed == {sessions[TENANT_A]}

    def test_members_of_different_tenants_are_not_pooled_together(self, sessions):
        a = _listed(client.get("/api/mobile/sessions", headers=_h(MEMBER_A)))
        b = _listed(client.get("/api/mobile/sessions", headers=_h(MEMBER_B)))
        assert a == {sessions[TENANT_A]} and b == {sessions[TENANT_B]}

    def test_a_write_without_a_header_is_attributed_to_the_verified_tenant(self, sessions):
        technician = f"attributed-{RUN}"
        response = client.post("/api/mobile/sessions", json={"technician_id": technician}, headers=_h(MEMBER_A))
        assert response.status_code == 200, response.text
        db = SessionLocal()
        try:
            assert [row.tenant_id for row in db.query(OfflineInspectionSession).filter_by(
                technician_id=technician)] == [TENANT_A]
        finally:
            db.close()

    def test_a_user_with_no_membership_is_refused_not_pooled(self, sessions):
        response = client.get("/api/mobile/sessions", headers=_h(OUTSIDER))
        assert response.status_code == 403
        assert sessions[DEFAULT] not in response.text


class TestSeveralMemberships:
    """The auth layer now treats either tenant header as the explicit selection."""

    def test_a_multi_member_must_select_a_tenant(self, sessions):
        assert client.get("/api/mobile/sessions", headers=_h(MULTI_AC)).status_code == 403

    @pytest.mark.parametrize("header", ["X-Tenant-Id", "X-LumenAI-Tenant-Id"])
    def test_a_multi_member_selects_one_of_their_tenants_with_either_header(self, sessions, header):
        assert _listed(client.get("/api/mobile/sessions", headers=_h(MULTI_AC, **{header: TENANT_C}))) == {
            sessions[TENANT_C]}

    @pytest.mark.parametrize("header", ["X-Tenant-Id", "X-LumenAI-Tenant-Id"])
    def test_a_multi_member_cannot_select_a_third_tenant(self, sessions, header):
        response = client.get("/api/mobile/sessions", headers=_h(MULTI_AC, **{header: TENANT_B}))
        assert response.status_code == 403
        assert sessions[TENANT_B] not in response.text


@pytest.fixture(scope="module")
def signals(_users):
    db = SessionLocal()
    try:
        made = {}
        for tenant in (TENANT_A, TENANT_B, DEFAULT):
            row = InstrumentQualitySignal(tenant_id=tenant, event_source="inspection", event_type=f"b4-{RUN}")
            db.add(row)
            db.flush()
            made[tenant] = row.signal_id
        db.commit()
        return made
    finally:
        db.close()


class TestPatientSafetySignalsAW03:
    """``/api/patient-safety`` — a module using the shared ``_tenant(request)`` helper."""

    def test_a_forged_lumenai_header_does_not_read_another_tenants_signals(self, signals):
        response = client.get("/api/patient-safety/signals", headers=_h(MEMBER_A, **{"X-LumenAI-Tenant-Id": TENANT_B}))
        assert response.status_code == 403
        assert signals[TENANT_B] not in response.text

    def test_a_member_without_a_header_sees_only_their_own_signals(self, signals):
        response = client.get("/api/patient-safety/signals", headers=_h(MEMBER_A))
        assert response.status_code == 200, response.text
        assert signals[TENANT_A] in response.text
        assert signals[TENANT_B] not in response.text and signals[DEFAULT] not in response.text


def test_no_route_handler_reads_the_tenant_header_itself():
    """The unverified re-read is gone from every route module, not just the swept routes."""
    import pathlib

    routes = pathlib.Path(__file__).resolve().parents[1] / "app" / "routes"
    offenders = sorted(p.name for p in routes.glob("*.py") if "get_request_tenant_id(" in p.read_text())
    assert offenders == []
