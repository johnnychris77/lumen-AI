"""P472-03 application-wide tenant isolation — the confirmed findings, each
reproduced with real data.

The sweep (``test_p472_03_application_wide_isolation.py``) shows WHICH routes use
another tenant's id as their SQL scope. This file shows WHAT that means, with one
concrete exploit per root cause against the routes named for priority review:
tenant B owns a record, and a caller who has no right to tenant B reads it or
changes it.

Every exploit test states the REQUIRED behaviour. A test for a finding that is
still open is marked ``xfail(strict=True)`` with its finding id: an open security
finding, not accepted behaviour, and the suite fails the moment the route is
fixed without the marker being removed. The tests for AW-09, AW-10 and AW-11
lost their markers in remediation batch 1 and now simply pass. Nothing here is
skipped.

The control tests at the end pass today. They record where the existing control
was examined and found sufficient, so a tenant identifier in a request is not
mistaken for a vulnerability.

All data is synthetic.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.capture_device import CaptureDevice
from app.models.network_benchmark import NetworkParticipant
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token

client = TestClient(app)
REFUSED = (401, 403)


def _finding(finding_id: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding_id}: {summary}")


# ── identities ────────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _user(global_role: str, memberships: dict[str, str] | None = None) -> tuple[str, dict]:
    """A signed-in user with a global role and the given {tenant: tenant_role} memberships."""
    email = f"{_uid('aw')}@example.com"
    db = SessionLocal()
    try:
        db.add(UserRoleAssignment(username=email, role=global_role, assigned_by="p472-03-test"))
        for tenant, tenant_role in (memberships or {}).items():
            db.add(models.TenantMembership(tenant_id=tenant, user_email=email, role=tenant_role, is_enabled=True))
        db.commit()
    finally:
        db.close()
    return email, {"Authorization": f"Bearer {_make_token(email)}"}


class Tenants:
    """Tenant A and tenant B, each with a manager who is a verified member."""

    def __init__(self) -> None:
        self.a, self.b = _uid("aw-tenant-a"), _uid("aw-tenant-b")
        self.user_a, self.headers_a = _user("spd_manager", {self.a: "tenant_admin"})
        self.user_b, self.headers_b = _user("spd_manager", {self.b: "tenant_admin"})


@pytest.fixture
def tenants() -> Tenants:
    return Tenants()


def _rows(model, tenant: str) -> int:
    db = SessionLocal()
    try:
        return db.query(model).filter(model.tenant_id == tenant).count()
    finally:
        db.close()


# ══ AW-01 — tenant header trusted with no membership check ════════════════════

# Remediated in P472-03 batch 2 (``resolve_tenant`` returns the verified tenant). The
# assertion is unchanged; only the xfail marker went.
def test_aw01_a_member_of_a_cannot_read_tenant_b_analytics_by_header(tenants):
    db = SessionLocal()
    try:
        db.add(models.Inspection(
            file_name="b-confidential.bin", tenant_id=tenants.b, tenant_name="Tenant B",
            vendor_name=_uid("b-confidential-vendor"), site_name="b-site", status="completed"))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/tenant-analytics/summary", headers={**tenants.headers_a, "X-Tenant-Id": tenants.b})

    assert response.status_code in REFUSED, (
        f"tenant A read tenant B's analytics (HTTP {response.status_code}): {response.text[:200]}")


# ══ AW-02 — membership checked on one header, data scoped by another ═════════

# Remediated in P472-03 batch 2 (``resolve_tenant`` returns the verified tenant and
# refuses tenant headers that disagree). The assertion is unchanged.
def test_aw02_split_tenant_headers_cannot_read_tenant_b_audit_logs(tenants):
    marker = _uid("b-confidential-audit")
    db = SessionLocal()
    try:
        db.add(AuditLog(tenant_id=tenants.b, tenant_name="Tenant B", actor_email=tenants.user_b,
                        action_type="b.private.action", resource_type="record", resource_id=marker))
        db.commit()
    finally:
        db.close()

    response = client.get("/api/audit-logs", headers={
        **tenants.headers_a, "X-LumenAI-Tenant-Id": tenants.a, "X-Tenant-Id": tenants.b})

    assert response.status_code in REFUSED or marker not in response.text, (
        "a tenant-A administrator received tenant B's audit log by sending mismatched tenant headers")


# ══ AW-03 — handler re-reads an unverified tenant header ══════════════════════

@_finding("AW-03", "POST /api/network/opt-in takes its tenant from X-LumenAI-Tenant-Id after authentication")
def test_aw03_a_member_of_a_cannot_opt_tenant_b_into_the_intelligence_network(tenants):
    """Network participation is a data-sharing consent decision."""
    assert _rows(NetworkParticipant, tenants.b) == 0

    response = client.post("/api/network/opt-in", headers={**tenants.headers_a, "X-LumenAI-Tenant-Id": tenants.b})

    enrolled = _rows(NetworkParticipant, tenants.b)
    assert response.status_code in REFUSED and enrolled == 0, (
        f"HTTP {response.status_code}; tenant B enrolled in the network by a member of tenant A: {enrolled} row(s)")


# ══ AW-04 — tenant taken from a query, path or body parameter ═════════════════

@_finding("AW-04", "POST /api/accreditation/programs stores the tenant named in the body")
def test_aw04_a_member_of_a_cannot_create_an_accreditation_program_in_tenant_b(tenants):
    before = _rows(models.AccreditationProgram, tenants.b)

    response = client.post("/api/accreditation/programs", headers=tenants.headers_a, json={
        "tenant_id": tenants.b, "facility_id": "b-facility", "accreditor": "joint_commission"})

    written = _rows(models.AccreditationProgram, tenants.b) - before
    assert response.status_code in REFUSED and written == 0, (
        f"HTTP {response.status_code}; {written} program(s) written into tenant B by a member of tenant A")


@_finding("AW-04", "GET /api/accreditation/programs?tenant_id= serves the tenant named in the query")
def test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs(tenants):
    note = _uid("b-confidential-note")
    created = client.post("/api/accreditation/programs", headers=tenants.headers_b, json={
        "tenant_id": tenants.b, "facility_id": "b-facility", "accreditor": "dnv", "notes": note})
    assert created.status_code == 201, created.text

    response = client.get("/api/accreditation/programs", headers=tenants.headers_a, params={"tenant_id": tenants.b})

    assert response.status_code in REFUSED or note not in response.text, (
        "tenant A listed tenant B's accreditation programs by naming B in the query")


@_finding("AW-04", "POST /api/intelligence/consent records sharing consent for the tenant named in the body")
def test_aw04_a_member_of_a_cannot_grant_data_sharing_consent_for_tenant_b(tenants):
    from app.models.vendor_intelligence import IntelligenceSharingConsent

    before = _rows(IntelligenceSharingConsent, tenants.b)

    response = client.post("/api/intelligence/consent", headers=tenants.headers_a, json={
        "tenant_id": tenants.b, "facility_id": "b-facility", "consented_by": "attacker@example.com"})

    written = _rows(IntelligenceSharingConsent, tenants.b) - before
    assert response.status_code in REFUSED and written == 0, (
        f"HTTP {response.status_code}; {written} consent record(s) created for tenant B by a member of tenant A")


@_finding("AW-04", "GET /api/network-intelligence/registry?tenant_id= serves the tenant named in the query")
def test_aw04_a_member_of_a_cannot_read_tenant_b_network_registry_entry():
    """These routes require the ``executive`` or ``admin`` global role."""
    a, b = _uid("aw-tenant-a"), _uid("aw-tenant-b")
    _, headers_a = _user("executive", {a: "admin"})
    _, headers_b = _user("executive", {b: "admin"})
    registered = client.post("/api/network-intelligence/registry", headers=headers_b, json={
        "tenant_id": b, "facility_name": "B General", "region": "b-region"})
    assert registered.status_code in (200, 201), registered.text

    response = client.get("/api/network-intelligence/registry", headers=headers_a, params={"tenant_id": b})

    assert response.status_code in REFUSED, (
        f"tenant A read tenant B's network registry entry (HTTP {response.status_code}): {response.text[:200]}")


# ══ AW-05 — header trusted when the user has no single verified tenant ════════

# Remediated in P472-03 batch 2 (the fallback to the request header is gone; the
# tenant comes from verified membership). The assertions are unchanged.
def test_aw05_a_user_with_no_membership_cannot_register_a_device_in_tenant_b(tenants):
    _, outsider = _user("spd_manager")              # the role, but no tenant membership at all
    before = _rows(CaptureDevice, tenants.b)

    response = client.post("/api/capture/devices", headers={**outsider, "X-Tenant-Id": tenants.b},
                           json={"name": "attacker-device"})

    written = _rows(CaptureDevice, tenants.b) - before
    assert response.status_code in REFUSED and written == 0, (
        f"HTTP {response.status_code}; {written} capture device(s) registered in tenant B by a user with no membership")


def test_aw05_a_user_with_two_memberships_cannot_list_a_third_tenants_devices(tenants):
    owner_registers = client.post("/api/capture/devices", headers=tenants.headers_b, json={"name": _uid("b-device")})
    assert owner_registers.status_code == 201, owner_registers.text
    device_name = owner_registers.json().get("name") or owner_registers.json().get("device", {}).get("name", "")
    other_1, other_2 = _uid("aw-tenant-c"), _uid("aw-tenant-d")
    _, both = _user("spd_manager", {other_1: "tenant_admin", other_2: "tenant_admin"})

    response = client.get("/api/capture/devices", headers={**both, "X-Tenant-Id": tenants.b})

    assert response.status_code in REFUSED or (device_name and device_name not in response.text), (
        "a user with memberships in two unrelated tenants listed tenant B's capture devices")


# ══ AW-06 — a shared default tenant instead of the verified one ═══════════════

@_finding("AW-06M", "handlers read the raw tenant header, so clients that send none all act in default-tenant")
def test_aw06m_members_of_different_tenants_do_not_share_a_default_tenant(tenants):
    """No attack: both callers are verified members of different tenants and send
    no tenant header, exactly as the web client does."""
    db = SessionLocal()
    try:
        db.query(NetworkParticipant).filter(NetworkParticipant.tenant_id == "default-tenant").delete()
        db.commit()
    finally:
        db.close()

    assert client.post("/api/network/opt-in", headers=tenants.headers_a).status_code == 200
    seen_by_b = client.get("/api/network/opt-in/status", headers=tenants.headers_b)

    pooled = _rows(NetworkParticipant, "default-tenant")
    own = _rows(NetworkParticipant, tenants.a)
    assert pooled == 0 and own == 1, (
        f"tenant A's opt-in was stored under default-tenant ({pooled} row) instead of tenant A ({own} row); "
        f"tenant B then sees: {seen_by_b.text[:160]}")


# On the capture-device routes this was remediated in P472-03 batch 2 together with
# AW-05 (same line of code). The assertions are unchanged. AW-06N is still OPEN on
# other routes: see the next test.
def test_aw06n_users_with_no_membership_are_refused_not_pooled():
    _, first = _user("spd_manager")
    _, second = _user("spd_manager")
    name = _uid("pooled-device")

    registered = client.post("/api/capture/devices", headers=first, json={"name": name})
    listed = client.get("/api/capture/devices", headers=second)

    assert registered.status_code in REFUSED and listed.status_code in REFUSED, (
        f"two unrelated users with no tenant membership share one tenant: register HTTP {registered.status_code}, "
        f"other user's list HTTP {listed.status_code}, device visible: {name in listed.text}")


@_finding("AW-06N", "getattr(current_user, 'tenant_id', None) or 'default-tenant': no membership is pooled, not refused")
def test_aw06n_users_with_no_membership_are_still_pooled_where_the_default_is_a_literal():
    """Still open after batch 2: handlers whose fallback is the literal
    ``default-tenant`` rather than the request header (16 places in 7 modules)."""
    db = SessionLocal()
    try:
        db.add(models.Inspection(file_name="pooled.bin", tenant_id="default-tenant", tenant_name="Default",
                                 vendor_name=_uid("pooled-vendor"), site_name="pooled-site", status="completed"))
        db.commit()
    finally:
        db.close()
    _, outsider = _user("spd_manager")

    response = client.get("/api/pre-sterilization-command-center/tray-readiness", headers=outsider)

    assert response.status_code in REFUSED, (
        f"a user with no tenant membership was served the shared default tenant (HTTP {response.status_code})")


# ══ AW-07 — manufacturer identity asserted by the client ══════════════════════

@_finding("AW-07", "require_manufacturer_auth accepts whatever X-Manufacturer-ID the caller sends")
def test_aw07_a_hospital_user_cannot_assume_an_arbitrary_manufacturer_identity(tenants):
    statuses = {
        manufacturer: client.get("/api/manufacturer-portal/my-scorecard",
                                 headers={**tenants.headers_a, "X-Manufacturer-ID": manufacturer}).status_code
        for manufacturer in ("stryker", "olympus", _uid("any-manufacturer"))
    }
    assert all(status in REFUSED for status in statuses.values()), (
        f"a hospital user with no manufacturer relationship was served as each manufacturer it named: {statuses}")


# ══ AW-08 — listing with no tenant predicate ══════════════════════════════════

@_finding("AW-08", "GET /api/accreditation/programs with no tenant_id returns every tenant's programs")
def test_aw08_listing_accreditation_programs_does_not_return_other_tenants(tenants):
    note = _uid("b-confidential-note")
    created = client.post("/api/accreditation/programs", headers=tenants.headers_b, json={
        "tenant_id": tenants.b, "facility_id": "b-facility", "accreditor": "cms", "notes": note})
    assert created.status_code == 201, created.text

    response = client.get("/api/accreditation/programs", headers=tenants.headers_a)     # names no tenant

    assert note not in response.text, "tenant A's unfiltered listing contains tenant B's accreditation program"


@_finding("AW-08", "vendor analytics loads every tenant's inspections (db.query(Inspection).all()) behind a global role")
def test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections(tenants):
    vendor = _uid("b-confidential-vendor")
    db = SessionLocal()
    try:
        db.add(models.Inspection(
            file_name="b-confidential.bin", tenant_id=tenants.b, tenant_name="Tenant B",
            vendor_name=vendor, site_name="b-site", status="completed"))
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/analytics/vendors/{vendor}/scorecard.json",
                          headers={**tenants.headers_a, "X-Tenant-Id": tenants.a})

    assert response.status_code in (*REFUSED, 404), (
        f"tenant A was served a scorecard built from tenant B's inspections (HTTP {response.status_code}): "
        f"{response.text[:200]}")


@_finding("AW-08", "GuardianX audit replay loads its subject by id with no tenant predicate")
def test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection(tenants):
    """Confirmed while implementing governance decision GD-2 (batch 2); not fixed."""
    db = SessionLocal()
    try:
        row = models.Inspection(file_name="b-replay.bin", tenant_id=tenants.b, tenant_name="Tenant B",
                                vendor_name=_uid("b-vendor"), site_name="b-site", status="completed")
        db.add(row)
        db.commit()
        inspection_id = row.id
    finally:
        db.close()

    _, member_of_a = _user("viewer", {tenants.a: "viewer"})     # the route requires this tenant role

    response = client.get(f"/api/guardianx/audit-replay/inspections/{inspection_id}",
                          headers={**member_of_a, "X-Tenant-Id": tenants.a})

    assert response.status_code in (*REFUSED, 404), (
        f"a member of tenant A replayed tenant B's inspection {inspection_id} (HTTP {response.status_code})")


# ══ AW-09 — unauthenticated access to tenant data ═════════════════════════════
#
# REMEDIATED in P472-03 batch 1 for the enterprise intake module: these are now
# ordinary tests. Their assertions are unchanged; only the xfail markers went.
# (Three public aggregate-count routes remain in the sweep register under AW-09
# pending an owner's decision; they are not exercised here.)

@pytest.mark.parametrize("path", [
    "/api/enterprise/audit-command-center",
    "/api/enterprise/audit-command-center.csv",
    "/api/enterprise/audit-command-center.powerbi.csv",
])
def test_aw09_an_unauthenticated_caller_cannot_read_the_audit_log(tenants, path):
    marker = _uid("b-confidential-audit")
    db = SessionLocal()
    try:
        db.add(AuditLog(tenant_id=tenants.b, tenant_name="Tenant B", actor_email=f"{marker}@example.com",
                        action_type="b.private.action", resource_type="record", resource_id=marker))
        db.commit()
    finally:
        db.close()

    response = client.get(path)                      # no credentials of any kind

    assert response.status_code in REFUSED, (
        f"HTTP {response.status_code} with no credentials; tenant B's audit record in the response: "
        f"{marker in response.text}; tenant B's id in the response: {tenants.b in response.text}")


@pytest.mark.parametrize("path", [
    "/api/enterprise/findings/kpi-summary",
    "/api/enterprise/executive-quality-review-dashboard",
    "/api/enterprise/baseline-review-queue",
    "/api/enterprise/export-readiness-history",
    "/api/enterprise/vendor-baselines",
])
def test_aw09_enterprise_quality_data_requires_authentication(path):
    response = client.get(path)
    assert response.status_code in REFUSED, f"HTTP {response.status_code} with no credentials: {response.text[:160]}"


# ══ AW-10 — tenant data held outside the database ═════════════════════════════
#
# REMEDIATED in P472-03 batch 1: ordinary tests now, assertions unchanged. The
# description below is of the defect as found.
#
# The sweep's oracle is SQL, so it cannot see this store: vendor governance events
# live in one process-wide list with no tenant field. Writes require enterprise
# authentication; the four read routes require nothing and return every tenant's
# events. Found by reviewing the public routes that execute no SQL.

def _tenant_b_vendor_event(tenants: Tenants) -> str:
    marker = _uid("b-confidential-vendor-event")
    created = client.post(
        "/api/enterprise/vendor-governance/events",
        headers={**tenants.headers_b, "X-Tenant-Id": tenants.b},
        json={"vendor_name": marker, "event_type": "quality_escape", "event_summary": f"summary {marker}",
              "risk_level": "high", "site": "b-site"})
    assert created.status_code == 200, created.text
    return marker


@pytest.mark.parametrize("path", [
    "/api/enterprise/vendor-governance/events",
    "/api/enterprise/vendor-governance/summary",
    "/api/enterprise/vendor-governance/capa-linkage-summary",
    "/api/enterprise/vendor-governance/powerbi-csv",
])
def test_aw10_an_unauthenticated_caller_cannot_read_vendor_governance_events(tenants, path):
    marker = _tenant_b_vendor_event(tenants)

    response = client.get(path)                      # no credentials of any kind

    assert response.status_code in REFUSED, (
        f"HTTP {response.status_code} with no credentials; tenant B's vendor event in the response: "
        f"{marker in response.text}")


def test_aw10_a_member_of_a_does_not_see_tenant_b_vendor_governance_events(tenants):
    marker = _tenant_b_vendor_event(tenants)

    response = client.get("/api/enterprise/vendor-governance/events",
                          headers={**tenants.headers_a, "X-Tenant-Id": tenants.a})

    assert marker not in response.text, "tenant A's listing contains tenant B's vendor governance event"


# ══ AW-11 — CAPA records in a store with no tenant column ═════════════════════
#
# REMEDIATED in P472-03 batch 1: ordinary tests now, assertions unchanged. The
# description below is of the defect as found.
#
# ``app/services/capa_service.py`` opens its own ``sqlite3`` connection, outside
# the SQLAlchemy engine the sweep listens on, and its ``capas`` table has no
# tenant column. Every ``/api/capa`` route requires only a global role, so every
# hospital's managers share one CAPA register.

def _tenant_b_capa(tenants: Tenants) -> tuple[str, str]:
    marker = _uid("b-confidential-capa")
    created = client.post("/api/capa", headers={**tenants.headers_b, "X-Tenant-Id": tenants.b}, json={
        "title": marker, "description": f"root cause {marker}", "risk_level": "high", "owner": "b-quality-lead"})
    assert created.status_code == 200, created.text
    listed = client.get("/api/capa", headers={**tenants.headers_b, "X-Tenant-Id": tenants.b}, params={"limit": 500})
    capa_id = next(item["id"] for item in listed.json()["items"] if item["title"] == marker)
    return marker, capa_id


@pytest.mark.parametrize("path", ["/api/capa", "/api/capa/powerbi-csv"])
def test_aw11_a_member_of_a_does_not_see_tenant_b_capas(tenants, path):
    marker, _ = _tenant_b_capa(tenants)

    response = client.get(path, headers={**tenants.headers_a, "X-Tenant-Id": tenants.a}, params={"limit": 500})

    assert marker not in response.text, f"tenant A's {path} contains tenant B's CAPA"


def test_aw11_a_member_of_a_cannot_read_tenant_b_capa_by_id(tenants):
    marker, capa_id = _tenant_b_capa(tenants)

    response = client.get(f"/api/capa/{capa_id}", headers={**tenants.headers_a, "X-Tenant-Id": tenants.a})

    assert response.status_code in (*REFUSED, 404), (
        f"tenant A read tenant B's CAPA by id (HTTP {response.status_code}); record returned: {marker in response.text}")


def test_aw11_a_member_of_a_cannot_modify_tenant_b_capa(tenants):
    _, capa_id = _tenant_b_capa(tenants)

    response = client.patch(f"/api/capa/{capa_id}", headers={**tenants.headers_a, "X-Tenant-Id": tenants.a},
                            json={"status": "closed", "owner": "tenant-a-intruder"})

    after = client.get(f"/api/capa/{capa_id}", headers={**tenants.headers_b, "X-Tenant-Id": tenants.b}).text
    assert response.status_code in (*REFUSED, 404) and "tenant-a-intruder" not in after, (
        f"tenant A changed tenant B's CAPA (HTTP {response.status_code}); "
        f"intruder recorded as owner: {'tenant-a-intruder' in after}")


# ══ Controls — examined and sufficient ════════════════════════════════════════

class _SqlCounter:
    def __enter__(self):
        self.statements: list[str] = []
        event.listen(Engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *_exc):
        event.remove(Engine, "before_cursor_execute", self._record)

    def _record(self, _conn, _cursor, statement, *_rest):
        self.statements.append(statement)


def test_control_baseline_ranking_audit_evidence_is_stateless():
    """``POST /baseline-ranking/audit-evidence`` is unauthenticated, which P472-03
    flagged for review. It is NOT a tenant-isolation defect: it executes no SQL
    and returns only a normalised copy of the fields the caller sent. Whether a
    stateless helper should require authentication is a separate, low-risk policy
    question recorded in the matrix."""
    payload = {"instrument_match_status": "matched", "baseline_status": "approved",
               "baseline_confidence": "high", "tenant_id": "some-other-tenant", "catalog_number": "X-1"}
    for path in ("/baseline-ranking/audit-evidence", "/api/baseline-ranking/audit-evidence"):
        with _SqlCounter() as sql:
            response = client.post(path, json=payload)
        if response.status_code == 404:
            continue
        assert response.status_code == 200
        assert sql.statements == []
        assert "some-other-tenant" not in response.text
        return
    pytest.fail("the audit-evidence route is not mounted at either expected path")


def test_control_tenant_role_dependency_verifies_the_header_it_uses(tenants):
    """Routes whose ONLY tenant source is ``require_tenant_roles`` verify membership
    for the same header they scope by. Naming tenant B is refused, by either header."""
    path = "/api/guardianx/reports/knowledge-provenance"
    _, viewer = _user("viewer", {tenants.a: "viewer"})
    own = client.get(path, headers={**viewer, "X-Tenant-Id": tenants.a})
    assert own.status_code == 200, own.text
    for header in ("X-Tenant-Id", "X-LumenAI-Tenant-Id"):
        assert client.get(path, headers={**viewer, header: tenants.b}).status_code == 403
    # Split headers do not help either: the dependency scopes by the header it verified.
    split = client.get(path, headers={**viewer, "X-LumenAI-Tenant-Id": tenants.a, "X-Tenant-Id": tenants.b})
    assert tenants.b not in split.text


def test_control_verified_context_routes_ignore_or_refuse_a_foreign_tenant(tenants):
    """Routes on the verified auth context (remediated in c13c5eb / 6c3072c)."""
    for path in ("/api/enterprise/cv/history", "/api/regulatory/readiness", "/api/enterprise/benchmarks/rollup"):
        assert client.get(path, headers=tenants.headers_a).status_code == 200, path
        for headers, params in (
            ({**tenants.headers_a, "X-Tenant-Id": tenants.b}, None),
            ({**tenants.headers_a, "X-LumenAI-Tenant-Id": tenants.b}, None),
        ):
            response = client.get(path, headers=headers, params=params)
            assert response.status_code in (200, 403), path
            assert tenants.b not in response.text, path
    for path in ("/api/regulatory/readiness", "/api/enterprise/benchmarks/rollup"):
        assert client.get(path, headers=tenants.headers_a, params={"tenant_id": tenants.b}).status_code == 403


def test_control_platform_admin_routes_refuse_tenant_users(tenants):
    """Cross-tenant administration routes are gated on the platform-admin role; a
    tenant's own administrator is refused."""
    for method, path in (("GET", "/api/platform/admin/audit-logs"), ("POST", "/api/admin/tenants")):
        response = client.request(method, path, headers=tenants.headers_a, json={} if method == "POST" else None)
        assert response.status_code in REFUSED, (method, path, response.status_code)
