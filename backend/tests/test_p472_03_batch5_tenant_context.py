"""P472-03 Batch 5 — B5.1 frontend tenant contract (Issue #187).

The defect (reproduced before the fix)
--------------------------------------
Batch 4 made a client ``tenant_id`` a *claim* that must equal the caller's
verified tenant. The web client never learned its verified tenant: it sends no
tenant header and puts a hard-coded or locally stored tenant into requests
(``AccreditationConsole.tsx`` claims ``localStorage.tenant_id || "default-tenant"``
— nothing ever sets that key). For every real tenant the console's requests are
therefore refused with 403, and a multi-membership user has no way to select a
tenant at all, because no endpoint tells the client which tenants it may act in.

The contract (``docs/enterprise-readiness/p472-03-tenant-context-adr-v1.md``)
-----------------------------------------------------------------------------
* ``GET /api/auth/tenants`` returns the authenticated caller's ENABLED
  memberships, derived only from the server-side principal. It is read-only and
  reveals nothing about any other user or tenant.
* The client selects one of those tenants and sends it as ``X-Tenant-Id`` on
  every request; where a route still requires a ``tenant_id`` parameter it
  repeats the SAME value (a claim equal to the verified tenant — Batch 4 rule).
* The selection is advisory: the server re-verifies membership on every
  request. Forged, conflicting, stale (revoked) or absent selections are refused.

``TestReproduction`` shows the console's current requests are refused for a
real tenant and that no tenant-context endpoint existed (404 before the fix).
The remaining classes are the regression suite for the contract.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token

RUN = uuid.uuid4().hex[:8]
HOSP_A, HOSP_B, HOSP_C = f"b5-hosp-a-{RUN}", f"b5-hosp-b-{RUN}", f"b5-hosp-c-{RUN}"
SINGLE_A = f"b5-single-a-{RUN}@example.com"     # one membership: A
SINGLE_B = f"b5-single-b-{RUN}@example.com"     # one membership: B
MULTI_AC = f"b5-multi-ac-{RUN}@example.com"     # two memberships: A and C
NOBODY = f"b5-nobody-{RUN}@example.com"         # authenticated, no membership
MEMBERSHIPS = [(HOSP_A, SINGLE_A), (HOSP_B, SINGLE_B), (HOSP_A, MULTI_AC), (HOSP_C, MULTI_AC)]

FACILITY = "F1"
ACCREDITOR = "joint_commission"

client = TestClient(app, raise_server_exceptions=False)


def _bearer(user: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}"}


@pytest.fixture(scope="module", autouse=True)
def _users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user in (SINGLE_A, SINGLE_B, MULTI_AC, NOBODY):
            db.add(UserRoleAssignment(username=user, role="spd_manager", assigned_by="p472-03-batch5"))
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


def _disable(tenant: str, user: str) -> None:
    db = SessionLocal()
    try:
        row = db.query(models.TenantMembership).filter_by(tenant_id=tenant, user_email=user).one()
        row.is_enabled = False
        db.commit()
    finally:
        db.close()


# ── the console's requests, as the web client issues them ────────────────────

def _readiness(headers: dict, tenant_claim: str):
    return client.get("/api/accreditation/readiness", headers=headers,
                      params={"tenant_id": tenant_claim, "facility_id": FACILITY, "accreditor": ACCREDITOR})


def _evidence_items(headers: dict, tenant_claim: str):
    return client.get("/api/accreditation/evidence-items", headers=headers,
                      params={"tenant_id": tenant_claim, "facility_id": FACILITY, "accreditor": ACCREDITOR})


def _seed(headers: dict, tenant_claim: str):
    return client.post("/api/accreditation/evidence-items/seed", headers=headers,
                       json={"tenant_id": tenant_claim, "facility_id": FACILITY, "accreditor": ACCREDITOR})


def _session_tenants(user: str):
    return client.get("/api/auth/tenants", headers=_bearer(user))


def _client_selection(user: str, choose: str | None = None) -> str:
    """What the fixed client does: ask the server, then use the sole tenant or the user's choice."""
    response = _session_tenants(user)
    assert response.status_code == 200, response.text
    body = response.json()
    allowed = [m["tenant_id"] for m in body["memberships"]]
    if choose is not None:
        assert choose in allowed
        return choose
    assert body["active_tenant_id"] in allowed
    return body["active_tenant_id"]


def _selected(user: str, tenant: str) -> dict:
    return {**_bearer(user), "X-Tenant-Id": tenant}


class TestReproduction:
    """B5.1 reproduction: the console as shipped cannot work for a real tenant."""

    def test_the_console_default_claim_is_refused_for_a_real_tenant(self):
        # AccreditationConsole.tsx:63 — localStorage.tenant_id is never set, so it claims "default-tenant".
        for request in (_readiness, _evidence_items, _seed):
            response = request(_bearer(SINGLE_A), "default-tenant")
            assert response.status_code == 403, (request.__name__, response.status_code, response.text)

    def test_the_client_can_learn_its_verified_tenants_from_the_server(self):
        response = _session_tenants(SINGLE_A)
        assert response.status_code == 200, response.text
        assert response.json() == {
            "memberships": [{"tenant_id": HOSP_A, "role": "tenant_admin"}],
            "active_tenant_id": HOSP_A,
            "selection_required": False,
        }


class TestSessionTenantsEndpoint:
    def test_requires_authentication(self):
        assert client.get("/api/auth/tenants").status_code == 401
        assert client.get("/api/auth/tenants", headers={"Authorization": "Bearer forged.jwt.value"}).status_code == 401

    def test_multi_member_must_select(self):
        body = _session_tenants(MULTI_AC).json()
        assert sorted(m["tenant_id"] for m in body["memberships"]) == sorted([HOSP_A, HOSP_C])
        assert body["active_tenant_id"] is None
        assert body["selection_required"] is True

    def test_no_membership_lists_nothing_and_selects_nothing(self):
        assert _session_tenants(NOBODY).json() == {"memberships": [], "active_tenant_id": None,
                                                   "selection_required": False}

    def test_headers_cannot_inject_a_tenant_into_the_list(self):
        for header in ("X-Tenant-Id", "X-LumenAI-Tenant-Id"):
            body = client.get("/api/auth/tenants", headers={**_bearer(SINGLE_A), header: HOSP_B}).json()
            assert [m["tenant_id"] for m in body["memberships"]] == [HOSP_A]
            assert HOSP_B not in str(body)

    def test_a_revoked_membership_disappears(self):
        _disable(HOSP_C, MULTI_AC)
        body = _session_tenants(MULTI_AC).json()
        assert [m["tenant_id"] for m in body["memberships"]] == [HOSP_A]
        assert body["active_tenant_id"] == HOSP_A

    def test_reveals_no_other_users_memberships(self):
        body = _session_tenants(SINGLE_B).json()
        assert HOSP_A not in str(body) and HOSP_C not in str(body)


class TestSingleTenantWorkflow:
    def test_the_fixed_console_flow_is_served(self):
        tenant = _client_selection(SINGLE_A)
        headers = _selected(SINGLE_A, tenant)
        seeded = _seed(headers, tenant)
        assert seeded.status_code == 201, seeded.text
        assert _readiness(headers, tenant).status_code == 200
        listed = _evidence_items(headers, tenant)
        assert listed.status_code == 200
        assert listed.json()["evidence_items"], "seeded items are visible to their own tenant"

    def test_another_tenant_cannot_see_the_seeded_items(self):
        assert _seed(_selected(SINGLE_A, HOSP_A), HOSP_A).status_code == 201
        listed = _evidence_items(_selected(SINGLE_B, HOSP_B), HOSP_B)
        assert listed.status_code == 200
        assert listed.json()["evidence_items"] == []


class TestMultiTenantWorkflow:
    def test_each_selected_membership_is_served_and_kept_apart(self):
        for tenant in (HOSP_A, HOSP_C):
            selected = _client_selection(MULTI_AC, choose=tenant)
            assert _seed(_selected(MULTI_AC, selected), selected).status_code == 201
        a_items = _evidence_items(_selected(MULTI_AC, HOSP_A), HOSP_A).json()["evidence_items"]
        c_items = _evidence_items(_selected(MULTI_AC, HOSP_C), HOSP_C).json()["evidence_items"]
        assert a_items and c_items
        assert not {i["id"] for i in a_items} & {i["id"] for i in c_items}

    def test_no_selection_is_refused(self):
        # A multi-member client that has not selected a tenant must not be given one.
        response = client.get("/api/accreditation/readiness", headers=_bearer(MULTI_AC),
                              params={"facility_id": FACILITY, "accreditor": ACCREDITOR, "tenant_id": ""})
        assert response.status_code in (403, 422)


class TestRefusedSelections:
    @pytest.mark.parametrize("request_fn", [_readiness, _evidence_items, _seed])
    def test_forged_selection_of_a_tenant_the_user_is_not_in(self, request_fn):
        assert request_fn(_selected(SINGLE_A, HOSP_B), HOSP_B).status_code == 403

    @pytest.mark.parametrize("request_fn", [_readiness, _evidence_items, _seed])
    def test_conflicting_header_and_claim(self, request_fn):
        assert request_fn(_selected(MULTI_AC, HOSP_A), HOSP_C).status_code == 403

    def test_conflicting_headers(self):
        headers = {**_bearer(MULTI_AC), "X-Tenant-Id": HOSP_A, "X-LumenAI-Tenant-Id": HOSP_C}
        assert _readiness(headers, HOSP_A).status_code == 403

    @pytest.mark.parametrize("request_fn", [_readiness, _evidence_items, _seed])
    def test_stale_selection_after_revocation(self, request_fn):
        _disable(HOSP_C, MULTI_AC)
        assert request_fn(_selected(MULTI_AC, HOSP_C), HOSP_C).status_code == 403

    def test_no_membership_user_is_refused(self):
        assert _readiness(_bearer(NOBODY), "default-tenant").status_code == 403
        assert _readiness({**_bearer(NOBODY), "X-Tenant-Id": HOSP_A}, HOSP_A).status_code == 403
