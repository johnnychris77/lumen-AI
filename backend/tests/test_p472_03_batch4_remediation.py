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


# ══ AW-04 — a tenant named in the query, path or body ═════════════════════════
#
# A ``tenant_id`` the client sends is only a CLAIM: it must name the caller's
# verified tenant or be absent. It is never a selector and is never rewritten.
# Every route registered for AW-04 at baseline 4fdac4c (the six accreditation
# routes were fixed in batch 3 and are kept here as regression coverage):

import signal  # noqa: E402

from sqlalchemy import event  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from tenant_isolation_sweep_runner import _Plan, _scope_hits, _Spec, _tables_touched  # noqa: E402

AW04_ROUTES = [
    "GET /api/accreditation/certifications", "GET /api/accreditation/evidence-items",
    "GET /api/accreditation/programs", "GET /api/accreditation/readiness",
    "GET /api/accreditation/readiness/trend", "GET /api/accreditation/survey-evidence",
    "GET /api/billing/status",
    "GET /api/commercial/business-case/executive-summary", "GET /api/commercial/customer-success/health-score",
    "POST /api/commercial/customer-success/snapshot", "GET /api/commercial/customer-success/trend",
    "POST /api/enterprise/ranking/composite-score", "GET /api/enterprise/ranking/kpi-summary",
    "POST /api/enterprise/ranking/profiles", "GET /api/enterprise/ranking/profiles/{tenant_id}",
    "POST /api/enterprise/ranking/score",
    "PATCH /api/genesis-ai/participants/{tenant_id}/research-opt-in",
    "POST /api/growth/reference-customers",
    "GET /api/infinity/billing/partner-licenses",
    "GET /api/intelligence/capa-effectiveness", "POST /api/intelligence/consent",
    "GET /api/intelligence/dashboard", "GET /api/intelligence/recalls", "GET /api/intelligence/recalls/{recall_id}",
    "GET /api/network-intelligence/executive/dashboards", "POST /api/network-intelligence/executive/dashboards",
    "GET /api/network-intelligence/executive/network-intelligence-summary",
    "GET /api/network-intelligence/executive/snapshots", "POST /api/network-intelligence/executive/snapshots",
    "GET /api/network-intelligence/lifecycle/events", "GET /api/network-intelligence/lifecycle/instruments",
    "POST /api/network-intelligence/lifecycle/instruments",
    "GET /api/network-intelligence/registry", "POST /api/network-intelligence/registry",
    "POST /api/olympus/trust/{tenant_id}/compute", "GET /api/olympus/participants/{tenant_id}",
    "GET /api/olympus/trust/{tenant_id}/history",
]
# The publisher filter of the network knowledge feed names a MANUFACTURER, not the
# caller's tenant; see the batch 4 review (triaged separately, still registered).
AW04_NOT_A_CALLER_CLAIM = {"GET /api/genesis-ai/manufacturer-updates"}
# Tenant-membership roles each test identity holds in turn, with the global role the
# route may require (the platform administrator, global role "admin", is excluded).
AW04_PROFILES = [("spd_manager", "spd_manager"), ("spd_manager", "tenant_admin"), ("executive", "admin"),
                 ("executive", "tenant_admin"), ("manager", "tenant_admin"), ("operator", "operator"),
                 ("viewer", "viewer")]
AW04_OWNERS = {i: f"b4-aw04-a-{i}-{RUN}@example.com" for i in range(len(AW04_PROFILES))}
AW04_MULTI = {i: f"b4-aw04-ac-{i}-{RUN}@example.com" for i in range(len(AW04_PROFILES))}
for _i, (_global, _tenant_role) in enumerate(AW04_PROFILES):
    MEMBERSHIPS.append((TENANT_A, AW04_OWNERS[_i]))
    MEMBERSHIPS.extend([(TENANT_A, AW04_MULTI[_i]), (TENANT_C, AW04_MULTI[_i])])
_AW04_TENANT_ROLE = {**{AW04_OWNERS[i]: r for i, (_, r) in enumerate(AW04_PROFILES)},
                     **{AW04_MULTI[i]: r for i, (_, r) in enumerate(AW04_PROFILES)}}


@pytest.fixture(scope="module")
def aw04_world(_users):
    db = SessionLocal()
    try:
        for index, (global_role, _) in enumerate(AW04_PROFILES):
            for user in (AW04_OWNERS[index], AW04_MULTI[index]):
                db.add(UserRoleAssignment(username=user, role=global_role, assigned_by="p472-03-batch4"))
        db.query(models.TenantMembership).filter(
            models.TenantMembership.user_email.in_(list(_AW04_TENANT_ROLE))).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _aw04_roles(_memberships):
    """The shared membership fixture adds ``tenant_admin`` rows; give AW-04 identities their role."""
    db = SessionLocal()
    try:
        for row in db.query(models.TenantMembership).filter(
                models.TenantMembership.user_email.in_(list(_AW04_TENANT_ROLE))):
            row.role = _AW04_TENANT_ROLE[row.user_email]
        db.commit()
    finally:
        db.close()


class _Aw04Caller:
    def __init__(self) -> None:
        self.client = TestClient(app, raise_server_exceptions=False)
        self.spec = _Spec(app.openapi())
        self.capturing, self.captured = False, []
        self.owner: dict[str, tuple[int | None, int]] = {}

    def on_sql(self, _conn, _cursor, statement, parameters, _context, _executemany):
        if self.capturing:
            self.captured.append((statement, parameters))

    def call(self, key: str, headers: dict, claim: str):
        from app.limiter import limiter

        method, path = key.split(" ", 1)
        plan = _Plan(self.spec, method, path)
        url, params, body = plan.request(path_tenant=claim, query_tenant=claim, body_tenant=claim)
        params.update({name: claim for name in plan.required_tenant_query})
        if limiter is not None:
            try:
                limiter.reset()
            except Exception:  # noqa: BLE001
                pass
        self.captured, self.capturing = [], True
        previous = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError()))
        signal.alarm(30)
        try:
            response = self.client.request(method, url, headers=headers, params=params or None, json=body)
            status, text = response.status_code, response.text[:200000]
        except TimeoutError:
            status, text = -1, ""
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
            self.capturing = False
        return status, list(self.captured), text

    def owner_profile(self, key: str) -> tuple[int | None, int]:
        if key not in self.owner:
            self.owner[key] = (None, 403)
            for index in range(len(AW04_PROFILES)):
                status, _, _ = self.call(key, _h(AW04_OWNERS[index], **{"X-Tenant-Id": TENANT_A}), TENANT_A)
                if status not in REFUSED:
                    self.owner[key] = (index, status)
                    break
        return self.owner[key]


@pytest.fixture(scope="module")
def aw04(aw04_world):
    caller = _Aw04Caller()
    event.listen(Engine, "before_cursor_execute", caller.on_sql)
    yield caller
    event.remove(Engine, "before_cursor_execute", caller.on_sql)


def _bound_to(capture, tenant: str) -> list[str]:
    hits = _scope_hits(capture, tenant)
    return sorted(set(hits["read"]) | set(hits["write"]))


def _writes(capture) -> list[str]:
    return sorted(set(_tables_touched(capture)["write"]) - {"tenant_memberships", "scheduler_leader"})


@pytest.mark.parametrize("key", AW04_ROUTES)
def test_aw04_a_claim_of_another_tenant_is_refused_and_changes_nothing(aw04, key):
    index, owner_status = aw04.owner_profile(key)
    user = AW04_OWNERS[index if index is not None else 0]
    for name, headers in (("own tenant header", {"X-Tenant-Id": TENANT_A}), ("no header", {})):
        status, capture, text = aw04.call(key, _h(user, **headers), TENANT_B)
        failed_like_the_owner = owner_status >= 400 and status == owner_status
        assert status in REFUSED or failed_like_the_owner, f"{name}: claim of B got HTTP {status} (owner {owner_status})"
        assert _bound_to(capture, TENANT_B) == [], f"{name}: SQL bound to tenant B on {_bound_to(capture, TENANT_B)}"
        if status in REFUSED:
            assert _writes(capture) == [], f"{name}: refused request wrote {_writes(capture)}"
        assert TENANT_B not in text, f"{name}: the response names tenant B"


@pytest.mark.parametrize("key", AW04_ROUTES)
def test_aw04_the_same_tenant_contract_is_preserved(aw04, key):
    index, owner_status = aw04.owner_profile(key)
    if index is None:
        pytest.skip("no tenant role profile may call this route (role-gated); refusal covered above")
    # The owner, selecting tenant A and claiming tenant A, is served (``owner_profile``).
    # Whether a member who sends NO tenant header is served is AW-06M, tested below.
    assert owner_status not in REFUSED
    status, capture, _ = aw04.call(key, _h(AW04_OWNERS[index], **{"X-Tenant-Id": TENANT_A}), TENANT_A)
    assert status not in REFUSED, f"owner selecting and claiming their own tenant got HTTP {status}"
    assert _bound_to(capture, TENANT_B) == [] and _bound_to(capture, TENANT_C) == []
    status, capture, _ = aw04.call(key, _h(AW04_MULTI[index], **{"X-Tenant-Id": TENANT_C}), TENANT_C)
    assert status not in REFUSED, f"multi-member selecting and claiming C got HTTP {status}"
    assert _bound_to(capture, TENANT_A) == [] and _bound_to(capture, TENANT_B) == []


def test_aw04_most_routes_have_a_working_owner(aw04):
    working = [key for key in AW04_ROUTES if aw04.owner_profile(key)[0] is not None]
    assert len(working) >= len(AW04_ROUTES) - 4, sorted(set(AW04_ROUTES) - set(working))


# ══ require_tenant_roles — the shared membership dependency (562 call sites) ════
#
# Two defects, found when the AW-04 routes that use this dependency joined the
# route-wide harness: a tenant named in X-LumenAI-Tenant-Id was verified and a
# DISAGREEING X-Tenant-Id ignored; and a member who named no tenant was placed in
# a shared "default-tenant" (refused unless they belonged to it, pooled if they did).

RTR_ROUTE = "/api/olympus/trust/{tenant}/history"          # require_tenant_roles(*_ALL_ROLES)
RTR_MEMBER = f"b4-rtr-a-{RUN}@example.com"
RTR_MULTI = f"b4-rtr-ac-{RUN}@example.com"
RTR_DEFAULT_TOO = f"b4-rtr-a-default-{RUN}@example.com"
MEMBERSHIPS.extend([(TENANT_A, RTR_MEMBER), (TENANT_A, RTR_MULTI), (TENANT_C, RTR_MULTI),
                    (TENANT_A, RTR_DEFAULT_TOO), (DEFAULT, RTR_DEFAULT_TOO)])
_RTR_ROLE = {RTR_MEMBER: "operator", RTR_MULTI: "operator", RTR_DEFAULT_TOO: "operator"}


@pytest.fixture(autouse=True)
def _rtr_roles(_memberships):
    db = SessionLocal()
    try:
        for row in db.query(models.TenantMembership).filter(models.TenantMembership.user_email.in_(list(_RTR_ROLE))):
            row.role = _RTR_ROLE[row.user_email]
        db.commit()
    finally:
        db.close()


class TestRequireTenantRoles:
    def test_a_member_who_names_no_tenant_acts_in_their_own_tenant(self):
        response = client.get(RTR_ROUTE.format(tenant=TENANT_A), headers=_h(RTR_MEMBER))
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize("headers", [
        {"X-LumenAI-Tenant-Id": "A", "X-Tenant-Id": "B"},
        {"X-Tenant-Id": "A", "X-LumenAI-Tenant-Id": "B"},
    ], ids=["lumenai A + tenant-id B", "tenant-id A + lumenai B"])
    def test_two_tenant_headers_that_disagree_are_refused(self, headers):
        named = {k: {"A": TENANT_A, "B": TENANT_B}[v] for k, v in headers.items()}
        response = client.get(RTR_ROUTE.format(tenant=TENANT_A), headers=_h(RTR_MEMBER, **named))
        assert response.status_code == 403

    def test_a_member_of_several_tenants_must_select_one(self):
        assert client.get(RTR_ROUTE.format(tenant=TENANT_A), headers=_h(RTR_MULTI)).status_code == 403
        selected = client.get(RTR_ROUTE.format(tenant=TENANT_C), headers=_h(RTR_MULTI, **{"X-Tenant-Id": TENANT_C}))
        assert selected.status_code == 200, selected.text

    def test_a_member_of_default_tenant_and_another_is_not_pooled_into_default(self):
        """Belonging to the legacy shared tenant no longer makes it the silent default."""
        response = client.get(RTR_ROUTE.format(tenant=DEFAULT), headers=_h(RTR_DEFAULT_TOO))
        assert response.status_code == 403

    def test_a_user_with_no_membership_is_refused(self):
        assert client.get(RTR_ROUTE.format(tenant=DEFAULT), headers=_h(OUTSIDER)).status_code == 403


def test_guardianx_evidence_audit_event_is_attributed_to_the_verified_tenant():
    """Surfaced by the require_tenant_roles fix: once a member who names no tenant is
    served (instead of refused at the dependency), POST /api/guardianx/evidence wrote
    its paired audit event under the shared "default-tenant". It must be the caller's."""
    from app.models.audit_log import AuditLog
    from app.models.inspection import Inspection

    # P472-03 Batch 7: evidence may be written only under a source the caller's
    # tenant owns, so the inspection must exist in TENANT_A (set-up corrected; it
    # used a non-existent id "b4-<run>"). Assertions unchanged.
    db = SessionLocal()
    try:
        inspection = Inspection(file_name=f"b4-{RUN}.png", tenant_id=TENANT_A)
        db.add(inspection)
        db.commit()
        source_id = str(inspection.id)
    finally:
        db.close()
    response = client.post("/api/guardianx/evidence", headers=_h(RTR_MEMBER), json={
        "source_type": "inspection", "source_id": source_id, "evidence": ["e1"]})
    assert response.status_code in (200, 201), response.text
    db = SessionLocal()
    try:
        rows = db.query(AuditLog).filter(AuditLog.resource_type == "guardianx_evidence_ledger_entry",
                                         AuditLog.resource_id == str(response.json()["id"])).all()
        assert [row.tenant_id for row in rows] == [TENANT_A]
    finally:
        db.close()


# ══ AW-06N — no membership pooled in the literal "default-tenant" ═════════════
#
# Handlers in six modules used ``getattr(current_user, "tenant_id", None) or
# "default-tenant"``: a signed-in user with no membership (whose principal has no
# active tenant) was served the shared default tenant, and a member of several
# tenants could not select one at all. They now use ``principal_tenant``.

AW06N_ROUTES = [
    "/api/pre-sterilization-command-center/tray-readiness", "/api/pre-sterilization-command-center/dashboard",
    "/api/cios/dashboard", "/api/cios/events", "/api/knowledge-graph/analytics",
    "/api/knowledge-graph/learning-confidence", "/api/decision-policies", "/api/unknown-findings",
    "/api/analytics/kpi-summary",
]
NOMEMBER_MANAGER = f"b4-06n-none-{RUN}@example.com"
MULTI_MANAGER = f"b4-06n-ac-{RUN}@example.com"
MEMBERSHIPS.extend([(TENANT_A, MULTI_MANAGER), (TENANT_C, MULTI_MANAGER)])


@pytest.fixture(scope="module")
def aw06n_users(_users):
    db = SessionLocal()
    try:
        for user in (NOMEMBER_MANAGER, MULTI_MANAGER):
            db.add(UserRoleAssignment(username=user, role="spd_manager", assigned_by="p472-03-batch4"))
        db.commit()
    finally:
        db.close()


@pytest.mark.parametrize("path", AW06N_ROUTES)
def test_aw06n_a_user_with_no_membership_is_refused_not_pooled(aw06n_users, path):
    response = client.get(path, headers=_h(NOMEMBER_MANAGER))
    assert response.status_code in REFUSED, f"HTTP {response.status_code}: {response.text[:160]}"


@pytest.mark.parametrize("path", AW06N_ROUTES)
def test_aw06n_a_member_of_several_tenants_selects_one_and_is_served(aw06n_users, path):
    assert client.get(path, headers=_h(MULTI_MANAGER)).status_code in REFUSED
    selected = client.get(path, headers=_h(MULTI_MANAGER, **{"X-Tenant-Id": TENANT_C}))
    assert selected.status_code not in REFUSED, selected.text[:200]
    assert client.get(path, headers=_h(MULTI_MANAGER, **{"X-Tenant-Id": TENANT_B})).status_code in REFUSED
