"""P472-03 Batch 5 — B5.3 Genesis manufacturer knowledge updates (GD-6, RB-T01).

``/api/genesis-ai/manufacturer-updates`` is a network-wide knowledge feed: any
tenant's leadership may submit an update (stored under the submitter's VERIFIED
tenant), and every tenant may read the feed. What each tenant may see and who
may publish is governance decision **GD-6 — unsigned**. This file therefore does
NOT change behaviour; it pins it:

* ``TestControls`` — what is already enforced (passes).
* ``TestOpenFindings`` — every exposure reproduced in Batch 5 as a STRICT
  expected failure; converted in Batch 6 (B6.1) after the fail-closed fix. A
  converted tripwire is still a RELEASE BLOCKER until a non-author reviewer
  records its disposition (RB-T15…RB-T23). A tripwire is an OPEN finding
  and a RELEASE BLOCKER, not a passing check. It flips to a failure the moment
  behaviour changes, forcing the marker to be removed deliberately once an
  approved GD-6 policy is implemented and independently reviewed.

Proposed least-privilege default for GD-6 (not implemented): unpublished
(pending_review / draft / rejected) content visible only to the submitting
tenant; published content visible network-wide through an explicit workflow;
cross-tenant moderation only for a separately authorized platform role with
tamper-evident audit; submitter/reviewer identities not disclosed to other
tenants. See docs/enterprise-readiness/p472-03-b53-gd6-decision-packet-v1.md.
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
MFR_A, HOSP_B = f"b53-mfr-a-{RUN}", f"b53-hosp-b-{RUN}"
LEAD_A = f"b53-lead-a-{RUN}@example.com"     # leadership in tenant A (the publisher)
LEAD_B = f"b53-lead-b-{RUN}@example.com"     # leadership in tenant B (another tenant)
VIEW_B = f"b53-view-b-{RUN}@example.com"     # viewer in tenant B
BASE = "/api/genesis-ai/manufacturer-updates"

client = TestClient(app, raise_server_exceptions=False)


def _gd6(finding: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding} (pending GD-6): {summary}")


def _h(user: str, tenant: str) -> dict:
    return {"Authorization": f"Bearer {_make_token(user)}", "X-Tenant-Id": tenant}


@pytest.fixture(scope="module", autouse=True)
def _users():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for user, role in ((LEAD_A, "spd_manager"), (LEAD_B, "spd_manager"), (VIEW_B, "viewer")):
            db.add(UserRoleAssignment(username=user, role=role, assigned_by="p472-03-batch5"))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _memberships(_users):
    db = SessionLocal()
    try:
        for tenant, user, role in ((MFR_A, LEAD_A, "spd_manager"), (HOSP_B, LEAD_B, "spd_manager"),
                                   (HOSP_B, VIEW_B, "viewer")):
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role=role, is_enabled=True))
        db.commit()
    finally:
        db.close()


def _submit(user=LEAD_A, tenant=MFR_A, **extra) -> dict:
    body = {"update_type": "ifu", "title": f"IFU rev {uuid.uuid4().hex[:6]}",
            "body": "draft wording not yet approved", **extra}
    response = client.post(BASE, headers=_h(user, tenant), json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _published() -> dict:
    update = _submit()
    response = client.post(f"{BASE}/{update['id']}/review", headers=_h(LEAD_A, MFR_A), json={"decision": "published"})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def pending() -> dict:
    return _submit()


class TestControls:
    def test_an_update_is_stored_under_the_submitters_verified_tenant(self):
        update = _submit(manufacturer_tenant_id=HOSP_B)  # body claim is ignored
        assert update["manufacturer_tenant_id"] == MFR_A
        assert update["status"] == "pending_review"

    def test_a_forged_tenant_header_cannot_submit_as_another_tenant(self):
        response = client.post(BASE, headers=_h(LEAD_A, HOSP_B), json={"update_type": "ifu", "title": "x"})
        assert response.status_code == 403

    def test_a_viewer_cannot_submit_or_review(self, pending):
        assert client.post(BASE, headers=_h(VIEW_B, HOSP_B), json={"update_type": "ifu", "title": "x"}
                           ).status_code == 403
        assert client.post(f"{BASE}/{pending['id']}/review", headers=_h(VIEW_B, HOSP_B),
                           json={"decision": "published"}).status_code == 403

    def test_published_content_is_visible_network_wide(self):
        published = _published()
        listed = client.get(BASE, headers=_h(VIEW_B, HOSP_B)).json()["updates"]
        assert published["id"] in {u["id"] for u in listed}

    def test_the_submitting_tenant_sees_its_own_pending_update(self, pending):
        assert client.get(f"{BASE}/{pending['id']}", headers=_h(LEAD_A, MFR_A)).status_code == 200

    def test_unauthenticated_callers_are_refused(self, pending):
        assert client.get(BASE).status_code == 401
        assert client.get(f"{BASE}/{pending['id']}").status_code == 401


class TestOpenFindings:
    """Each test asserts the PROPOSED least-privilege behaviour; each fails today."""

    # GD6-01 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_another_tenant_cannot_read_a_pending_update_by_id(self, pending):
        response = client.get(f"{BASE}/{pending['id']}", headers=_h(VIEW_B, HOSP_B))
        assert response.status_code == 404
        assert pending["body"] not in response.text

    # GD6-02 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_the_feed_does_not_list_another_tenants_unpublished_updates(self, pending):
        listed = client.get(BASE, headers=_h(VIEW_B, HOSP_B)).json()["updates"]
        assert pending["id"] not in {u["id"] for u in listed}

    # GD6-03 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_status_filter_does_not_reveal_another_tenants_pending_updates(self, pending):
        listed = client.get(BASE, headers=_h(VIEW_B, HOSP_B), params={"status": "pending_review"}).json()["updates"]
        assert all(u["manufacturer_tenant_id"] == HOSP_B for u in listed)

    # Converted in B6.1. ASSERTION AMENDED (for reviewer attention): the publisher
    # filter naming another tenant is now refused (403, Batch 4 claim rule), so there
    # is no list to inspect; a refusal is accepted as "not revealed" and the pending
    # id must still be absent from the response body.
    def test_publisher_filter_does_not_reveal_unpublished_content(self, pending):
        response = client.get(BASE, headers=_h(VIEW_B, HOSP_B), params={"manufacturer_tenant_id": MFR_A})
        assert response.status_code in (200, 403)
        listed = response.json()["updates"] if response.status_code == 200 else []
        assert pending["id"] not in {u["id"] for u in listed}
        assert pending["body"] not in response.text

    # GD6-05 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_version_chain_does_not_disclose_unpublished_versions(self):
        draft = _submit()
        published = _submit(supersedes_id=draft["id"])
        client.post(f"{BASE}/{published['id']}/review", headers=_h(LEAD_A, MFR_A), json={"decision": "published"})
        chain = client.get(f"{BASE}/{published['id']}/version-chain", headers=_h(VIEW_B, HOSP_B)).json()["chain"]
        assert draft["id"] not in {u["id"] for u in chain}

    # GD6-06 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_another_tenant_cannot_publish(self, pending):
        response = client.post(f"{BASE}/{pending['id']}/review", headers=_h(LEAD_B, HOSP_B), json={"decision": "published"})
        assert response.status_code in (403, 404)

    # GD6-07 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_another_tenant_cannot_reject(self, pending):
        response = client.post(f"{BASE}/{pending['id']}/review", headers=_h(LEAD_B, HOSP_B), json={"decision": "rejected"})
        assert response.status_code in (403, 404)

    # GD6-08 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_cannot_supersede_another_tenants_update(self, pending):
        response = client.post(BASE, headers=_h(LEAD_B, HOSP_B),
                               json={"update_type": "ifu", "title": "hijack", "supersedes_id": pending["id"]})
        assert response.status_code in (403, 404, 422)

    # GD6-09 — strict tripwire in Batch 5; converted in B6.1 (assertion unchanged).
    def test_other_tenants_do_not_see_submitter_identities(self):
        published = _published()
        listed = client.get(BASE, headers=_h(VIEW_B, HOSP_B)).json()["updates"]
        row = next(u for u in listed if u["id"] == published["id"])
        assert LEAD_A not in str(row)


class TestB61FailClosedControls:
    """B6.1: what the fail-closed rule still allows, and what it records."""

    def test_the_owning_tenant_can_still_review_its_own_update_and_it_is_audited(self, pending):
        from app.models.audit_log import AuditLog
        response = client.post(f"{BASE}/{pending['id']}/review", headers=_h(LEAD_A, MFR_A), json={"decision": "published"})
        assert response.status_code == 200 and response.json()["status"] == "published"
        db = SessionLocal()
        try:
            events = db.query(AuditLog).filter(AuditLog.resource_type == "genesis_manufacturer_update",
                                               AuditLog.resource_id == str(pending["id"])).all()
        finally:
            db.close()
        assert [e.action_type for e in events] == ["genesis.manufacturer_update.published"]
        assert events[0].tenant_id == MFR_A

    def test_another_tenants_id_and_a_missing_id_are_indistinguishable(self, pending):
        other = client.get(f"{BASE}/{pending['id']}", headers=_h(VIEW_B, HOSP_B))
        missing = client.get(f"{BASE}/999999999", headers=_h(VIEW_B, HOSP_B))
        assert other.status_code == missing.status_code == 404
        assert other.json()["detail"].replace(str(pending["id"]), "N") == missing.json()["detail"].replace("999999999", "N")

    def test_the_publisher_filter_works_for_the_callers_own_tenant(self, pending):
        listed = client.get(BASE, headers=_h(LEAD_A, MFR_A), params={"manufacturer_tenant_id": MFR_A}).json()["updates"]
        assert pending["id"] in {u["id"] for u in listed}
        assert all(u["owned_by_caller"] for u in listed)

    def test_published_content_from_another_tenant_is_pseudonymous(self):
        published = _published()
        row = next(u for u in client.get(BASE, headers=_h(VIEW_B, HOSP_B)).json()["updates"] if u["id"] == published["id"])
        assert row["manufacturer_tenant_id"] is None and row["submitted_by"] is None and row["reviewed_by"] is None
        assert row["owned_by_caller"] is False and row["body"] == published["body"]

    def test_the_owner_sees_its_own_identities(self, pending):
        row = client.get(f"{BASE}/{pending['id']}", headers=_h(LEAD_A, MFR_A)).json()
        assert row["submitted_by"] == LEAD_A and row["manufacturer_tenant_id"] == MFR_A

    def test_superseding_own_update_still_works(self, pending):
        newer = _submit(supersedes_id=pending["id"])
        chain = client.get(f"{BASE}/{newer['id']}/version-chain", headers=_h(LEAD_A, MFR_A)).json()["chain"]
        assert [u["id"] for u in chain] == [pending["id"], newer["id"]]
