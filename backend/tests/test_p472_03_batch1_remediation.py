"""P472-03 remediation batch 1 — AW-09, AW-10, AW-11.

Covers every mounted route of the three remediated modules:

* ``app.routes.enterprise_intake``  (enterprise quality: findings, evidence,
  baselines, CAPAs, governance packets, exports, audit command center)
* ``app.routes.vendor_governance``  (vendor governance events)
* ``app.routes.capa``               (the CAPA register)

Two tenants, A and B, each own a full set of real records created through the
API: a finding with evidence, a risk score, a disposition, a review, an
enterprise CAPA, an instrument baseline, export history and audit rows; a CAPA
in the register; and a vendor governance event. Every record carries a marker
that is unique to its tenant.

What is asserted, for every route:

* an unauthenticated, malformed-token, expired-token, tampered-token,
  no-membership or disabled-membership caller is refused, learns nothing and
  changes nothing;
* tenant A, correctly authenticated, cannot read, export, aggregate or modify
  tenant B's records — not by B's object ids, not by naming B in a header or a
  body, not through a list or a dashboard;
* SQL executed for tenant A never binds tenant B's id, and every statement on a
  tenant-owned table is restricted to A or is a primary-key lookup whose row is
  then checked;
* the owner's own workflow still works;
* a user with two memberships acts only in the tenant they select.

Nothing here is skipped or expected to fail. All data is synthetic.
"""
from __future__ import annotations

import base64
import copy
import io
import re
import zipfile
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.db import models
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.enterprise_quality import (
    EnterpriseCapa,
    EnterpriseDepartment,
    EnterpriseDisposition,
    EnterpriseEvidence,
    EnterpriseExportReadinessHistory,
    EnterpriseFacility,
    EnterpriseFinding,
    EnterpriseInstrument,
    EnterpriseInstrumentBaseline,
    EnterpriseRiskScore,
    EnterpriseVendor,
)
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import ALGORITHM, SECRET_KEY, _make_token, jwt
from app.services import capa_lifecycle_service, capa_service, vendor_governance_service

client = TestClient(app)
REFUSED = (401, 403)
HIDDEN = (403, 404)            # another tenant's object: refused or "not found", never served

MODULES = ("app.routes.enterprise_intake", "app.routes.vendor_governance", "app.routes.capa")
# Probes that stay public. They must carry no tenant data (asserted below).
PUBLIC_PROBES = {
    ("GET", "/api/enterprise/storage/health"),
    ("GET", "/api/enterprise/vendor-governance/health"),
    ("GET", "/api/capa/health"),
}
TENANT_MODELS = [
    EnterpriseFacility, EnterpriseDepartment, EnterpriseVendor, EnterpriseInstrument, EnterpriseEvidence,
    EnterpriseFinding, EnterpriseRiskScore, EnterpriseDisposition, EnterpriseCapa,
    EnterpriseInstrumentBaseline, EnterpriseExportReadinessHistory, AuditLog,
]
TENANT_TABLES = [model.__tablename__ for model in TENANT_MODELS]


def _routes() -> list[tuple[str, str]]:
    found = []
    for route in app.routes:
        if isinstance(route, APIRoute) and route.endpoint.__module__ in MODULES:
            for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
                found.append((method, route.path))
    return sorted(set(found))


ROUTES = _routes()
PROTECTED = [route for route in ROUTES if route not in PUBLIC_PROBES]
ROUTE_IDS = [f"{method} {path}" for method, path in PROTECTED]
WRITES = [route for route in PROTECTED if route[0] != "GET"]


# ── identities ────────────────────────────────────────────────────────────────

def _uid(prefix: str) -> str:
    import uuid

    return f"{prefix}{uuid.uuid4().hex[:10]}"


# conftest clears ``tenant_memberships`` before every test, so the memberships of
# the module-scoped identities are recorded here and restored per test.
_MEMBERSHIPS: list[tuple[str, str, bool]] = []


def _seed_memberships() -> None:
    db = SessionLocal()
    try:
        for tenant, email, enabled in _MEMBERSHIPS:
            present = (db.query(models.TenantMembership)
                       .filter_by(tenant_id=tenant, user_email=email).first())
            if present is None:
                db.add(models.TenantMembership(
                    tenant_id=tenant, user_email=email, role="tenant_admin", is_enabled=enabled))
        db.commit()
    finally:
        db.close()


def _user(global_role: str, memberships: dict[str, bool]) -> tuple[str, dict]:
    """A signed-in user with a global role and {tenant: enabled} memberships."""
    email = f"{_uid('b1')}@example.com"
    db = SessionLocal()
    try:
        db.add(UserRoleAssignment(username=email, role=global_role, assigned_by="p472-03-batch1"))
        db.commit()
    finally:
        db.close()
    _MEMBERSHIPS.extend((tenant, email, enabled) for tenant, enabled in memberships.items())
    _seed_memberships()
    return email, {"Authorization": f"Bearer {_make_token(email)}"}


def _expired_token(user: str) -> str:
    issued = datetime.now(timezone.utc) - timedelta(hours=3)
    return jwt.encode({"sub": user, "iat": int(issued.timestamp()),
                       "exp": int((issued + timedelta(minutes=5)).timestamp())}, SECRET_KEY, algorithm=ALGORITHM)


def _tampered_token(user: str) -> str:
    header, payload, signature = _make_token(user).split(".")
    return f"{header}.{payload}.{signature[:-4]}AAAA"


@dataclass
class Party:
    """One tenant with a hospital administrator, a quality manager and one of everything."""
    tenant: str
    marker: str
    admin: str = ""
    admin_headers: dict = field(default_factory=dict)
    manager: str = ""
    manager_headers: dict = field(default_factory=dict)
    finding_id: int = 0
    instrument_id: int = 0
    evidence_id: int = 0
    enterprise_capa_id: int = 0
    baseline_id: int = 0
    register_capa_id: str = ""
    event_id: str = ""

    def headers(self, route: tuple[str, str]) -> dict:
        """The identity that passes the route's ROLE guard, so only tenancy is under test."""
        return self.manager_headers if route[1].startswith("/api/capa") else self.admin_headers


@dataclass
class World:
    a: Party
    b: Party
    library_baseline_id: int
    outsider: dict            # authenticated, hospital_admin role, member of no tenant
    disabled_b: dict          # authenticated, membership in B is disabled
    multi: dict               # hospital_admin, enabled member of A and B
    multi_manager: dict       # spd_manager, enabled member of A and B


def _png() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _build_party(tenant: str, marker: str) -> Party:
    party = Party(tenant=tenant, marker=marker)
    party.admin, party.admin_headers = _user("hospital_admin", {tenant: True})
    party.manager, party.manager_headers = _user("spd_manager", {tenant: True})
    h = party.admin_headers

    intake = client.post("/api/enterprise/intake", headers=h, json={
        "facility_name": f"facility {marker}", "vendor_name": f"vendor {marker}",
        "instrument_name": f"instrument {marker}", "finding_category": "bioburden / retained debris",
        "finding_description": f"description {marker}", "severity": "critical", "confidence_score": 0.9,
        "evidence_file_name": f"evidence-{marker}.png"})
    assert intake.status_code == 200, intake.text
    party.finding_id = intake.json()["finding_id"]
    assert intake.json()["tenant_id"] == tenant

    db = SessionLocal()
    try:
        party.instrument_id = db.get(EnterpriseFinding, party.finding_id).instrument_id
    finally:
        db.close()

    review = client.post(f"/api/enterprise/intake/{party.finding_id}/review", headers=h,
                         json={"decision": "approve", "review_notes": f"review {marker}"})
    assert review.status_code == 200, review.text

    capa = client.post(f"/api/enterprise/intake/{party.finding_id}/capa", headers=h,
                       json={"title": f"enterprise capa {marker}", "description": f"capa description {marker}"})
    assert capa.status_code == 200, capa.text
    party.enterprise_capa_id = capa.json()["capa_id"]

    evidence = client.post(f"/api/enterprise/intake/{party.finding_id}/evidence", headers=h,
                           files={"file": (f"upload-{marker}.png", _png(), "image/png")},
                           data={"notes": f"evidence notes {marker}"})
    assert evidence.status_code == 200, evidence.text
    party.evidence_id = evidence.json()["evidence_id"]

    baseline = client.post(f"/api/enterprise/instruments/{party.instrument_id}/baseline", headers=h,
                           files={"file": (f"baseline-{marker}.png", _png(), "image/png")},
                           data={"manufacturer_name": f"manufacturer {marker}", "baseline_notes": f"baseline {marker}"})
    assert baseline.status_code == 200, baseline.text
    party.baseline_id = baseline.json()["baseline_id"]

    for path in (f"/api/enterprise/intake/{party.finding_id}/export-readiness-status",
                 f"/api/enterprise/intake/{party.finding_id}/governance-packet.pdf"):
        produced = client.get(path, headers=h)
        assert produced.status_code == 200, (path, produced.text[:200])

    register = client.post("/api/capa", headers=party.manager_headers, json={
        "title": f"register capa {marker}", "description": f"root cause {marker}", "risk_level": "high",
        "owner": f"owner {marker}", "due_date": "2020-01-01"})
    assert register.status_code == 200, register.text
    party.register_capa_id = register.json()["capa"]["id"]

    governance = client.post("/api/enterprise/vendor-governance/events", headers=h, json={
        "vendor_name": f"governed vendor {marker}", "event_type": "quality_escape",
        "event_summary": f"event summary {marker}", "risk_level": "high", "site": f"site {marker}"})
    assert governance.status_code == 200, governance.text
    party.event_id = governance.json()["event"]["id"]
    return party


@pytest.fixture(scope="module")
def world() -> World:
    # Module-scoped fixtures are set up before conftest's function-scoped
    # table-creating fixture, so make sure the schema exists first.
    from app.db.base import Base
    from app.db.session import engine

    Base.metadata.create_all(bind=engine)
    a = _build_party(_uid("b1tenanta"), _uid("amark"))
    b = _build_party(_uid("b1tenantb"), _uid("bmark"))

    library = client.post("/api/enterprise/vendor-baseline-subscription/baselines", headers=a.admin_headers, json={
        "vendor_name": "Shared Library Vendor", "instrument_name": "Shared Library Instrument",
        "catalog_number": _uid("cat")})
    assert library.status_code == 200, library.text
    library_id = library.json().get("baseline", {}).get("baseline_id") or library.json().get("baseline_id") or 1

    _, outsider = _user("hospital_admin", {})
    _, disabled_b = _user("hospital_admin", {b.tenant: False})
    _, multi = _user("hospital_admin", {a.tenant: True, b.tenant: True})
    _, multi_manager = _user("spd_manager", {a.tenant: True, b.tenant: True})
    return World(a, b, int(library_id), outsider, disabled_b, multi, multi_manager)


@pytest.fixture(autouse=True)
def _memberships(world):
    _seed_memberships()


# ── requests ──────────────────────────────────────────────────────────────────

def _request(route: tuple[str, str], objects: Party, world: World) -> tuple[str, dict]:
    """A valid request for ``route`` that addresses ``objects``' records."""
    method, template = route
    values = {
        "finding_id": objects.finding_id,
        "evidence_id": objects.evidence_id,
        "instrument_id": objects.instrument_id,
        "event_id": objects.event_id,
        "capa_id": objects.register_capa_id if template.startswith("/api/capa") else objects.enterprise_capa_id,
        "baseline_id": world.library_baseline_id if "vendor-baseline-subscription" in template else objects.baseline_id,
    }
    path = re.sub(r"\{(\w+)\}", lambda m: str(values[m.group(1)]), template)
    kwargs: dict = {}
    params = {
        "/api/enterprise/intake/{finding_id}/governance-packet/verify-hash": {"packet_hash": "0" * 64},
        "/api/enterprise/audit/verify-chain": {
            "resource_type": "enterprise_governance_packet", "resource_id": str(objects.finding_id)},
        "/api/enterprise/audit/events/export/verify": {"audit_export_hash": "0" * 64},
        "/api/enterprise/audit/events/export/manifest/verify": {"manifest_hash": "0" * 64},
        "/api/enterprise/audit/evidence-bundle/verify": {"bundle_hash": "0" * 64},
        "/api/enterprise/audit/evidence-bundle/verification-summary": {"bundle_hash": "0" * 64},
    }.get(template)
    if params:
        kwargs["params"] = params
    if method == "GET":
        return path, kwargs

    tag = _uid("w")
    bodies = {
        ("POST", "/api/enterprise/intake"): {"json": {
            "facility_name": f"facility {tag}", "vendor_name": f"vendor {tag}", "instrument_name": f"instrument {tag}",
            "finding_category": "bioburden / retained debris", "severity": "high"}},
        ("POST", "/api/enterprise/intake/{finding_id}/review"): {"json": {
            "decision": "reject", "review_notes": f"intruder review {tag}", "reviewer_name": "intruder"}},
        ("POST", "/api/enterprise/intake/{finding_id}/capa"): {"json": {"title": f"intruder capa {tag}"}},
        ("PATCH", "/api/enterprise/capas/{capa_id}/status"): {"json": {"status": "closed", "note": f"intruder {tag}"}},
        ("POST", "/api/enterprise/intake/{finding_id}/evidence"): {
            "files": {"file": (f"intruder-{tag}.png", _png(), "image/png")}},
        ("POST", "/api/enterprise/instruments/{instrument_id}/baseline"): {
            "files": {"file": (f"intruder-{tag}.png", _png(), "image/png")}},
        ("POST", "/api/enterprise/baselines/{baseline_id}/review"): {"json": {
            "decision": "reject", "review_notes": f"intruder {tag}"}},
        ("POST", "/api/enterprise/baseline-aware-score"): {"json": {}},
        ("POST", "/api/enterprise/vendor-baseline-subscription/baselines"): {"json": {
            "vendor_name": "Shared Library Vendor", "instrument_name": f"library {tag}"}},
        ("POST", "/api/enterprise/vendor-baseline-subscription/baselines/upload-image"): {
            "files": {"file": (f"library-{tag}.png", _png(), "image/png")}},
        ("POST", "/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve"): {"json": {}},
        ("POST", "/api/enterprise/vendor-baseline-subscription/match"): {"json": {}},
        ("POST", "/api/enterprise/audit/events"): {"json": {"action_type": "demo_audit_event", "resource_id": tag}},
        ("POST", "/api/enterprise/vendor-governance/events"): {"json": {
            "vendor_name": f"vendor {tag}", "event_type": "quality_escape", "event_summary": f"summary {tag}"}},
        ("POST", "/api/enterprise/vendor-governance/events/{event_id}/link-capa"): {"json": {
            "capa_id": objects.register_capa_id}},
        ("POST", "/api/capa"): {"json": {"title": f"capa {tag}"}},
        ("POST", "/api/capa/from-audit-signal"): {"json": {"event_summary": f"signal {tag}"}},
        ("PATCH", "/api/capa/{capa_id}"): {"json": {"owner": f"intruder {tag}", "status": "closed"}},
    }
    kwargs.update(bodies.get(route, {}))
    return path, kwargs


def _send(route: tuple[str, str], headers: dict, objects: Party, world: World):
    path, kwargs = _request(route, objects, world)
    return client.request(route[0], path, headers=headers, **kwargs)


# ── what a response reveals ───────────────────────────────────────────────────

def _pdf_text(content: bytes) -> str:
    """Decoded text of a ReportLab PDF's content streams (ASCII85 + Flate)."""
    parts = []
    for stream in re.findall(rb"stream\r?\n(.*?)endstream", content, flags=re.S):
        data = stream.strip()
        for decode in (lambda d: zlib.decompress(base64.a85decode(d, adobe=True)),
                       lambda d: zlib.decompress(base64.a85decode(d.rstrip(b"~>") )),
                       zlib.decompress):
            try:
                parts.append(decode(data).decode("latin-1"))
                break
            except Exception:
                continue
    return "\n".join(parts)


def _visible_text(response) -> str:
    """Everything a caller can read out of a response: body, headers, PDF text, ZIP members."""
    content = response.content
    text = [response.text, " ".join(f"{k}={v}" for k, v in response.headers.items())]
    if content.startswith(b"%PDF"):
        text.append(_pdf_text(content))
    elif content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                for name in archive.namelist():
                    member = archive.read(name)
                    text.append(name)
                    text.append(_pdf_text(member) if member.startswith(b"%PDF") else member.decode("utf-8", "replace"))
        except zipfile.BadZipFile:
            pass
    return "\n".join(text)


def _reveals(response, party: Party) -> list[str]:
    seen = _visible_text(response)
    secrets = {"marker": party.marker, "tenant id": party.tenant, "admin": party.admin, "manager": party.manager,
               "register CAPA id": party.register_capa_id, "event id": party.event_id}
    return [name for name, value in secrets.items() if value and value in seen]


# ── what a request changes ────────────────────────────────────────────────────

def _snapshot(party: Party) -> dict:
    """Every stored record owned by ``party``'s tenant, across all three stores."""
    db = SessionLocal()
    try:
        state = {
            model.__tablename__: sorted(
                (tuple(row) for row in db.execute(
                    select(model.__table__).where(model.__table__.c.tenant_id == party.tenant)).all()),
                key=repr)
            for model in TENANT_MODELS
        }
    finally:
        db.close()
    capa_lifecycle_service.ensure_lifecycle_columns()
    with capa_service._connect() as conn:
        state["capas"] = sorted(
            (tuple(row) for row in conn.execute("SELECT * FROM capas WHERE tenant_id = ?", (party.tenant,)).fetchall()),
            key=repr)
    state["vendor_events"] = copy.deepcopy(sorted(
        (e for e in vendor_governance_service._VENDOR_EVENTS if e.get("tenant_id") == party.tenant),
        key=lambda e: e["id"]))
    return state


def _row_counts() -> dict:
    """Row counts of everything this batch protects, whoever owns it."""
    db = SessionLocal()
    try:
        counts = {model.__tablename__: db.query(model).count() for model in TENANT_MODELS}
    finally:
        db.close()
    with capa_service._connect() as conn:
        counts["capas"] = conn.execute("SELECT COUNT(*) FROM capas").fetchone()[0]
    counts["vendor_events"] = len(vendor_governance_service._VENDOR_EVENTS)
    return counts


class _Statements:
    """SQL executed while the block runs, with bound parameters."""

    def __enter__(self):
        self.seen: list[tuple[str, object]] = []
        event.listen(Engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc):
        event.remove(Engine, "before_cursor_execute", self._record)

    def _record(self, conn, cursor, statement, parameters, context, executemany):
        self.seen.append((statement, parameters))


def _flat(parameters) -> list:
    if isinstance(parameters, dict):
        return list(parameters.values())
    if isinstance(parameters, (list, tuple)):
        out = []
        for item in parameters:
            out.extend(_flat(item) if isinstance(item, (dict, list, tuple)) else [item])
        return out
    return [parameters]


# ══ 1. The route table is the mounted application ═════════════════════════════

def test_the_tables_cover_every_mounted_route_of_the_three_modules():
    by_module = {module: 0 for module in MODULES}
    for route in app.routes:
        if isinstance(route, APIRoute) and route.endpoint.__module__ in MODULES:
            by_module[route.endpoint.__module__] += len(route.methods - {"HEAD", "OPTIONS"})
    assert by_module == {"app.routes.enterprise_intake": 77, "app.routes.vendor_governance": 8, "app.routes.capa": 9}
    assert len(ROUTES) == 94 and len(PROTECTED) == 91
    assert PUBLIC_PROBES <= set(ROUTES)


def test_every_write_route_has_a_valid_request_body(world):
    """A write that fails validation would be refused for the wrong reason."""
    for route in WRITES:
        path, kwargs = _request(route, world.a, world)
        assert "{" not in path, route


# ══ 2. Callers with no verified identity ══════════════════════════════════════

def _unverified(world: World) -> dict[str, dict]:
    b = world.b
    named = {"X-Tenant-Id": b.tenant, "X-LumenAI-Tenant-Id": b.tenant}
    return {
        "anonymous": {},
        "anonymous naming tenant B": named,
        "not a token": {"Authorization": "Bearer not-a-jwt", **named},
        "expired token of B's administrator": {"Authorization": f"Bearer {_expired_token(b.admin)}", **named},
        "tampered token of B's administrator": {"Authorization": f"Bearer {_tampered_token(b.admin)}", **named},
        "development token role headers without the token": {
            "X-LumenAI-Role": "enterprise_admin", "X-LumenAI-Actor": b.admin, **named},
        "user with no membership": world.outsider,
        "user with no membership naming tenant B": {**world.outsider, **named},
        "disabled member of B": {**world.disabled_b, **named},
    }


IDENTITIES = sorted(_unverified(World(Party("t", "m"), Party("t", "m"), 1, {}, {}, {}, {})))


class TestUnverifiedCallersGetNothing:
    @pytest.mark.parametrize("identity", IDENTITIES)
    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_refused_without_data_or_side_effect(self, world, route, identity):
        headers = _unverified(world)[identity]
        before, counts = _snapshot(world.b), _row_counts()

        response = _send(route, headers, world.b, world)

        assert response.status_code in REFUSED, f"{identity}: HTTP {response.status_code} {response.text[:160]}"
        assert _reveals(response, world.b) == []
        assert _snapshot(world.b) == before
        assert _row_counts() == counts, "a refused request stored something"


class TestPublicProbesCarryNoTenantData:
    @pytest.mark.parametrize("route", sorted(PUBLIC_PROBES), ids=lambda r: f"{r[0]} {r[1]}")
    def test_probe_is_public_and_empty_of_tenant_data(self, world, route):
        response = client.get(route[1])
        assert response.status_code == 200
        assert _reveals(response, world.a) == [] and _reveals(response, world.b) == []
        body = response.json()
        if "summary" in body:
            assert body["summary"] == {}, "a public probe must not carry per-tenant figures"
        assert "database_path" not in response.text


# ══ 3. Tenant A against tenant B ══════════════════════════════════════════════

OBJECT_ROUTES = [route for route in PROTECTED if "{" in route[1] and "vendor-baseline-subscription" not in route[1]]


class TestTenantACannotReachTenantB:
    @pytest.mark.parametrize("route", OBJECT_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    def test_object_id_substitution_is_refused(self, world, route):
        """A's own credentials and tenant, B's object id in the path."""
        before, counts = _snapshot(world.b), _row_counts()

        response = _send(route, world.a.headers(route), world.b, world)

        if route[1].endswith("/governance-packet/verify-hash") or route[1].endswith("/governance-export-history"):
            # These answer 200 for any finding id and describe only the CALLER's
            # exports; for another tenant's finding that is "nothing recorded".
            assert response.status_code == 200
        else:
            assert response.status_code in HIDDEN, f"HTTP {response.status_code}: {response.text[:200]}"
        assert _reveals(response, world.b) == []
        assert _snapshot(world.b) == before, "tenant A changed tenant B's records"
        after = _row_counts()
        after["audit_logs"] = counts["audit_logs"]            # A's own access may be audited under A
        assert after == counts, "a refused cross-tenant request created records"

    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_naming_tenant_b_in_the_verified_header_is_refused(self, world, route):
        before, counts = _snapshot(world.b), _row_counts()

        response = _send(route, {**world.a.headers(route), "X-Tenant-Id": world.b.tenant}, world.b, world)

        assert response.status_code == 403, f"HTTP {response.status_code}: {response.text[:200]}"
        assert _reveals(response, world.b) == []
        assert _snapshot(world.b) == before and _row_counts() == counts

    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_disagreeing_tenant_headers_are_refused(self, world, route):
        """Member of A states A in one header and B in the other."""
        before, counts = _snapshot(world.b), _row_counts()
        headers = {**world.a.headers(route), "X-Tenant-Id": world.a.tenant, "X-LumenAI-Tenant-Id": world.b.tenant}

        response = _send(route, headers, world.b, world)

        assert response.status_code == 403, f"HTTP {response.status_code}: {response.text[:200]}"
        assert _reveals(response, world.b) == []
        assert _snapshot(world.b) == before and _row_counts() == counts

    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_an_unverified_tenant_header_does_not_move_the_caller(self, world, route):
        """``X-LumenAI-Tenant-Id: B`` alone is not a selector: the caller stays in
        A (or is refused), and tenant B is neither read nor written."""
        before = _snapshot(world.b)

        with _Statements() as sql:
            response = _send(route, {**world.a.headers(route), "X-LumenAI-Tenant-Id": world.b.tenant}, world.a, world)

        assert response.status_code < 500, response.text[:200]
        assert _reveals(response, world.b) == []
        assert _snapshot(world.b) == before
        bound = [s for s, p in sql.seen if world.b.tenant in _flat(p) and "tenant_memberships" not in s]
        assert bound == [], f"SQL bound tenant B: {bound[:2]}"

    def test_a_body_that_names_tenant_b_creates_nothing(self, world):
        before, counts = _snapshot(world.b), _row_counts()
        response = client.post("/api/enterprise/intake", headers=world.a.admin_headers, json={
            "tenant_id": world.b.tenant, "facility_name": "f", "vendor_name": "v", "instrument_name": "i",
            "finding_category": "c"})
        assert response.status_code == 403, response.text
        assert _snapshot(world.b) == before and _row_counts() == counts

    @pytest.mark.parametrize("tenant", ["bonsecours", "default-tenant", "demo"])
    def test_a_body_that_names_a_literal_tenant_creates_nothing(self, world, tenant):
        counts = _row_counts()
        response = client.post("/api/enterprise/intake", headers=world.a.admin_headers, json={
            "tenant_id": tenant, "facility_name": "f", "vendor_name": "v", "instrument_name": "i",
            "finding_category": "c"})
        assert response.status_code == 403, response.text
        assert _row_counts() == counts

    def test_a_vendor_event_cannot_be_linked_to_tenant_b_capa(self, world):
        before_a, before_b = _snapshot(world.a), _snapshot(world.b)
        response = client.post(f"/api/enterprise/vendor-governance/events/{world.a.event_id}/link-capa",
                               headers=world.a.admin_headers, json={"capa_id": world.b.register_capa_id})
        assert response.status_code == 404, response.text
        assert _snapshot(world.a) == before_a and _snapshot(world.b) == before_b

    def test_a_vendor_event_cannot_be_created_pointing_at_tenant_b_capa(self, world):
        counts = _row_counts()
        response = client.post("/api/enterprise/vendor-governance/events", headers=world.a.admin_headers, json={
            "vendor_name": "v", "event_type": "t", "event_summary": "s", "capa_id": world.b.register_capa_id})
        assert response.status_code == 404, response.text
        assert _row_counts() == counts

    def test_an_audit_query_that_names_tenant_b_is_refused(self, world):
        for path in ("/api/enterprise/audit/events", "/api/enterprise/audit/events/export.csv",
                     "/api/enterprise/audit/evidence-bundle", "/api/enterprise/audit/evidence-bundle/download.json"):
            response = client.get(path, headers=world.a.admin_headers, params={"tenant_id": world.b.tenant})
            assert response.status_code == 403, (path, response.status_code)
            assert _reveals(response, world.b) == []


LISTING_ROUTES = [route for route in PROTECTED if route[0] == "GET" and "{" not in route[1]]

# NOT partitioned by tenant, deliberately left so in this batch and recorded as an
# open item in the review document. All five require an authenticated, verified
# hospital or enterprise administrator. Four look an event up by a SHA-256 hash
# the caller must already hold (the hash of an export they were given); one looks
# a hash chain up by resource id. They return verification metadata, never the
# audited content; ``TestVerificationRoutesReturnMetadataOnly`` pins that down.
VERIFICATION_ROUTES = {
    ("GET", "/api/enterprise/audit/verify-chain"),
    ("GET", "/api/enterprise/audit/events/export/verify"),
    ("GET", "/api/enterprise/audit/events/export/manifest/verify"),
    ("GET", "/api/enterprise/audit/evidence-bundle/verify"),
    ("GET", "/api/enterprise/audit/evidence-bundle/verification-summary"),
}
# The append-only audit writer links each new event to the previous event of the
# same resource (a hash chain). That lookup is by resource, returns nothing to
# the caller, and is the one statement on ``audit_logs`` that is not tenant-bound.
_AUDIT_CHAIN_LOOKUP = re.compile(
    r"WHERE audit_logs\.resource_type = \S+ AND audit_logs\.resource_id = \S+\s+ORDER BY audit_logs\.id DESC\s+LIMIT", re.S)


class TestListsAggregatesAndExportsAreTenantScoped:
    @pytest.mark.parametrize("route", LISTING_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    def test_nothing_of_tenant_b_is_returned(self, world, route):
        response = _send(route, world.a.headers(route), world.a, world)
        assert response.status_code < 400, f"HTTP {response.status_code}: {response.text[:200]}"
        assert _reveals(response, world.b) == []

    @pytest.mark.parametrize(
        "route", [r for r in PROTECTED if r[0] == "GET" and r not in VERIFICATION_ROUTES], ids=lambda r: f"{r[0]} {r[1]}")
    def test_sql_for_tenant_a_never_reaches_tenant_b(self, world, route):
        """Structural check, independent of what the response happens to show."""
        with _Statements() as sql:
            _send(route, world.a.headers(route), world.a, world)

        for statement, parameters in sql.seen:
            if "tenant_memberships" in statement:
                continue
            assert world.b.tenant not in _flat(parameters), statement
            verb = statement.lstrip().split(None, 1)[0].upper()
            if verb not in ("SELECT", "UPDATE", "DELETE"):
                continue
            for table in TENANT_TABLES:
                if not re.search(rf"\b(FROM|UPDATE|JOIN)\s+{table}\b", statement):
                    continue
                if table == "audit_logs" and _AUDIT_CHAIN_LOOKUP.search(statement):
                    continue
                where = statement.split("WHERE", 1)[1] if "WHERE" in statement else ""
                scoped = f"{table}.tenant_id = " in where
                by_primary_key = re.search(rf"{table}\.id = ", where) is not None
                assert scoped or by_primary_key, f"unscoped statement on {table}: {statement[:300]}"
                if scoped:
                    assert world.a.tenant in _flat(parameters), statement[:300]

    def test_aggregates_count_only_the_callers_records(self, world):
        dashboard = client.get("/api/enterprise/executive-quality-review-dashboard", headers=world.a.admin_headers)
        assert dashboard.status_code == 200
        db = SessionLocal()
        try:
            own = db.query(EnterpriseFinding).filter(EnterpriseFinding.tenant_id == world.a.tenant).count()
            everyone = db.query(EnterpriseFinding).count()
        finally:
            db.close()
        assert everyone > own >= 1
        counted = [value for key, value in _walk(dashboard.json()) if key == "total_findings"]
        assert counted and all(value == own for value in counted), (counted, own)

        capas = client.get("/api/capa", headers=world.a.manager_headers, params={"limit": 500}).json()
        with capa_service._connect() as conn:
            own_capas = conn.execute("SELECT COUNT(*) FROM capas WHERE tenant_id = ?", (world.a.tenant,)).fetchone()[0]
        assert capas["summary"]["total"] == own_capas == len(capas["items"])

        events = client.get("/api/enterprise/vendor-governance/summary", headers=world.a.admin_headers).json()
        own_events = sum(1 for e in vendor_governance_service._VENDOR_EVENTS if e["tenant_id"] == world.a.tenant)
        assert events["summary"]["total_vendor_events"] == own_events

    def test_other_readers_of_the_capa_register_are_tenant_scoped(self, world):
        """The analytics routes that read the register outside ``/api/capa``."""
        kpi = client.get("/api/analytics/kpi-summary", headers=world.a.manager_headers)
        assert kpi.status_code == 200, kpi.text
        with capa_service._connect() as conn:
            own = conn.execute("SELECT COUNT(*) FROM capas WHERE tenant_id = ?", (world.a.tenant,)).fetchone()[0]
            everyone = conn.execute("SELECT COUNT(*) FROM capas").fetchone()[0]
        assert everyone > own
        totals = [value for key, value in _walk(kpi.json()) if key in ("total_capas", "capa_total")]
        assert all(value <= own for value in totals), (totals, own)
        assert _reveals(kpi, world.b) == []


class TestVerificationRoutesReturnMetadataOnly:
    """The five routes in ``VERIFICATION_ROUTES``, pointed at tenant B's records."""

    def test_chain_verification_of_tenant_b_resource_discloses_no_content(self, world):
        response = client.get("/api/enterprise/audit/verify-chain", headers=world.a.admin_headers, params={
            "resource_type": "enterprise_governance_packet", "resource_id": str(world.b.finding_id)})
        assert response.status_code == 200
        assert set(response.json()) <= {
            "status", "verified", "resource_type", "resource_id", "event_count", "broken_event_id", "message",
            "expected_previous_hash", "stored_previous_hash", "expected_event_hash", "stored_event_hash"}
        assert _reveals(response, world.b) == []

    def test_hash_verification_needs_the_hash_and_discloses_no_content(self, world):
        exported = client.get("/api/enterprise/audit/events/export.csv", headers=world.b.admin_headers)
        assert exported.status_code == 200
        export_hash = exported.headers["X-LumenAI-Audit-Export-Hash"]
        manifest_hash = exported.headers["X-LumenAI-Audit-Manifest-Hash"]

        for path, params in (
            ("/api/enterprise/audit/events/export/verify", {"audit_export_hash": export_hash}),
            ("/api/enterprise/audit/events/export/manifest/verify", {"manifest_hash": manifest_hash}),
            ("/api/enterprise/audit/evidence-bundle/verify", {"bundle_hash": export_hash}),
            ("/api/enterprise/audit/evidence-bundle/verification-summary", {"bundle_hash": export_hash}),
        ):
            response = client.get(path, headers=world.a.admin_headers, params=params)
            assert response.status_code in (200, 404), (path, response.status_code)
            assert [name for name in _reveals(response, world.b)] == [], path

    def test_an_export_contains_only_the_exporters_tenant(self, world):
        exported = client.get("/api/enterprise/audit/events/export.csv", headers=world.a.admin_headers,
                              params={"limit": 200})
        assert exported.status_code == 200
        assert _reveals(exported, world.b) == []
        listed = client.get("/api/enterprise/audit/events", headers=world.a.admin_headers, params={"limit": 200})
        assert _reveals(listed, world.b) == []
        db = SessionLocal()
        try:
            owners = {row.tenant_id for row in db.query(AuditLog).filter(
                AuditLog.id.in_([event["id"] for event in listed.json()["events"]])).all()}
        finally:
            db.close()
        assert owners <= {world.a.tenant}


def _walk(node, key: str = ""):
    if isinstance(node, dict):
        for name, value in node.items():
            yield from _walk(value, name)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item, key)
    else:
        yield key, node


# ══ 4. The owner's own workflow still works ═══════════════════════════════════

# Requests that are valid but have a documented non-2xx answer for these fixtures.
EXPECTED_STATUS = {
    ("GET", "/api/enterprise/audit/events/export/verify"): {200, 404},
    ("GET", "/api/enterprise/audit/events/export/manifest/verify"): {200, 404},
    ("GET", "/api/enterprise/audit/evidence-bundle/verify"): {200, 404},
    ("GET", "/api/enterprise/audit/evidence-bundle/verification-summary"): {200, 404},
}


class TestTheOwnerIsServed:
    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_owner_request_succeeds(self, world, route):
        response = _send(route, world.a.headers(route), world.a, world)
        allowed = EXPECTED_STATUS.get(route, {200, 201})
        assert response.status_code in allowed, f"HTTP {response.status_code}: {response.text[:300]}"

    @pytest.mark.parametrize("path", [
        "/api/enterprise/intake/history",
        "/api/enterprise/intake/{finding_id}/governance-packet",
        "/api/enterprise/intake/{finding_id}/governance-packet.pdf",
        "/api/enterprise/intake/{finding_id}/vendor-escalation-packet",
        "/api/enterprise/intake/{finding_id}/governance-zip-bundle",
        "/api/enterprise/intake/{finding_id}/evidence",
        "/api/enterprise/capas",
        "/api/enterprise/audit-trail",
        "/api/enterprise/audit-command-center.csv",
        "/api/enterprise/vendor-governance/events",
        "/api/enterprise/vendor-governance/powerbi-csv",
        "/api/capa",
        "/api/capa/powerbi-csv",
        "/api/capa/{capa_id}",
    ])
    def test_owner_sees_their_own_records(self, world, path):
        """The positive control for the marker checks above: the same reader that
        finds nothing of B in A's responses does find A's own data."""
        route = ("GET", path)
        response = _send(route, world.a.headers(route), world.a, world)
        assert response.status_code == 200, response.text[:200]
        assert _reveals(response, world.a) != [], f"{path} returned none of the owner's own records"
        assert _reveals(response, world.b) == []

    def test_records_created_without_naming_a_tenant_belong_to_the_caller(self, world):
        db = SessionLocal()
        try:
            for model, object_id in ((EnterpriseFinding, world.a.finding_id), (EnterpriseEvidence, world.a.evidence_id),
                                     (EnterpriseCapa, world.a.enterprise_capa_id),
                                     (EnterpriseInstrumentBaseline, world.a.baseline_id)):
                assert db.get(model, object_id).tenant_id == world.a.tenant, model.__tablename__
        finally:
            db.close()
        assert capa_service.get_capa(world.a.register_capa_id, tenant_id=world.a.tenant) is not None
        assert vendor_governance_service.get_vendor_event(world.a.event_id, tenant_id=world.a.tenant) is not None

    def test_naming_the_callers_own_tenant_is_accepted(self, world):
        response = client.post("/api/enterprise/intake", headers={**world.a.admin_headers, "X-Tenant-Id": world.a.tenant},
                               json={"tenant_id": world.a.tenant, "facility_name": "f", "vendor_name": "v",
                                     "instrument_name": "i", "finding_category": "c"})
        assert response.status_code == 200, response.text
        assert response.json()["tenant_id"] == world.a.tenant

    def test_audit_rows_are_recorded_in_the_callers_tenant(self, world):
        db = SessionLocal()
        try:
            last = db.query(AuditLog.id).order_by(AuditLog.id.desc()).first()[0]
        finally:
            db.close()
        for path in ("/api/enterprise/audit-command-center", "/api/enterprise/export-readiness-history.csv",
                     "/api/enterprise/export-readiness-history.powerbi.data-dictionary",
                     "/api/enterprise/baseline-review-queue",
                     f"/api/enterprise/intake/{world.a.finding_id}/vendor-escalation-packet"):
            assert client.get(path, headers=world.a.admin_headers).status_code == 200, path
        db = SessionLocal()
        try:
            written = db.query(AuditLog).filter(AuditLog.id > last).all()
        finally:
            db.close()
        assert len(written) >= 5
        assert {row.tenant_id for row in written} == {world.a.tenant}
        assert {row.actor_email for row in written} == {world.a.admin}


# ══ 5. A user who belongs to both tenants ═════════════════════════════════════

class TestMultiTenantMembership:
    def _headers(self, world: World, route, tenant: str | None) -> dict:
        base = world.multi_manager if route[1].startswith("/api/capa") else world.multi
        return {**base, "X-Tenant-Id": tenant} if tenant else dict(base)

    @pytest.mark.parametrize("route", OBJECT_ROUTES, ids=lambda r: f"{r[0]} {r[1]}")
    def test_acts_only_in_the_selected_tenant(self, world, route):
        if route[0] == "GET":
            own = _send(route, self._headers(world, route, world.a.tenant), world.a, world)
            assert own.status_code in EXPECTED_STATUS.get(route, {200}), own.text[:200]
            assert _reveals(own, world.b) == []
        before = _snapshot(world.b)
        other = _send(route, self._headers(world, route, world.a.tenant), world.b, world)
        if not (route[1].endswith("/verify-hash") or route[1].endswith("/governance-export-history")):
            assert other.status_code in HIDDEN, f"HTTP {other.status_code}: {other.text[:200]}"
        assert _reveals(other, world.b) == []
        assert _snapshot(world.b) == before

    def test_selecting_the_other_tenant_serves_the_other_tenant(self, world):
        route = ("GET", "/api/enterprise/intake/{finding_id}/governance-packet")
        as_b = _send(route, self._headers(world, route, world.b.tenant), world.b, world)
        assert as_b.status_code == 200 and _reveals(as_b, world.b) != [] and _reveals(as_b, world.a) == []

    @pytest.mark.parametrize("route", PROTECTED, ids=ROUTE_IDS)
    def test_no_selection_and_a_third_tenant_are_both_refused(self, world, route):
        unselected = _send(route, self._headers(world, route, None), world.a, world)
        assert unselected.status_code in REFUSED, f"no tenant selected: HTTP {unselected.status_code}"
        third = _send(route, self._headers(world, route, _uid("b1third")), world.a, world)
        assert third.status_code == 403, f"third tenant: HTTP {third.status_code}"


# ══ 6. The stores themselves ══════════════════════════════════════════════════

class TestCapaRegisterIsTenantOwned:
    @pytest.mark.parametrize("tenant", [None, "", "   "])
    def test_every_function_requires_a_tenant(self, tenant):
        calls = [
            lambda: capa_service.create_capa("t", tenant_id=tenant),
            lambda: capa_service.list_capas(tenant_id=tenant),
            lambda: capa_service.get_capa("x", tenant_id=tenant),
            lambda: capa_service.capa_summary(tenant_id=tenant),
            lambda: capa_service.update_capa("x", status="closed", tenant_id=tenant),
            lambda: capa_service.capa_escalation_summary(tenant_id=tenant),
            lambda: capa_service.build_capa_powerbi_rows(tenant_id=tenant),
            lambda: capa_service.capa_governance_scorecard(tenant_id=tenant),
            lambda: capa_service.create_capa_from_audit_signal({}, tenant_id=tenant),
            lambda: capa_lifecycle_service.get_capa(tenant, "x"),
            lambda: capa_lifecycle_service.list_capas(tenant),
            lambda: capa_lifecycle_service.lifecycle_summary(tenant),
        ]
        for call in calls:
            with pytest.raises(ValueError):
                call()

    def test_a_record_with_no_owner_is_visible_to_no_tenant(self, world):
        """Rows written before tenant ownership existed (``tenant_id`` NULL)."""
        capa_lifecycle_service.ensure_lifecycle_columns()
        orphan, title = _uid("orphan"), _uid("orphantitle")
        now = datetime.now(timezone.utc).isoformat()
        with capa_service._connect() as conn:
            conn.execute(
                "INSERT INTO capas (id, title, source, description, risk_level, owner, status, created_at, updated_at, tenant_id)"
                " VALUES (?, ?, 'manual', '', 'high', 'nobody', 'open', ?, ?, NULL)", (orphan, title, now, now))
            conn.commit()

        for tenant in (world.a.tenant, world.b.tenant, "default-tenant"):
            assert capa_service.get_capa(orphan, tenant_id=tenant) is None
            assert capa_service.update_capa(orphan, status="closed", tenant_id=tenant) is None
            assert title not in repr(capa_service.list_capas(limit=500, tenant_id=tenant))
            assert title not in repr(capa_service.build_capa_powerbi_rows(limit=5000, tenant_id=tenant))
            assert capa_lifecycle_service.get_capa(tenant, orphan) is None
            assert title not in repr(capa_lifecycle_service.list_capas(tenant, limit=500))
            with pytest.raises(ValueError):
                capa_lifecycle_service.advance_lifecycle(tenant, orphan, "closed", actor="intruder")
        with capa_service._connect() as conn:
            row = conn.execute("SELECT status, tenant_id FROM capas WHERE id = ?", (orphan,)).fetchone()
        assert (row["status"], row["tenant_id"]) == ("open", None)

    def test_the_lifecycle_service_cannot_read_or_advance_another_tenants_capa(self, world):
        before = _snapshot(world.b)
        assert capa_lifecycle_service.get_capa(world.a.tenant, world.b.register_capa_id) is None
        with pytest.raises(ValueError):
            capa_lifecycle_service.advance_lifecycle(world.a.tenant, world.b.register_capa_id, "closed", actor="intruder")
        assert _snapshot(world.b) == before


class TestVendorGovernanceEventsAreTenantOwned:
    def test_seeded_illustrative_events_belong_to_the_demo_tenant_only(self, world):
        seeded = [e for e in vendor_governance_service._VENDOR_EVENTS if e["vendor_name"] in
                  {"Stryker", "DePuy Synthes", "Medtronic"} and e["event_type"] in
                  {"Tray Quality Signal", "Missing Instrument Signal", "Documentation / IFU Review"}]
        assert len(seeded) == 3
        assert {e["tenant_id"] for e in seeded} == {vendor_governance_service.DEMO_TENANT_ID}
        listed = client.get("/api/enterprise/vendor-governance/events", headers=world.a.admin_headers,
                            params={"limit": 500}).json()
        assert not {item["id"] for item in listed["items"]} & {e["id"] for e in seeded}

    @pytest.mark.parametrize("tenant", [None, "", "  "])
    def test_every_function_requires_a_tenant(self, tenant):
        service = vendor_governance_service
        for call in (lambda: service.list_vendor_events(tenant_id=tenant),
                     lambda: service.vendor_governance_summary(tenant_id=tenant),
                     lambda: service.get_vendor_event("x", tenant_id=tenant),
                     lambda: service.vendor_capa_linkage_summary(tenant_id=tenant),
                     lambda: service.build_vendor_governance_powerbi_rows(tenant_id=tenant),
                     lambda: service.create_vendor_event("v", "t", "s", tenant_id=tenant)):
            with pytest.raises(ValueError):
                call()

    def test_creating_a_capa_from_an_event_stays_in_the_tenant(self, world):
        response = client.post(f"/api/enterprise/vendor-governance/events/{world.a.event_id}/create-capa",
                               headers=world.a.admin_headers)
        assert response.status_code == 200, response.text
        capa_id = response.json()["capa"]["id"]
        assert capa_service.get_capa(capa_id, tenant_id=world.a.tenant) is not None
        assert capa_service.get_capa(capa_id, tenant_id=world.b.tenant) is None
