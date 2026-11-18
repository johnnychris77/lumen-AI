"""P472-03 — cross-tenant authorization on the regulatory, predictions,
benchmarks and vendor-intelligence API routes.

Before P472-03 these routes authenticated the caller for their own tenant and
then served or wrote whichever ``tenant_id`` the request named. The rule now:

* the tenant a request acts in is the tenant of its verified auth context;
* a ``tenant_id`` in the query string or body is only a claim — if it names any
  other tenant the request is refused (403); it is never rewritten;
* a request that names no tenant acts in the caller's verified tenant;
* a user who belongs to several tenants selects one with ``X-Tenant-Id``, which
  the auth layer verifies against membership.

EVERY route of the four modules is in the table below, and the table is checked
against the mounted application, so a new route cannot be added without a row.

Everything is synthetic: canned provider outputs, constant digests, test users.
"""
# ruff: noqa: F811 - pytest fixtures imported from the baseline module are requested by name
from __future__ import annotations

import ast
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from fastapi.routing import APIRoute
from test_p472_cross_tenant_api import (  # noqa: F401 - fixtures are used by name
    REFUSED,
    Party,
    World,
    _add_membership,
    _analyze,
    _bearer,
    _environment,
    _party,
    _uid,
    _unverified_identities,
    client,
    world,
)

from app.auth.context import AuthContext
from app.auth.tenant_scope import TENANT_DENIED_DETAIL, authorized_tenant
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.benchmarking import (
    BenchmarkTrendPoint,
    BoardReport,
    EnterpriseRollup,
    HospitalBenchmark,
    VendorBenchmark,
)
from app.models.cv_inference import CVInferenceProvenance, CVInferenceRecord
from app.models.predictions import PredictionOutcome
from app.models.regulatory import FDASubmissionTracker, RegulatoryAuditPackage

ROUTE_GROUPS = (
    "/api/regulatory", "/api/predictions", "/api/enterprise/benchmarks", "/api/vendor-intelligence",
)
PERIOD = "2026-11"


# ── the endpoint table ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Endpoint:
    method: str
    template: str                 # the route as mounted
    claim: str                    # where the route reads a client tenant: query | body | none
    path: str = ""                # a concrete path, when the template has parameters
    params: tuple = ()            # other query parameters the request needs
    body: tuple = ()              # JSON fields the request needs (without tenant_id)

    @property
    def id(self) -> str:
        return f"{self.method} {self.template}"

    @property
    def url(self) -> str:
        return self.path or self.template


_PACKAGE = (("package_type", "joint_commission"), ("period_label", PERIOD), ("generated_by", "p472-03-test"))
_OUTCOME = (
    ("instrument_name", "synthetic-instrument"), ("prediction_date", "2026-11-01T00:00:00"),
    ("predicted_risk_category", "low"), ("actual_outcome", "no_event"), ("recorded_by", "p472-03-test"),
)
_FDA = (("device_name", "synthetic-device"), ("manufacturer", "synthetic-manufacturer"))
_PERIOD_BODY = (("period", {"period_type": "monthly", "period_label": PERIOD}),)

R, P, B, V = ROUTE_GROUPS
ENDPOINTS = [
    # Regulatory
    Endpoint("GET", f"{R}/readiness", "query"),
    Endpoint("GET", f"{R}/readiness/findings", "query"),
    Endpoint("GET", f"{R}/standards", "none"),
    Endpoint("GET", f"{R}/standards/mapping", "none", params=(("finding_category", "blood"),)),
    Endpoint("POST", f"{R}/audit-package", "body", body=_PACKAGE),
    Endpoint("POST", f"{R}/audit-package/pdf", "body", body=_PACKAGE),
    Endpoint("GET", f"{R}/audit-packages", "query"),
    Endpoint("GET", f"{R}/fda-submissions", "query"),
    Endpoint("POST", f"{R}/fda-submissions", "body", body=_FDA),
    Endpoint("GET", f"{R}/dashboard", "query"),
    # Predictions
    Endpoint("GET", f"{P}/failures", "query"),
    Endpoint("GET", f"{P}/failures/{{instrument_id}}", "query", path=f"{P}/failures/synthetic-instrument"),
    Endpoint("GET", f"{P}/contamination", "query"),
    Endpoint("GET", f"{P}/contamination/{{instrument_id}}", "query", path=f"{P}/contamination/synthetic-instrument"),
    Endpoint("GET", f"{P}/repairs", "query"),
    Endpoint("GET", f"{P}/repairs/{{instrument_id}}", "query", path=f"{P}/repairs/synthetic-instrument"),
    Endpoint("GET", f"{P}/recall-risk", "query"),
    Endpoint("GET", f"{P}/recall-risk/{{instrument_category}}", "query", path=f"{P}/recall-risk/endoscope"),
    Endpoint("GET", f"{P}/tray-risk", "query", params=(("tray_id", "default-tray"),)),
    Endpoint("GET", f"{P}/dashboard", "query"),
    Endpoint("POST", f"{P}/outcomes", "body", body=_OUTCOME),
    Endpoint("GET", f"{P}/accuracy", "query"),
    # Benchmarks
    Endpoint("POST", f"{B}/hospitals", "body", body=_PERIOD_BODY),
    Endpoint("GET", f"{B}/hospitals/{{hospital_id}}", "query", path=f"{B}/hospitals/synthetic-hospital"),
    Endpoint("GET", f"{B}/hospitals", "query"),
    Endpoint("POST", f"{B}/vendors", "body", body=_PERIOD_BODY),
    Endpoint("GET", f"{B}/vendors", "query"),
    Endpoint("POST", f"{B}/rollup", "body", body=_PERIOD_BODY),
    Endpoint("GET", f"{B}/rollup", "query"),
    Endpoint("GET", f"{B}/executive-dashboard", "query"),
    Endpoint("GET", f"{B}/trends/{{subject_type}}/{{subject_id}}/{{metric_name}}", "query",
             path=f"{B}/trends/hospital/synthetic-hospital/avg_cleanliness_score"),
    Endpoint("POST", f"{B}/reports/generate", "body", body=(("report_type", "monthly"), ("period_label", PERIOD))),
    Endpoint("GET", f"{B}/reports/{{report_type}}", "query", path=f"{B}/reports/monthly"),
    Endpoint("GET", f"{B}/reports/{{report_type}}/{{period_label}}", "query", path=f"{B}/reports/monthly/{PERIOD}"),
    Endpoint("GET", f"{B}/kpi-summary", "query"),
    # Vendor intelligence
    Endpoint("GET", f"{V}/vendors", "query"),
    Endpoint("GET", f"{V}/vendors/{{vendor_id}}", "query", path=f"{V}/vendors/olympus"),
    Endpoint("GET", f"{V}/vendors/{{vendor_id}}/scorecard", "query", path=f"{V}/vendors/olympus/scorecard"),
    Endpoint("GET", f"{V}/vendors/{{vendor_id}}/trends", "query", path=f"{V}/vendors/olympus/trends"),
]
TENANT_SCOPED = [ep for ep in ENDPOINTS if ep.claim != "none"]
BODY_ENDPOINTS = [ep for ep in ENDPOINTS if ep.claim == "body"]
READ_ENDPOINTS = [ep for ep in TENANT_SCOPED if ep.method == "GET"]
by_id = lambda eps: [ep.id for ep in eps]  # noqa: E731 - parametrize ids


def _send(ep: Endpoint, headers: dict, *, claim: str | None = None, via: str | None = None):
    """Send ``ep``. ``claim`` is a tenant id the client asserts through ``via``
    (default: the channel the route reads)."""
    params = dict(ep.params)
    body = dict(ep.body) if ep.method == "POST" else None
    if claim is not None:
        channel = via or ep.claim
        if channel == "query":
            params["tenant_id"] = claim
        elif channel == "body" and body is not None:
            body["tenant_id"] = claim
    return client.request(ep.method, ep.url, headers=headers, params=params or None, json=body)


# ── tenant row census ─────────────────────────────────────────────────────────

_CENSUS_MODELS = (
    AuditLog, BoardReport, HospitalBenchmark, VendorBenchmark, EnterpriseRollup, BenchmarkTrendPoint,
    RegulatoryAuditPackage, FDASubmissionTracker, PredictionOutcome, CVInferenceRecord, CVInferenceProvenance,
)


def _census(tenant: str) -> dict[str, int]:
    """Row counts for ``tenant`` in every table these routes can write."""
    db = SessionLocal()
    try:
        return {m.__tablename__: db.query(m).filter(m.tenant_id == tenant).count() for m in _CENSUS_MODELS}
    finally:
        db.close()


def _full_census(tenant: str) -> dict[str, int]:
    """Row counts for ``tenant`` in EVERY table that has a ``tenant_id`` column."""
    existing = set(sa.inspect(engine).get_table_names())
    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name in existing and "tenant_id" in table.c:
                counts[table.name] = conn.execute(
                    sa.select(sa.func.count()).select_from(table).where(table.c.tenant_id == tenant)
                ).scalar_one()
    return {name: count for name, count in counts.items() if count}


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def pair() -> World:
    """Two tenants with one verified member each (no inference data), plus a user
    with no membership and a disabled member of B. Tenant B already owns one row
    of each kind these routes write, created by B itself through the API."""
    a, b = _party("a"), _party("b")
    for path, body in ((f"{P}/outcomes", dict(_OUTCOME)), (f"{R}/fda-submissions", dict(_FDA))):
        assert client.post(path, json=body, headers=b.headers).status_code == 200
    disabled_user = f"{_uid('p47203-disabled')}@example.com"
    _add_membership(b.tenant, disabled_user, enabled=False)
    return World(a=a, b=b, outsider=_bearer(f"{_uid('p47203-outsider')}@example.com"),
                 disabled_b=_bearer(disabled_user))


def _assert_no_trace(response, *parties: Party) -> None:
    for party in parties:
        assert party.tenant.encode() not in response.content
        assert party.user.encode() not in response.content


# ══ 0. Inventory ══════════════════════════════════════════════════════════════

class TestRouteInventory:
    def test_the_table_is_every_mounted_route_of_the_four_modules(self):
        mounted = sorted(
            (method, route.path)
            for route in app.routes
            if isinstance(route, APIRoute) and route.path.startswith(ROUTE_GROUPS)
            for method in route.methods - {"HEAD", "OPTIONS"}
        )
        assert mounted == sorted((ep.method, ep.template) for ep in ENDPOINTS)
        assert len(ENDPOINTS) == 39 and len(TENANT_SCOPED) == 37

    def test_every_handler_that_can_name_a_tenant_resolves_it_through_the_shared_helper(self):
        """Static guard: a handler in these modules that accepts a tenant (query
        parameter or request body) must call ``authorized_tenant`` on the verified
        auth context, and may use a client tenant nowhere else."""
        routes_dir = Path(__file__).resolve().parents[1] / "app" / "routes"
        checked = 0
        for module in ("regulatory", "predictions", "benchmarking", "vendor_intelligence"):
            source = (routes_dir / f"{module}.py").read_text(encoding="utf-8")
            for node in ast.walk(ast.parse(source)):
                if not isinstance(node, ast.FunctionDef) or not any(
                    isinstance(d, ast.Call) and getattr(d.func, "value", None) is not None
                    and getattr(d.func.value, "id", "") == "router" for d in node.decorator_list
                ):
                    continue
                segment = ast.get_source_segment(source, node)
                args = node.args.args + node.args.kwonlyargs
                # A request-body model is an argument annotated with a schema class
                # (``AuditPackageRequest``, ``FDASubmissionCreate``, ...).
                takes_body = any(
                    isinstance(a.annotation, ast.Name)
                    and a.annotation.id.endswith(("Request", "Create")) and a.annotation.id != "Request"
                    for a in args
                )
                takes_tenant = takes_body or any(a.arg == "tenant_id" for a in args)
                if not takes_tenant:
                    assert "tenant_id" not in segment, f"{module}.{node.name}"
                    continue
                checked += 1
                assert "authorized_tenant(" in segment, f"{module}.{node.name} does not scope its tenant"
                assert "require_enterprise_auth(request, db=db)" in segment, f"{module}.{node.name}"
                # A client-supplied tenant may appear only as an argument to the helper.
                for line in segment.splitlines():
                    if re.search(r"\b(body|req)\.tenant_id\b", line):
                        assert "authorized_tenant(" in line, f"{module}.{node.name}: {line.strip()}"
            assert "demo-tenant" not in source and "default-tenant" not in source, module
        assert checked == 37


# ══ 1. Valid same-tenant access ═══════════════════════════════════════════════

class TestValidSameTenantAccess:
    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    @pytest.mark.parametrize("how", ["no tenant named", "own tenant claimed", "own tenant in header and claim"])
    def test_the_owner_is_served(self, pair, ep, how):
        a, b = pair.a, pair.b
        headers = {**a.headers, "X-Tenant-Id": a.tenant} if "header" in how else a.headers
        claim = None if how == "no tenant named" else a.tenant

        response = _send(ep, headers, claim=claim)

        assert response.status_code == 200, (ep.id, how, response.status_code, response.text[:300])
        _assert_no_trace(response, b)

    @pytest.mark.parametrize("ep", [ep for ep in ENDPOINTS if ep.claim == "none"],
                             ids=by_id([ep for ep in ENDPOINTS if ep.claim == "none"]))
    def test_the_static_catalogue_routes_need_authentication_only(self, pair, ep):
        assert _send(ep, pair.a.headers).status_code == 200
        assert _send(ep, {}).status_code in REFUSED

    @pytest.mark.parametrize("ep", [ep for ep in TENANT_SCOPED if ep.template in (
        f"{B}/rollup", f"{B}/executive-dashboard", f"{P}/failures", f"{P}/accuracy", f"{V}/vendors",
        f"{R}/readiness", f"{R}/dashboard")], ids=lambda ep: ep.id)
    def test_a_request_that_names_no_tenant_acts_in_the_callers_tenant(self, pair, ep):
        """Where the response states its tenant, it is the caller's — the old
        ``demo-tenant`` default is gone."""
        a = pair.a
        response = _send(ep, a.headers)
        assert response.status_code == 200
        assert a.tenant.encode() in response.content
        assert b"demo-tenant" not in response.content and b"default-tenant" not in response.content


# ══ 2. Tenant A cannot read or write tenant B ═════════════════════════════════

ATTACKS = {
    "names B in the request": lambda a, b: (a.headers, b.tenant),
    "names B in X-Tenant-Id": lambda a, b: ({**a.headers, "X-Tenant-Id": b.tenant}, None),
    "names B in header and request": lambda a, b: ({**a.headers, "X-Tenant-Id": b.tenant}, b.tenant),
    "own tenant in header, B in the request": lambda a, b: ({**a.headers, "X-Tenant-Id": a.tenant}, b.tenant),
    "both tenant headers name B": lambda a, b: (
        {**a.headers, "X-Tenant-Id": b.tenant, "X-LumenAI-Tenant-Id": b.tenant}, None),
}


class TestTenantACannotReachTenantB:
    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    @pytest.mark.parametrize("attack", sorted(ATTACKS))
    def test_refused_with_no_data_and_no_write(self, pair, ep, attack):
        a, b = pair.a, pair.b
        before_b, before_a = _census(b.tenant), _census(a.tenant)
        headers, claim = ATTACKS[attack](a, b)

        response = _send(ep, headers, claim=claim)

        assert response.status_code == 403, (ep.id, attack, response.status_code, response.text[:200])
        _assert_no_trace(response, b)
        assert _census(b.tenant) == before_b           # nothing written into B
        assert _census(a.tenant) == before_a           # and the refusal wrote nothing at all

    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    def test_the_refusal_does_not_reveal_whether_the_tenant_exists(self, pair, ep):
        a, b = pair.a, pair.b
        existing = _send(ep, a.headers, claim=b.tenant)
        missing = _send(ep, a.headers, claim=_uid("no-such-tenant"))
        assert existing.status_code == missing.status_code == 403
        assert existing.json() == missing.json() == {"detail": TENANT_DENIED_DETAIL}

    @pytest.mark.parametrize("ep", BODY_ENDPOINTS, ids=by_id(BODY_ENDPOINTS))
    def test_a_tenant_in_the_query_of_a_body_route_is_not_a_selector(self, pair, ep):
        """Body routes do not read a query ``tenant_id``. Naming B there must not
        move the request into B: it is served as the caller's tenant."""
        a, b = pair.a, pair.b
        before_b = _census(b.tenant)

        response = _send(ep, a.headers, claim=b.tenant, via="query")

        assert response.status_code == 200, (ep.id, response.status_code, response.text[:200])
        assert _census(b.tenant) == before_b
        if response.headers.get("content-type", "").startswith("application/json"):
            _assert_no_trace(response, b)

    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    def test_the_secondary_tenant_header_alone_does_not_switch_tenant(self, pair, ep):
        a, b = pair.a, pair.b
        before_b = _census(b.tenant)

        response = _send(ep, {**a.headers, "X-LumenAI-Tenant-Id": b.tenant})

        assert response.status_code in (200, 403)
        assert _census(b.tenant) == before_b
        _assert_no_trace(response, b)

    def test_no_attack_on_any_endpoint_changes_any_table_of_tenant_b(self, pair):
        """One sweep of every attack over every endpoint, checked against EVERY
        table that has a tenant column — not only the ones these routes are known
        to write."""
        a, b = pair.a, pair.b
        before = _full_census(b.tenant)
        assert before, "tenant B should own rows before the sweep"

        for ep in TENANT_SCOPED:
            for attack in ATTACKS.values():
                headers, claim = attack(a, b)
                assert _send(ep, headers, claim=claim).status_code == 403

        assert _full_census(b.tenant) == before


# ══ 3. Unauthenticated and unverified callers ═════════════════════════════════

UNVERIFIED = [
    "anonymous", "anonymous naming tenant B", "not a token", "tampered signature for B's user",
    "unsigned token for B's user", "user with no membership", "user with no membership naming tenant B",
    "disabled member of B", "disabled member of B naming tenant B",
]


class TestUnverifiedCallersFailClosed:
    @pytest.mark.parametrize("ep", ENDPOINTS, ids=by_id(ENDPOINTS))
    @pytest.mark.parametrize("identity", UNVERIFIED)
    def test_refused_before_any_tenant_data_is_touched(self, pair, ep, identity):
        b = pair.b
        before = _census(b.tenant)

        response = _send(ep, _unverified_identities(pair)[identity], claim=b.tenant)

        assert response.status_code in REFUSED, (ep.id, identity, response.status_code)
        _assert_no_trace(response, b)
        assert _census(b.tenant) == before


# ══ 4. Legitimate multi-tenant membership ═════════════════════════════════════

class TestMultiTenantMembership:
    @pytest.fixture
    def both(self, pair) -> dict:
        """A user who is a verified, enabled member of BOTH tenants."""
        user = f"{_uid('p47203-both')}@example.com"
        _add_membership(pair.a.tenant, user)
        _add_membership(pair.b.tenant, user)
        return _bearer(user)

    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    def test_access_follows_the_selected_verified_tenant_only(self, pair, both, ep):
        a, b = pair.a, pair.b

        as_a = _send(ep, {**both, "X-Tenant-Id": a.tenant})
        as_b = _send(ep, {**both, "X-Tenant-Id": b.tenant}, claim=b.tenant)
        assert as_a.status_code == as_b.status_code == 200, (ep.id, as_a.status_code, as_b.status_code)
        assert b.tenant.encode() not in as_a.content
        assert a.tenant.encode() not in as_b.content

        # Belonging to both does not make the request ambiguous in the caller's favour.
        assert _send(ep, {**both, "X-Tenant-Id": a.tenant}, claim=b.tenant).status_code == 403
        assert _send(ep, both).status_code == 403                    # no tenant selected
        assert _send(ep, both, claim=b.tenant).status_code == 403    # a claim is not a selector

    def test_membership_in_a_third_tenant_grants_nothing_here(self, pair, both):
        third = _party("c")
        for ep in TENANT_SCOPED:
            assert _send(ep, {**both, "X-Tenant-Id": third.tenant}).status_code == 403
            assert _send(ep, {**both, "X-Tenant-Id": pair.a.tenant}, claim=third.tenant).status_code == 403

    def test_a_revoked_membership_stops_working_immediately(self, pair, both):
        from app.db import models

        db = SessionLocal()
        try:
            db.query(models.TenantMembership).filter(
                models.TenantMembership.tenant_id == pair.b.tenant,
                models.TenantMembership.user_email.like("p47203-both-%"),
            ).update({"is_enabled": False}, synchronize_session=False)
            db.commit()
        finally:
            db.close()
        ep = TENANT_SCOPED[0]
        assert _send(ep, {**both, "X-Tenant-Id": pair.b.tenant}).status_code == 403
        assert _send(ep, {**both, "X-Tenant-Id": pair.a.tenant}).status_code == 200


# ══ 5. Unsafe defaults: demo-tenant / default-tenant ══════════════════════════

class TestHardcodedTenantsAreRefusedNotRedirected:
    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    @pytest.mark.parametrize("hardcoded", ["demo-tenant", "default-tenant", "demo"])
    def test_a_client_that_still_sends_a_hardcoded_tenant_gets_403(self, pair, ep, hardcoded):
        a = pair.a
        before_named, before_own = _census(hardcoded), _census(a.tenant)

        response = _send(ep, a.headers, claim=hardcoded)

        assert response.status_code == 403, (ep.id, hardcoded, response.status_code)
        assert response.json() == {"detail": TENANT_DENIED_DETAIL}
        assert _census(hardcoded) == before_named      # not served from the named tenant ...
        assert _census(a.tenant) == before_own         # ... and not silently served from the caller's


# ══ 6. Writes ═════════════════════════════════════════════════════════════════

class TestWritesLandOnlyInTheCallersTenant:
    def test_prediction_outcomes_and_accuracy(self, pair):
        a, b = pair.a, pair.b
        for _ in range(2):
            body = {**dict(_OUTCOME), "predicted_risk_category": "high", "actual_outcome": "failed"}
            assert client.post(f"{P}/outcomes", json=body, headers=a.headers).status_code == 200

        db = SessionLocal()
        try:
            assert db.query(PredictionOutcome).filter(PredictionOutcome.tenant_id == a.tenant).count() == 2
            assert db.query(PredictionOutcome).filter(PredictionOutcome.tenant_id == b.tenant).count() == 1
        finally:
            db.close()
        accuracy_a = client.get(f"{P}/accuracy", headers=a.headers).json()["accuracy"]
        accuracy_b = client.get(f"{P}/accuracy", headers=b.headers).json()["accuracy"]
        assert (accuracy_a["tenant_id"], accuracy_a["total_outcomes"]) == (a.tenant, 2)
        assert (accuracy_b["tenant_id"], accuracy_b["total_outcomes"]) == (b.tenant, 1)

    def test_fda_submissions_are_visible_only_to_their_tenant(self, pair):
        a, b = pair.a, pair.b
        marker = _uid("confidential-device")
        created = client.post(
            f"{R}/fda-submissions", headers=a.headers,
            json={"device_name": marker, "manufacturer": "synthetic-manufacturer"})
        assert created.status_code == 200

        assert marker in client.get(f"{R}/fda-submissions", headers=a.headers).text
        assert marker not in client.get(f"{R}/fda-submissions", headers=b.headers).text
        assert marker not in client.get(f"{R}/dashboard", headers=b.headers).text
        assert client.get(f"{R}/fda-submissions", headers=b.headers,
                          params={"tenant_id": a.tenant}).status_code == 403

    def test_audit_packages_are_visible_only_to_their_tenant(self, pair):
        a, b = pair.a, pair.b
        assert client.post(f"{R}/audit-package", json=dict(_PACKAGE), headers=a.headers).status_code == 200

        listed_a = client.get(f"{R}/audit-packages", headers=a.headers).json()["packages"]
        listed_b = client.get(f"{R}/audit-packages", headers=b.headers).json()["packages"]
        assert len(listed_a) == 1 and listed_b == []
        db = SessionLocal()
        try:
            owners = {row.tenant_id for row in db.query(RegulatoryAuditPackage).filter(
                RegulatoryAuditPackage.id == listed_a[0]["id"])}
        finally:
            db.close()
        assert owners == {a.tenant}

    def test_board_reports_are_generated_published_and_listed_per_tenant(self, pair):
        a, b = pair.a, pair.b
        body = {"report_type": "monthly", "period_label": PERIOD}
        draft_b = client.post(f"{B}/reports/generate", json=body, headers=b.headers)
        assert draft_b.status_code == 200 and draft_b.json()["status"] != "published"

        # A tries to publish B's report by naming B: refused, B's report untouched.
        attack = client.post(f"{B}/reports/generate", headers=a.headers,
                             json={**body, "publish": True, "tenant_id": b.tenant})
        assert attack.status_code == 403
        db = SessionLocal()
        try:
            statuses = {r.status for r in db.query(BoardReport).filter(BoardReport.tenant_id == b.tenant)}
        finally:
            db.close()
        assert "published" not in statuses and statuses

        # A publishes its own.
        own = client.post(f"{B}/reports/generate", json={**body, "publish": True}, headers=a.headers)
        assert own.status_code == 200 and own.json()["tenant_id"] == a.tenant
        assert own.json()["status"] == "published"
        listed_a = client.get(f"{B}/reports/monthly", headers=a.headers).json()
        listed_b = client.get(f"{B}/reports/monthly", headers=b.headers).json()
        assert {r["id"] for r in listed_a}.isdisjoint({r["id"] for r in listed_b})
        fetched_b = client.get(f"{B}/reports/monthly/{PERIOD}", headers=b.headers).json()
        assert fetched_b["tenant_id"] == b.tenant and fetched_b["status"] != "published"

    def test_a_write_that_names_no_tenant_is_stored_under_the_caller(self, pair):
        a = pair.a
        for ep in BODY_ENDPOINTS:
            assert _send(ep, a.headers).status_code == 200, ep.id
        census = _census(a.tenant)
        assert census["prediction_outcomes"] == 1 and census["fda_submission_trackers"] == 1
        assert census["regulatory_audit_packages"] >= 1 and census["board_reports"] == 1


# ══ 7. Derived persistence and audit attribution ══════════════════════════════
#
# None of these four modules starts a background task. What outlives a request
# is what a request PERSISTS as a side effect: benchmark snapshots written by
# GET aggregation routes, generated reports and packages, and the prediction
# access audit trail. (The CV async job is covered in test_p472_cross_tenant_api.)

class TestDerivedPersistenceStaysInTenant:
    def test_aggregation_snapshots_are_written_only_for_the_callers_tenant(self, pair):
        a, b = pair.a, pair.b
        others = (b.tenant, "demo-tenant", "default-tenant")
        before = {tenant: _full_census(tenant) for tenant in others}
        assert _census(a.tenant)["enterprise_rollups"] == 0

        for template in (f"{B}/hospitals", f"{B}/vendors", f"{B}/rollup", f"{B}/executive-dashboard",
                         f"{B}/kpi-summary"):
            assert client.get(template, headers=a.headers).status_code == 200

        # The snapshots these routes persist were written for the caller ...
        assert _census(a.tenant)["enterprise_rollups"] >= 1
        # ... and for nobody else: not tenant B, and not the old default tenants.
        assert {tenant: _full_census(tenant) for tenant in others} == before

    def test_prediction_access_is_audited_under_the_verified_tenant_and_actor(self, pair):
        a = pair.a
        response = client.get(
            f"{P}/failures", headers={**a.headers, "X-LumenAI-Role": "enterprise_admin",
                                      "X-LumenAI-Actor": "someone-else@example.com"})
        assert response.status_code == 200

        db = SessionLocal()
        try:
            rows = db.query(AuditLog).filter(
                AuditLog.tenant_id == a.tenant, AuditLog.action_type == "prediction:failures_list").all()
        finally:
            db.close()
        assert len(rows) == 1
        assert rows[0].actor_email == a.user                 # from the verified token
        assert rows[0].actor_role != "enterprise_admin"      # not from a client header
        assert rows[0].resource_id == a.tenant

    def test_a_refused_request_is_not_audited_as_access_to_the_named_tenant(self, pair):
        a, b = pair.a, pair.b
        db = SessionLocal()
        try:
            before = db.query(AuditLog).filter(AuditLog.tenant_id == b.tenant).count()
        finally:
            db.close()
        for ep in [ep for ep in TENANT_SCOPED if ep.template.startswith(P)]:
            assert _send(ep, a.headers, claim=b.tenant).status_code == 403
        db = SessionLocal()
        try:
            assert db.query(AuditLog).filter(AuditLog.tenant_id == b.tenant).count() == before
        finally:
            db.close()


# ══ 8. Aggregate isolation and non-disclosure, with real tenant data ══════════

# Fields that carry the time of the request itself.
_VOLATILE = ("generated", "timestamp", "assessment_date", "prediction_date", "created_at", "computed_at",
             "updated_at")


def _stable(value):
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if not any(marker in k for marker in _VOLATILE)}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def _give_b_more_data(b: Party) -> list[str]:
    """Tenant B creates sensitive records of every kind; returns their markers."""
    device, instrument = _uid("b-confidential-device"), _uid("b-confidential-instrument")
    assert client.post(f"{R}/fda-submissions", headers=b.headers,
                       json={"device_name": device, "manufacturer": "b-manufacturer"}).status_code == 200
    assert client.post(f"{P}/outcomes", headers=b.headers, json={
        **dict(_OUTCOME), "instrument_name": instrument, "predicted_risk_category": "high",
        "actual_outcome": "failed"}).status_code == 200
    assert client.post(f"{R}/audit-package", json=dict(_PACKAGE), headers=b.headers).status_code == 200
    assert client.post(f"{B}/reports/generate", headers=b.headers,
                       json={"report_type": "monthly", "period_label": PERIOD, "publish": True}).status_code == 200
    for _ in range(2):
        _analyze(b)
    return [device, instrument]


class TestAggregateIsolation:
    def test_each_tenant_aggregates_only_its_own_verified_inference(self, world):
        a, b = world.a, world.b
        kpi_a = client.get(f"{B}/kpi-summary", headers=a.headers).json()
        kpi_b = client.get(f"{B}/kpi-summary", headers=b.headers).json()
        assert kpi_a["total_inspections"] == len(a.inference_ids) == 1
        assert kpi_b["total_inspections"] == len(b.inference_ids) == 4
        rollup_a = client.get(f"{B}/rollup", headers=a.headers).json()
        assert (rollup_a["tenant_id"], rollup_a["total_cv_analyses"]) == (a.tenant, 1)

    @pytest.mark.parametrize("ep", READ_ENDPOINTS, ids=by_id(READ_ENDPOINTS))
    def test_activity_in_tenant_b_does_not_move_tenant_a(self, world, ep):
        """Differential: A's response is the same before and after B creates more
        inference runs, outcomes, submissions, packages and reports."""
        a, b = world.a, world.b
        _send(ep, a.headers)                 # warm-up: some routes persist on first use
        before = _send(ep, a.headers)
        assert before.status_code == 200

        _give_b_more_data(b)

        after = _send(ep, a.headers)
        assert after.status_code == 200
        assert _stable(after.json()) == _stable(before.json()), ep.id


class TestNonDisclosure:
    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    def test_no_response_to_tenant_a_contains_tenant_b_records(self, world, ep):
        a, b = world.a, world.b
        secrets = [*_give_b_more_data(b), *b.inference_ids, b.tenant, b.user]

        for response in (_send(ep, a.headers), _send(ep, a.headers, claim=a.tenant),
                         _send(ep, a.headers, claim=b.tenant)):
            for secret in secrets:
                assert secret.encode() not in response.content, (ep.id, secret)


# ══ 9. The shared development token (non-production only) ═════════════════════

class TestDevelopmentTokenGetsNoNewPower:
    """The shared development token is an existing non-production credential whose
    tenant is whatever ``X-Tenant-Id`` says. P472-03 does not widen it: a tenant
    named only in the query or body selects nothing."""
    DEV = {"Authorization": "Bearer dev-token"}

    @pytest.mark.parametrize("ep", TENANT_SCOPED, ids=by_id(TENANT_SCOPED))
    def test_a_claim_without_the_matching_header_is_refused(self, pair, ep):
        b = pair.b
        before = _census(b.tenant)

        assert _send(ep, self.DEV, claim=b.tenant).status_code == 403
        assert _send(ep, {**self.DEV, "X-Tenant-Id": pair.a.tenant}, claim=b.tenant).status_code == 403
        assert _census(b.tenant) == before


# ══ 10. The helper ════════════════════════════════════════════════════════════

class TestAuthorizedTenantHelper:
    CTX = AuthContext(actor="user@example.com", role="viewer", tenant_id="tenant-a")

    @pytest.mark.parametrize("claims", [(), (None,), ("",), ("   ",), ("tenant-a",), (" tenant-a ",),
                                        ("tenant-a", None, "", "tenant-a")])
    def test_returns_the_verified_tenant(self, claims):
        assert authorized_tenant(self.CTX, *claims) == "tenant-a"

    @pytest.mark.parametrize("claims", [("tenant-b",), ("TENANT-A",), ("tenant-a", "tenant-b"), ("tenant-a/",),
                                        ("*",), ("%",), (["tenant-a"],), (0,), ({"tenant_id": "tenant-a"},)])
    def test_refuses_any_other_claim(self, claims):
        with pytest.raises(HTTPException) as refused:
            authorized_tenant(self.CTX, *claims)
        assert refused.value.status_code == 403 and refused.value.detail == TENANT_DENIED_DETAIL

    @pytest.mark.parametrize("tenant", ["", "   ", None])
    def test_a_context_without_a_tenant_fails_closed(self, tenant):
        ctx = AuthContext(actor="user@example.com", role="viewer", tenant_id=tenant)
        for claims in ((), ("tenant-a",)):
            with pytest.raises(HTTPException) as refused:
                authorized_tenant(ctx, *claims)
            assert refused.value.status_code == 403

    def test_a_unique_id_is_never_confused_with_another(self):
        ctx = AuthContext(actor="u", role="viewer", tenant_id=f"t-{uuid.uuid4().hex}")
        with pytest.raises(HTTPException):
            authorized_tenant(ctx, f"t-{uuid.uuid4().hex}")
