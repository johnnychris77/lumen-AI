"""P472-03 remediation batch 2 — verified tenant membership (AW-01, AW-02, AW-05).

Three shared mechanisms let a signed-in user act in a tenant they do not belong
to. Each is one root cause and is fixed in its own commit:

* ``resolve_tenant`` returned the ``X-Tenant-Id`` header unverified (AW-02, and
  the tenant-analytics part of AW-01);
* handlers that read the tenant header directly behind a global-role guard
  (AW-01: ML images, operations);
* ``current_user.tenant_id or <header>``: users with no membership, or several,
  were scoped by whatever header they sent (AW-05).

All three now go through ``app.auth.tenant_scope.principal_tenant``.

What this file asserts
----------------------
1. The rule itself, as unit tests of the resolver.
2. For EVERY mounted route that resolves its tenant through the verified
   resolver (discovered from the application, not listed by hand): a
   schema-valid request is refused when it names another tenant in either tenant
   header, sends two tenant headers that disagree, comes from a user with no
   membership, or comes from a user with two memberships who selects none or a
   third tenant — and such a request executes no SQL bound to the other tenant
   and writes nothing. The same request from the owner is served.
3. With stored records of two tenants: lists, exports and object routes of the
   affected modules return only the caller's tenant, and audit rows are
   attributed to the verified tenant.

Requests are built from the OpenAPI description by the same builder the
application-wide sweep uses (``tenant_isolation_sweep_runner``).
"""
from __future__ import annotations

import importlib
import inspect
import re
import signal
import socket
import uuid

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from starlette.requests import Request

from tenant_isolation_sweep_runner import (
    MEMBERSHIP_TABLES,
    PROFILES,
    _Plan,
    _Spec,
    _scope_hits,
    _tables_touched,
)

from app.auth.tenant_scope import (
    NO_VERIFIED_TENANT_DETAIL,
    TENANT_DENIED_DETAIL,
    named_tenant,
    principal_tenant,
)
from app.db import models
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.user_role_assignment import UserRoleAssignment
from app.routers.auth_simple import _make_token
from app.security.principal import (
    METHOD_DEVELOPMENT,
    METHOD_JWT,
    AuthenticatedPrincipal,
    TenantMembershipView,
)
from app.tenant import resolve_tenant

REFUSED = (401, 403)
RUN = uuid.uuid4().hex[:8]
TENANT_A, TENANT_B, TENANT_C = f"b2-alpha-{RUN}", f"b2-bravo-{RUN}", f"b2-charlie-{RUN}"
RESOLVER_CALLS = ("principal_tenant(", "verified_request_tenant(")
# (global role, tenant-membership role): the sweep's profiles plus the two global
# roles that some of these routes require and the sweep does not carry. The
# platform administrator (global role "admin") is deliberately absent.
ROLE_PROFILES = [*PROFILES, ("manager", "tenant_admin"), ("technician", "operator")]


# ══ 1. The rule ═══════════════════════════════════════════════════════════════

def _request(**headers: str) -> Request:
    raw = [(name.lower().replace("_", "-").encode(), value.encode()) for name, value in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "query_string": b""})


def _principal(*tenants: str, role: str = "spd_manager", method: str = METHOD_JWT) -> AuthenticatedPrincipal:
    memberships = tuple(TenantMembershipView(tenant_id=t, tenant_name=t, role_name="tenant_admin") for t in tenants)
    return AuthenticatedPrincipal(
        subject="u@example.com", email="u@example.com", role=role, authentication_method=method,
        tenant_memberships=memberships, active_tenant_id=tenants[0] if len(tenants) == 1 else None)


def _refusal(principal, request) -> tuple[int, str]:
    with pytest.raises(Exception) as caught:
        principal_tenant(principal, request)
    return caught.value.status_code, caught.value.detail


class TestTheRule:
    def test_a_member_acts_in_their_sole_tenant_when_none_is_named(self):
        assert principal_tenant(_principal("t-a"), _request()) == "t-a"

    @pytest.mark.parametrize("header", ["x_tenant_id", "x_lumenai_tenant_id"])
    def test_a_member_may_name_their_own_tenant_in_either_header(self, header):
        assert principal_tenant(_principal("t-a"), _request(**{header: "t-a"})) == "t-a"

    @pytest.mark.parametrize("header", ["x_tenant_id", "x_lumenai_tenant_id"])
    def test_naming_another_tenant_is_refused_not_redirected(self, header):
        assert _refusal(_principal("t-a"), _request(**{header: "t-b"})) == (403, TENANT_DENIED_DETAIL)

    @pytest.mark.parametrize("headers", [
        {"x_lumenai_tenant_id": "t-a", "x_tenant_id": "t-b"},
        {"x_tenant_id": "t-a", "x_lumenai_tenant_id": "t-b"},
    ])
    def test_two_tenant_headers_that_disagree_are_refused(self, headers):
        """The AW-02 request: one header passes the membership check, the other selects the data."""
        assert _refusal(_principal("t-a"), _request(**headers)) == (403, TENANT_DENIED_DETAIL)

    def test_two_tenant_headers_that_agree_are_accepted(self):
        assert principal_tenant(_principal("t-a"), _request(x_tenant_id="t-a", x_lumenai_tenant_id="t-a")) == "t-a"

    @pytest.mark.parametrize("headers", [{}, {"x_tenant_id": "t-b"}, {"x_lumenai_tenant_id": "t-b"},
                                         {"x_tenant_id": "default-tenant"}])
    def test_a_user_with_no_membership_is_refused(self, headers):
        status, _ = _refusal(_principal(), _request(**headers))
        assert status == 403

    def test_a_user_with_no_membership_is_not_pooled_in_a_default_tenant(self):
        assert _refusal(_principal(), _request()) == (403, NO_VERIFIED_TENANT_DETAIL)

    def test_a_user_with_several_memberships_must_select_one(self):
        assert _refusal(_principal("t-a", "t-c"), _request()) == (403, NO_VERIFIED_TENANT_DETAIL)

    @pytest.mark.parametrize("selected", ["t-a", "t-c"])
    def test_a_user_with_several_memberships_acts_in_the_selected_one(self, selected):
        assert principal_tenant(_principal("t-a", "t-c"), _request(x_tenant_id=selected)) == selected

    def test_a_user_with_several_memberships_cannot_select_a_third_tenant(self):
        assert _refusal(_principal("t-a", "t-c"), _request(x_tenant_id="t-b")) == (403, TENANT_DENIED_DETAIL)

    @pytest.mark.parametrize("value", ["", "   "])
    def test_an_empty_tenant_header_names_nothing(self, value):
        assert named_tenant(_request(x_tenant_id=value)) is None
        assert principal_tenant(_principal("t-a"), _request(x_tenant_id=value)) == "t-a"

    @pytest.mark.parametrize("not_a_principal", [None, {"tenant_id": "t-b"}, object()])
    def test_anything_that_is_not_a_verified_principal_is_refused(self, not_a_principal):
        with pytest.raises(Exception) as caught:
            principal_tenant(not_a_principal, _request(x_tenant_id="t-b"))
        assert caught.value.status_code == 403

    def test_a_disabled_membership_is_no_membership(self):
        """Only enabled memberships are loaded into the principal (``_load_tenant_memberships``)."""
        from app.deps import _load_tenant_memberships

        email = f"b2-disabled-{uuid.uuid4().hex[:8]}@example.com"
        db = SessionLocal()
        try:
            db.add(models.TenantMembership(tenant_id="t-a", user_email=email, role="tenant_admin", is_enabled=False))
            db.commit()
            assert _load_tenant_memberships(db, email) == ()
        finally:
            db.close()

    # The two caller classes whose behaviour is deliberately unchanged. They are
    # pinned here so that a change to either is a visible decision.
    def test_development_tokens_keep_their_previous_behaviour(self):
        dev = _principal(role="admin", method=METHOD_DEVELOPMENT)
        assert principal_tenant(dev, _request()) == "default-tenant"
        assert principal_tenant(dev, _request(x_tenant_id="t-b")) == "t-b"
        assert principal_tenant(_principal("t-a", method=METHOD_DEVELOPMENT), _request(x_tenant_id="t-b")) == "t-a"

    def test_development_tokens_do_not_exist_in_production(self, monkeypatch):
        """``get_current_user`` only issues a development principal from ``_DEV_ROLE_MAP``,
        which is empty unless dev auth is enabled outside production."""
        import app.deps as deps

        source = inspect.getsource(deps)
        assert '_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and _APP_ENV not in {"production", "prod"}' in source
        assert "} if _DEV_AUTH_ACTIVE else {}" in source

    def test_the_platform_administrator_rule_is_unchanged_and_explicit(self):
        """OPEN GOVERNANCE ITEM (not closed by this batch): the global role ``admin``
        still reaches any tenant it names. Unchanged from before; pinned so it cannot
        widen or disappear silently."""
        admin = _principal(role="admin")
        assert principal_tenant(admin, _request(x_tenant_id="t-b")) == "t-b"
        assert principal_tenant(admin, _request()) == "default-tenant"
        assert principal_tenant(_principal("t-a", role="admin"), _request(x_tenant_id="t-b")) == "t-a"

    def test_disagreeing_headers_are_refused_for_every_caller_class(self):
        for principal in (_principal(role="admin"), _principal(role="admin", method=METHOD_DEVELOPMENT)):
            assert _refusal(principal, _request(x_tenant_id="t-a", x_lumenai_tenant_id="t-b"))[0] == 403

    def test_no_legacy_fallback_remains_in_remediated_code(self):
        """``resolve_tenant`` no longer reads a header on its own."""
        source = inspect.getsource(importlib.import_module("app.tenant"))
        assert "Header(" not in source and "verified_request_tenant(" in source


# ══ 2. Every route that uses the verified resolver ════════════════════════════

def _dependency_calls(dependant, found: set) -> set:
    for sub in dependant.dependencies:
        if sub.call is not None:
            found.add(sub.call)
        _dependency_calls(sub, found)
    return found


def _tenant_helpers(module) -> set[str]:
    """Functions of ``module`` that reach the verified resolver, directly or through
    another function of the same module."""
    sources: dict[str, str] = {}
    for name, obj in vars(module).items():
        if inspect.isfunction(obj) and obj.__module__ == module.__name__:
            try:
                sources[name] = inspect.getsource(obj)
            except (OSError, TypeError):
                continue
    helpers = {name for name, source in sources.items() if any(call in source for call in RESOLVER_CALLS)}
    grew = True
    while grew:
        grew = False
        for name, source in sources.items():
            if name not in helpers and any(re.search(rf"\b{re.escape(h)}\(", source) for h in helpers):
                helpers.add(name)
                grew = True
    return helpers


def _discover() -> list[tuple[str, str, str]]:
    """(method, path, how) for every mounted route that resolves its tenant through
    the verified resolver. ``how`` is ``dependency`` (``Depends(resolve_tenant)``)
    or ``handler`` (the handler calls the resolver itself)."""
    found, seen, helpers = [], set(), {}
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        module_name = route.endpoint.__module__
        if not module_name.startswith("app."):
            continue
        if resolve_tenant in _dependency_calls(route.dependant, set()):
            how = "dependency"
        else:
            if module_name not in helpers:
                helpers[module_name] = _tenant_helpers(importlib.import_module(module_name))
            if route.endpoint.__name__ not in helpers[module_name]:
                continue
            how = "handler"
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            if (method, route.path) not in seen:          # the first registration is the one served
                seen.add((method, route.path))
                found.append((method, route.path, how))
    return found


ROUTES = _discover()
ROUTE_IDS = [f"{method} {path}" for method, path, _ in ROUTES]

# Routes on which this file's own checks found a defect that is NOT fixed yet.
# Each is a strict expected failure naming its finding: it must be fixed, and the
# entry removed, before the test can pass. {"METHOD path": "finding: what is wrong"}
OPEN_OWNER_FINDINGS: dict[str, str] = {}
OPEN_REFUSAL_FINDINGS: dict[str, str] = {}

# Routes that serve shared, network-wide data by default and resolve a tenant only
# on an optional branch. The request is made on that branch, so the tenant rule is
# what is exercised.
TENANT_BRANCH_PARAMS: dict[str, dict] = {
    "GET /api/horizon/emerging-trends": {"mine_only": "true"},
}
# Routes that update one network-wide record on behalf of the calling tenant. The
# record itself lists the participating tenants (that is its purpose), so SQL for
# one tenant's request necessarily carries the others' ids. Covered by
# ``TestTrendAlertsDoNotNameOtherOrganisations`` below.
SHARED_RECORD_ROUTES = {
    "POST /api/horizon/emerging-trends/{trend_id}/acknowledge":
        "one cross-hospital alert row records every organisation that acknowledged it",
}
TENANT_BRANCH_BODIES: dict[str, dict] = {
    "POST /api/horizon/evidence": {"private": True, "evidence_type": "peer_reviewed", "title": "t",
                                   "citation_text": "c"},
}


def _params(open_findings: dict[str, str]) -> list:
    return [
        pytest.param(method, path, how, id=f"{method} {path}", marks=(
            [pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {open_findings[f'{method} {path}']}")]
            if f"{method} {path}" in open_findings else []))
        for method, path, how in ROUTES
    ]

# Identities: one user per sweep role profile in each role the tests need.
_USERS: dict[str, dict[int, str]] = {"a": {}, "none": {}, "multi": {}}
_MEMBERSHIPS: list[tuple[str, str, str]] = []


@pytest.fixture(scope="module")
def world():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for index, (global_role, tenant_role) in enumerate(ROLE_PROFILES):
            for kind, tenants in (("a", [TENANT_A]), ("none", []), ("multi", [TENANT_A, TENANT_C])):
                user = f"b2-{kind}-{index}-{RUN}@example.com"
                _USERS[kind][index] = user
                db.add(UserRoleAssignment(username=user, role=global_role, assigned_by="p472-03-batch2"))
                _MEMBERSHIPS.extend((tenant, user, tenant_role) for tenant in tenants)
        db.commit()
    finally:
        db.close()
    return _USERS


@pytest.fixture(autouse=True)
def _memberships(world):
    """conftest clears ``tenant_memberships`` before every test; put ours back."""
    db = SessionLocal()
    try:
        for tenant, user, role in _MEMBERSHIPS:
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role=role, is_enabled=True))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _no_outbound_network(monkeypatch):
    real_connect = socket.socket.connect

    def guarded(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if self.family == socket.AF_UNIX or str(host) in {"127.0.0.1", "::1", "localhost"}:
            return real_connect(self, address, *args, **kwargs)
        raise OSError(f"outbound network blocked in the batch 2 tests: {host!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded)


class _Timeout(Exception):
    pass


def _alarm(_signum, _frame):
    raise _Timeout()


class _Caller:
    """Sends one route's request as different identities and records the SQL each executes."""

    def __init__(self) -> None:
        self.client = TestClient(app, raise_server_exceptions=False)
        self.spec = _Spec(app.openapi())
        self.captured: list = []
        self.capturing = False
        self.profile: dict[tuple[str, str], tuple[int | None, int]] = {}

    def on_sql(self, _conn, _cursor, statement, parameters, _context, _executemany):
        if self.capturing:
            self.captured.append((statement, parameters))

    def call(self, method: str, path: str, headers: dict) -> tuple[int, list, str]:
        from app.limiter import limiter

        plan = _Plan(self.spec, method, path)
        url, params, body = plan.request(path_tenant=TENANT_A, query_tenant=TENANT_A, body_tenant=TENANT_A)
        params.update({name: TENANT_A for name in plan.required_tenant_query})
        params.update(TENANT_BRANCH_PARAMS.get(f"{method} {path}", {}))
        body = TENANT_BRANCH_BODIES.get(f"{method} {path}", body)
        if limiter is not None:
            try:
                limiter.reset()
            except Exception:  # noqa: BLE001 - not every limiter backend can reset
                pass
        self.captured, self.capturing = [], True
        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(30)
        try:
            response = self.client.request(method, url, headers=headers, params=params or None, json=body)
            status, text = response.status_code, response.text[:200000]
        except _Timeout:
            status, text = -1, ""
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)
            self.capturing = False
        return status, list(self.captured), text

    @staticmethod
    def headers(user: str | None, **extra: str) -> dict:
        base = {"Authorization": f"Bearer {_make_token(user)}"} if user else {}
        return {**base, **extra}

    def owner_profile(self, method: str, path: str) -> tuple[int | None, int]:
        """The first role profile whose own-tenant request is not refused, and its status."""
        key = (method, path)
        if key not in self.profile:
            self.profile[key] = (None, 403)
            for index in range(len(ROLE_PROFILES)):
                status, _, _ = self.call(method, path, self.headers(_USERS["a"][index], **{"X-Tenant-Id": TENANT_A}))
                if status not in REFUSED:
                    self.profile[key] = (index, status)
                    break
        return self.profile[key]


@pytest.fixture(scope="module")
def caller():
    instance = _Caller()
    event.listen(Engine, "before_cursor_execute", instance.on_sql)
    yield instance
    event.remove(Engine, "before_cursor_execute", instance.on_sql)


def _bound(capture, tenant: str) -> list[str]:
    hits = _scope_hits(capture, tenant)
    return sorted(set(hits["read"]) | set(hits["write"]))


# Tables a refused request may still write: none. ``scheduler_leader`` is the
# heartbeat of the background scheduler thread, which can tick while a request is
# being captured; it is not written by any request.
BACKGROUND_TABLES = {"scheduler_leader"}


def _written(capture) -> list[str]:
    return sorted(set(_tables_touched(capture)["write"]) - MEMBERSHIP_TABLES - BACKGROUND_TABLES)


def _attacks(index: int) -> list[tuple[str, dict, list[str]]]:
    """(name, headers, tenants that must not be bound by any SQL)."""
    member, outsider, multi = _USERS["a"][index], _USERS["none"][index], _USERS["multi"][index]
    h = _Caller.headers
    return [
        ("member of A names B in X-Tenant-Id", h(member, **{"X-Tenant-Id": TENANT_B}), [TENANT_B]),
        ("member of A names B in X-LumenAI-Tenant-Id", h(member, **{"X-LumenAI-Tenant-Id": TENANT_B}), [TENANT_B]),
        ("split headers: X-LumenAI-Tenant-Id A, X-Tenant-Id B",
         h(member, **{"X-LumenAI-Tenant-Id": TENANT_A, "X-Tenant-Id": TENANT_B}), [TENANT_B]),
        ("split headers: X-Tenant-Id A, X-LumenAI-Tenant-Id B",
         h(member, **{"X-Tenant-Id": TENANT_A, "X-LumenAI-Tenant-Id": TENANT_B}), [TENANT_B]),
        ("no membership, no tenant named", h(outsider), ["default-tenant"]),
        ("no membership, names B", h(outsider, **{"X-Tenant-Id": TENANT_B}), [TENANT_B, "default-tenant"]),
        ("two memberships, none selected", h(multi), [TENANT_A, TENANT_C, "default-tenant"]),
        ("two memberships, names a third tenant", h(multi, **{"X-Tenant-Id": TENANT_B}), [TENANT_B]),
    ]


def test_the_route_table_is_the_mounted_application():
    """The parametrised tests below cover every route that uses the verified
    resolver; these counts change only when a route is added or converted."""
    by_how = {how: sum(1 for _, _, h in ROUTES if h == how) for how in ("dependency", "handler")}
    assert by_how == {"dependency": 190, "handler": 497}, by_how
    assert len(set(ROUTE_IDS)) == len(ROUTE_IDS)
    assert set(OPEN_OWNER_FINDINGS) | set(OPEN_REFUSAL_FINDINGS) <= set(ROUTE_IDS)


@pytest.mark.parametrize(("method", "path", "how"), _params(OPEN_REFUSAL_FINDINGS))
def test_unverified_tenant_requests_are_refused_and_change_nothing(caller, method, path, how):
    index, owner_status = caller.owner_profile(method, path)
    anonymous, capture, _ = caller.call(method, path, {"X-Tenant-Id": TENANT_B})
    assert anonymous in REFUSED, f"unauthenticated caller got HTTP {anonymous}"
    assert _written(capture) == [] and _bound(capture, TENANT_B) == []

    for name, headers, forbidden in _attacks(index if index is not None else 1):
        status, capture, text = caller.call(method, path, headers)
        # ``dependency`` routes resolve the tenant before the handler runs, so the
        # refusal is unconditional. A ``handler`` route may fail earlier in the same
        # way for every caller (a missing object, say); that is not an acceptance.
        failed_like_the_owner = how == "handler" and owner_status >= 400 and status == owner_status
        assert status in REFUSED or failed_like_the_owner, f"{name}: HTTP {status} (owner gets {owner_status})"
        for tenant in forbidden:
            assert _bound(capture, tenant) == [], f"{name}: SQL bound to {tenant} on {_bound(capture, tenant)}"
        assert _written(capture) == [], f"{name}: refused request wrote to {_written(capture)}"
        assert TENANT_B not in text, f"{name}: the response names tenant B"


@pytest.mark.parametrize(("method", "path", "how"), _params(OPEN_OWNER_FINDINGS))
def test_the_owner_and_a_selected_membership_are_served(caller, method, path, how):
    index, owner_status = caller.owner_profile(method, path)
    if index is None:
        # No tenant role profile may call this route at all (it needs a role the
        # tenant profiles do not have). Counted in the coverage test below.
        return
    assert owner_status not in REFUSED

    status, capture, _ = caller.call(method, path, caller.headers(_USERS["a"][index]))
    if how == "handler":
        # The web client sends no tenant header: the member acts in their own tenant.
        assert status not in REFUSED, f"member with no tenant header got HTTP {status}"
    assert _bound(capture, TENANT_B) == [] and _bound(capture, TENANT_C) == []

    status, capture, text = caller.call(
        method, path, caller.headers(_USERS["multi"][index], **{"X-Tenant-Id": TENANT_C}))
    assert status not in REFUSED, f"user with two memberships selecting one of them got HTTP {status}"
    assert _bound(capture, TENANT_B) == []
    assert TENANT_B not in text
    if f"{method} {path}" in SHARED_RECORD_ROUTES:
        # The row is shared by design and stores other participants; what matters is
        # that the response does not name them.
        assert TENANT_A not in text, "the response to a request made in tenant C names tenant A"
    else:
        assert _bound(capture, TENANT_A) == [], "a request made in tenant C touched tenant A"


def test_most_routes_were_exercised_with_a_working_owner(caller):
    """How many routes a tenant role profile can actually call. The rest are refused
    for every profile (role-gated) and so were only shown to refuse."""
    reachable = sum(1 for method, path, _ in ROUTES if caller.owner_profile(method, path)[0] is not None)
    assert reachable >= int(len(ROUTES) * 0.9), f"only {reachable} of {len(ROUTES)} routes had a working owner"


# ══ 3. Stored records of two tenants ══════════════════════════════════════════

import io  # noqa: E402
import zipfile  # noqa: E402

from app.models.audit_log import AuditLog  # noqa: E402


def _contains(response, needle: str) -> bool:
    """``needle`` anywhere in a response, including inside ZIP/XLSX members."""
    raw = response.content
    if needle.encode() in raw:
        return True
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for name in archive.namelist():
                member = archive.read(name)
                if needle.encode() in member:
                    return True
                if member[:2] == b"PK":
                    with zipfile.ZipFile(io.BytesIO(member)) as inner:
                        if any(needle.encode() in inner.read(n) for n in inner.namelist()):
                            return True
    return False


def _member(tenant: str, *, global_role: str = "spd_manager", tenant_role: str = "tenant_admin") -> tuple[str, dict]:
    """A signed-in user who is a member of ``tenant`` (registered for re-seeding)."""
    user = f"b2-{uuid.uuid4().hex[:10]}@example.com"
    db = SessionLocal()
    try:
        db.add(UserRoleAssignment(username=user, role=global_role, assigned_by="p472-03-batch2"))
        db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role=tenant_role, is_enabled=True))
        db.commit()
    finally:
        db.close()
    return user, {"Authorization": f"Bearer {_make_token(user)}"}


http = TestClient(app, raise_server_exceptions=False)


class TestAuditLogsAreTenantScoped:
    """AW-02: ``/api/audit-logs`` verified membership on one header and selected the
    rows by another."""

    PATHS = ["/api/audit-logs", "/api/audit-logs/export.json", "/api/audit-logs/export.csv",
             "/api/audit-logs/export.xlsx", "/api/audit-logs/export.bundle.zip"]

    @pytest.fixture
    def rows(self):
        mine, theirs = f"b2-mine-{uuid.uuid4().hex[:10]}", f"b2-theirs-{uuid.uuid4().hex[:10]}"
        db = SessionLocal()
        try:
            db.add(AuditLog(tenant_id=TENANT_A, tenant_name="A", actor_email="a@example.com",
                            action_type="a.action", resource_type="record", resource_id=mine))
            db.add(AuditLog(tenant_id=TENANT_B, tenant_name="B", actor_email="b@example.com",
                            action_type="b.private.action", resource_type="record", resource_id=theirs))
            db.commit()
        finally:
            db.close()
        return mine, theirs

    @pytest.mark.parametrize("path", PATHS)
    def test_the_owner_reads_only_their_own_audit_log(self, rows, path):
        mine, theirs = rows
        _, headers = _member(TENANT_A)
        response = http.get(path, headers={**headers, "X-Tenant-Id": TENANT_A})
        assert response.status_code == 200, response.text[:200]
        assert _contains(response, mine) and not _contains(response, theirs)

    @pytest.mark.parametrize("path", PATHS)
    @pytest.mark.parametrize("attack", [
        {"X-LumenAI-Tenant-Id": TENANT_A, "X-Tenant-Id": TENANT_B},
        {"X-Tenant-Id": TENANT_A, "X-LumenAI-Tenant-Id": TENANT_B},
        {"X-Tenant-Id": TENANT_B},
        {"X-LumenAI-Tenant-Id": TENANT_B},
    ], ids=["split-verified-A-data-B", "split-reversed", "names-B", "names-B-lumenai"])
    def test_no_header_combination_reads_tenant_b(self, rows, path, attack):
        _, theirs = rows
        _, headers = _member(TENANT_A)
        response = http.get(path, headers={**headers, **attack})
        assert response.status_code == 403, response.text[:200]
        assert not _contains(response, theirs)


class TestTenantAnalyticsAreTenantScoped:
    """AW-01: ``/api/tenant-analytics/*`` checked a global role and used the header."""

    PATHS = ["/api/tenant-analytics/summary", "/api/tenant-analytics/export.json",
             "/api/tenant-analytics/export.csv", "/api/tenant-analytics/export.xlsx",
             "/api/tenant-analytics/export.bundle.zip"]

    @pytest.fixture
    def inspections(self):
        mine, theirs = f"b2-vendor-mine-{uuid.uuid4().hex[:8]}", f"b2-vendor-theirs-{uuid.uuid4().hex[:8]}"
        db = SessionLocal()
        try:
            db.add(models.Inspection(file_name="a.bin", tenant_id=TENANT_A, tenant_name="A",
                                     vendor_name=mine, site_name="a-site", status="completed"))
            db.add(models.Inspection(file_name="b.bin", tenant_id=TENANT_B, tenant_name="B",
                                     vendor_name=theirs, site_name="b-site", status="completed"))
            db.commit()
        finally:
            db.close()
        return mine, theirs

    @pytest.mark.parametrize("path", PATHS)
    def test_a_member_sees_their_own_tenant_without_naming_it(self, inspections, path):
        """The web client sends no tenant header."""
        mine, theirs = inspections
        _, headers = _member(TENANT_A)
        response = http.get(path, headers=headers)
        assert response.status_code == 200, response.text[:200]
        assert _contains(response, mine) and not _contains(response, theirs)

    @pytest.mark.parametrize("path", PATHS)
    @pytest.mark.parametrize("header", ["X-Tenant-Id", "X-LumenAI-Tenant-Id"])
    def test_naming_tenant_b_is_refused(self, inspections, path, header):
        _, theirs = inspections
        _, headers = _member(TENANT_A)
        response = http.get(path, headers={**headers, header: TENANT_B})
        assert response.status_code == 403
        assert not _contains(response, theirs)

    @pytest.mark.parametrize("path", PATHS)
    def test_a_manager_with_no_membership_sees_no_tenant(self, inspections, path):
        """Before: any user with the global manager role read any tenant by header,
        and ``default-tenant`` with none."""
        user = f"b2-outsider-{uuid.uuid4().hex[:8]}@example.com"
        db = SessionLocal()
        try:
            db.add(UserRoleAssignment(username=user, role="spd_manager", assigned_by="p472-03-batch2"))
            db.commit()
        finally:
            db.close()
        headers = {"Authorization": f"Bearer {_make_token(user)}"}
        for extra in ({}, {"X-Tenant-Id": TENANT_B}, {"X-Tenant-Id": TENANT_A}):
            assert http.get(path, headers={**headers, **extra}).status_code == 403


class TestAuditAttributionComesFromTheVerifiedIdentity:
    def test_a_write_is_recorded_under_the_verified_tenant_and_user(self):
        user, headers = _member(TENANT_A)
        artifact = f"b2-artifact-{uuid.uuid4().hex[:8]}"
        response = http.post("/api/legal-hold", headers={
            **headers, "X-Tenant-Id": TENANT_A,
            # Everything below is client-controlled and must not reach the audit row.
            "X-Tenant-Name": "Tenant B Hospital", "X-LumenAI-Actor": "someone-else@example.com",
            "X-LumenAI-Role": "enterprise_admin",
        }, json={"artifact_type": artifact, "legal_hold_enabled": True, "notes": "batch 2"})
        assert response.status_code == 200, response.text[:300]

        db = SessionLocal()
        try:
            rows = db.query(AuditLog).filter(AuditLog.actor_email == user).all()
            assert rows, "the write left no audit row for the verified user"
            for row in rows:
                assert row.tenant_id == TENANT_A
                assert "Tenant B Hospital" not in (row.tenant_name or "")
                assert row.actor_role == "tenant_admin"         # the membership role, not the header
            assert db.query(AuditLog).filter(AuditLog.actor_email == "someone-else@example.com").count() == 0
        finally:
            db.close()

    def test_a_refused_write_stores_nothing(self):
        _, headers = _member(TENANT_A)
        artifact = f"b2-artifact-{uuid.uuid4().hex[:8]}"
        response = http.post("/api/legal-hold", headers={
            **headers, "X-LumenAI-Tenant-Id": TENANT_A, "X-Tenant-Id": TENANT_B,
        }, json={"artifact_type": artifact, "legal_hold_enabled": True})
        assert response.status_code == 403
        db = SessionLocal()
        try:
            assert db.query(models.RetentionPolicy).filter(
                models.RetentionPolicy.artifact_type == artifact).count() == 0
        finally:
            db.close()


# ══ AW-12 — a tenant-triggered job that covered every tenant ══════════════════
# Found by ``test_the_owner_and_a_selected_membership_are_served`` above: a tenant
# administrator's "run SLA scan" evaluated every tenant with an enabled policy,
# wrote SLA events in each of them and returned all of their results.

from app.models.governance_sla_event import GovernanceSlaEvent  # noqa: E402
from app.models.governance_sla_policy import GovernanceSlaPolicy  # noqa: E402

SLA_SCAN_ROUTES = [
    "/api/governance-sla-scanner/run",
    "/api/governance-command-center/actions/run-sla-scan",
    "/api/customer-operations-hub/actions/run-sla-scan",
]


class TestSlaScanIsLimitedToTheCallersTenant:
    @pytest.fixture
    def policies(self):
        """Both tenants have an enabled policy, so the old all-tenant scan includes both."""
        db = SessionLocal()
        try:
            for tenant in (TENANT_A, TENANT_B):
                if not db.query(GovernanceSlaPolicy).filter(GovernanceSlaPolicy.tenant_id == tenant).count():
                    db.add(GovernanceSlaPolicy(tenant_id=tenant, tenant_name=tenant,
                                               policy_key="pending_packet_release", is_enabled=True))
            db.commit()
        finally:
            db.close()

    @staticmethod
    def _events(tenant: str) -> int:
        db = SessionLocal()
        try:
            return db.query(GovernanceSlaEvent).filter(GovernanceSlaEvent.tenant_id == tenant).count()
        finally:
            db.close()

    @pytest.mark.parametrize("path", SLA_SCAN_ROUTES)
    def test_a_tenant_administrators_scan_evaluates_and_returns_only_their_tenant(self, policies, caller, path):
        _, headers = _member(TENANT_A)
        before = self._events(TENANT_B)
        caller.captured, caller.capturing = [], True
        try:
            response = http.post(path, headers={**headers, "X-Tenant-Id": TENANT_A})
        finally:
            caller.capturing = False
        assert response.status_code == 200, response.text[:300]
        body = response.json()
        assert TENANT_B not in response.text
        assert [r["tenant_id"] for r in body["results"]] == [TENANT_A] and body["tenant_count"] == 1
        assert _bound(caller.captured, TENANT_B) == []
        assert self._events(TENANT_B) == before

    def test_the_status_route_shows_only_the_callers_part_of_a_platform_run(self, policies):
        from app.governance_sla_scanner import run_scanner_once

        scheduled = run_scanner_once()                 # the scheduled platform job: no tenant
        assert {TENANT_A, TENANT_B} <= {r["tenant_id"] for r in scheduled["results"]}

        _, headers = _member(TENANT_A)
        response = http.get("/api/governance-sla-scanner/status", headers={**headers, "X-Tenant-Id": TENANT_A})
        assert response.status_code == 200
        assert TENANT_B not in response.text
        assert all(r["tenant_id"] == TENANT_A for r in response.json()["last_run"].get("results", []))

    def test_one_tenants_manual_run_is_not_shown_to_another(self, policies):
        _, a = _member(TENANT_A)
        assert http.post(SLA_SCAN_ROUTES[0], headers={**a, "X-Tenant-Id": TENANT_A}).status_code == 200
        _, b = _member(TENANT_B)
        status = http.get("/api/governance-sla-scanner/status", headers={**b, "X-Tenant-Id": TENANT_B})
        assert status.status_code == 200 and TENANT_A not in status.text


# ══ AW-01 — ML images and operations: the tenant header behind a global role ══

from app.models.p22_operations import OperationsWorkflow, WorkflowExecution  # noqa: E402
from app.models.retained_image import RetainedImage  # noqa: E402


class TestMlImagesAreTenantScoped:
    @pytest.fixture
    def images(self):
        mine, theirs = f"b2-img-mine-{uuid.uuid4().hex[:8]}", f"b2-img-theirs-{uuid.uuid4().hex[:8]}"
        db = SessionLocal()
        try:
            own = RetainedImage(tenant_id=TENANT_A, deident_name=mine, instrument_type="scissors",
                                content_type="image/png", size_bytes=4, sha256="a" * 64, image_bytes=b"AAAA")
            other = RetainedImage(tenant_id=TENANT_B, deident_name=theirs, instrument_type="scissors",
                                  content_type="image/png", size_bytes=10, sha256="b" * 64,
                                  image_bytes=b"B-PRIVATE!")
            db.add_all([own, other])
            db.commit()
            return mine, theirs, own.id, other.id
        finally:
            db.close()

    def test_a_member_lists_only_their_own_images(self, images):
        mine, theirs, _, _ = images
        _, headers = _member(TENANT_A)
        response = http.get("/api/ml/images", headers=headers)
        assert response.status_code == 200, response.text[:200]
        assert mine in response.text and theirs not in response.text

    @pytest.mark.parametrize("header", ["X-Tenant-Id", "X-LumenAI-Tenant-Id"])
    def test_naming_tenant_b_does_not_list_its_images(self, images, header):
        _, theirs, _, _ = images
        _, headers = _member(TENANT_A)
        response = http.get("/api/ml/images", headers={**headers, header: TENANT_B})
        assert response.status_code == 403 and theirs not in response.text

    def test_tenant_b_image_bytes_cannot_be_fetched_by_id(self, images):
        _, _, own_id, other_id = images
        _, headers = _member(TENANT_A)
        assert http.get(f"/api/ml/images/{own_id}/bytes", headers=headers).content == b"AAAA"
        for extra in ({}, {"X-Tenant-Id": TENANT_B}, {"X-LumenAI-Tenant-Id": TENANT_B}):
            response = http.get(f"/api/ml/images/{other_id}/bytes", headers={**headers, **extra})
            assert response.status_code in (403, 404)
            assert b"B-PRIVATE!" not in response.content

    def test_tenant_b_image_cannot_be_labelled(self, images):
        from app.models.retained_image import ImageLabel

        _, _, _, other_id = images
        _, headers = _member(TENANT_A)
        for extra in ({}, {"X-Tenant-Id": TENANT_B}):
            response = http.post(f"/api/ml/images/{other_id}/labels", headers={**headers, **extra},
                                 json={"finding_type": "corrosion"})
            assert response.status_code in (403, 404)
        db = SessionLocal()
        try:
            assert db.query(ImageLabel).filter(ImageLabel.image_id == other_id).count() == 0
        finally:
            db.close()

    def test_the_dataset_export_holds_only_the_callers_images(self, images):
        mine, theirs, _, _ = images
        _, headers = _member(TENANT_A)
        response = http.get("/api/ml/dataset/export", headers=headers)
        assert response.status_code == 200, response.text[:200]
        assert not _contains(response, theirs) and TENANT_B not in response.text


class TestOperationsAreTenantScoped:
    @pytest.fixture
    def workflows(self):
        mine, theirs = f"b2-wf-mine-{uuid.uuid4().hex[:8]}", f"b2-wf-theirs-{uuid.uuid4().hex[:8]}"
        db = SessionLocal()
        try:
            own = OperationsWorkflow(tenant_id=TENANT_A, name=mine, workflow_type="capa", created_by="a")
            other = OperationsWorkflow(tenant_id=TENANT_B, name=theirs, workflow_type="capa", created_by="b")
            db.add_all([own, other])
            db.flush()
            execution = WorkflowExecution(tenant_id=TENANT_B, workflow_id=other.id, resource_type="capa",
                                          resource_id="b-capa-1", triggered_by="b", status="awaiting_approval")
            db.add(execution)
            db.commit()
            return mine, theirs, other.id, execution.id
        finally:
            db.close()

    def test_a_manager_lists_only_their_own_workflows(self, workflows):
        mine, theirs, _, _ = workflows
        _, headers = _member(TENANT_A, global_role="manager")
        response = http.get("/api/operations/workflows", headers=headers)
        assert response.status_code == 200, response.text[:200]
        assert mine in response.text and theirs not in response.text

    @pytest.mark.parametrize("header", ["X-Tenant-Id", "X-LumenAI-Tenant-Id"])
    def test_naming_tenant_b_does_not_list_its_workflows(self, workflows, header):
        _, theirs, _, _ = workflows
        _, headers = _member(TENANT_A, global_role="manager")
        response = http.get("/api/operations/workflows", headers={**headers, header: TENANT_B})
        assert response.status_code == 403 and theirs not in response.text

    def test_a_manager_with_no_membership_reaches_no_tenant(self, workflows):
        _, theirs, _, _ = workflows
        user = f"b2-ops-outsider-{uuid.uuid4().hex[:8]}@example.com"
        db = SessionLocal()
        try:
            db.add(UserRoleAssignment(username=user, role="manager", assigned_by="p472-03-batch2"))
            db.commit()
        finally:
            db.close()
        headers = {"Authorization": f"Bearer {_make_token(user)}"}
        for extra in ({}, {"X-Tenant-Id": TENANT_B}):
            response = http.get("/api/operations/workflows", headers={**headers, **extra})
            assert response.status_code == 403 and theirs not in response.text

    def test_tenant_b_execution_cannot_be_approved_by_id(self, workflows):
        _, _, _, execution_id = workflows
        _, headers = _member(TENANT_A, global_role="manager")
        body = {"approved_by": "attacker", "approved": True}
        for extra in ({}, {"X-Tenant-Id": TENANT_B}, {"X-LumenAI-Tenant-Id": TENANT_A, "X-Tenant-Id": TENANT_B}):
            response = http.post(f"/api/operations/executions/{execution_id}/approve",
                                 headers={**headers, **extra}, json=body)
            assert response.status_code in (403, 404)
        db = SessionLocal()
        try:
            execution = db.get(WorkflowExecution, execution_id)
            assert execution.status == "awaiting_approval" and execution.approved_by is None
        finally:
            db.close()

    def test_tenant_b_workflow_steps_cannot_be_read_or_added_by_id(self, workflows):
        _, _, workflow_id, _ = workflows
        _, headers = _member(TENANT_A, global_role="manager")
        assert http.get(f"/api/operations/workflows/{workflow_id}/steps", headers=headers).status_code == 404
        added = http.post(f"/api/operations/workflows/{workflow_id}/steps", headers=headers,
                          json={"step_number": 1, "name": "x", "step_type": "review"})
        assert added.status_code in (404, 422)

    def test_an_operations_write_is_attributed_to_the_authenticated_user(self):
        """These audit rows used to say actor ``system`` / role ``admin`` for everyone."""
        user, headers = _member(TENANT_A, global_role="manager")
        name = f"b2-wf-{uuid.uuid4().hex[:8]}"
        response = http.post("/api/operations/workflows", headers={**headers, "X-LumenAI-Actor": "spoofed"},
                             json={"name": name, "workflow_type": "capa", "created_by": "whoever"})
        assert response.status_code == 201, response.text[:300]
        db = SessionLocal()
        try:
            rows = db.query(AuditLog).filter(AuditLog.actor_email == user,
                                             AuditLog.action_type == "workflow_created").all()
            assert len(rows) == 1 and rows[0].tenant_id == TENANT_A and rows[0].actor_role == "manager"
        finally:
            db.close()


# ══ AW-13 — participant identities in cross-hospital trend alerts ═════════════
# Found by the per-route test: a request made in one tenant carried another
# tenant's id. The shared alert row stores which organisations were notified and
# which acknowledged, and the routes returned those lists to every caller.

from app.models.federated_horizon import EmergingTrendAlert  # noqa: E402
import json as _json  # noqa: E402


class TestTrendAlertsDoNotNameOtherOrganisations:
    @pytest.fixture
    def alert(self):
        db = SessionLocal()
        try:
            row = EmergingTrendAlert(
                trend_type="new_corrosion_pattern", description=f"b2 alert {uuid.uuid4().hex[:8]}",
                evidence_json="[]", tenant_count=3, severity="medium",
                notified_tenant_ids_json=_json.dumps([TENANT_A, TENANT_B, TENANT_C]),
                acknowledged_tenant_ids_json=_json.dumps([TENANT_B]),
            )
            db.add(row)
            db.commit()
            return row.id
        finally:
            db.close()

    @staticmethod
    def _mine(body: dict, alert_id: int) -> dict:
        return next(t for t in body["trends"] if t["id"] == alert_id)

    @pytest.mark.parametrize("params", [{}, {"mine_only": "true"}])
    def test_listing_does_not_name_other_organisations(self, alert, params):
        _, headers = _member(TENANT_A)
        response = http.get("/api/horizon/emerging-trends", headers=headers, params=params)
        assert response.status_code == 200, response.text[:300]
        assert TENANT_B not in response.text and TENANT_C not in response.text
        trend = self._mine(response.json(), alert)
        assert trend["notified_organization_count"] == 3 and trend["acknowledged_organization_count"] == 1
        assert "notified_tenant_ids_json" not in trend and "acknowledged_tenant_ids_json" not in trend

    def test_a_caller_learns_only_their_own_status(self, alert):
        _, headers = _member(TENANT_A)
        trend = self._mine(http.get("/api/horizon/emerging-trends", headers=headers,
                                    params={"mine_only": "true"}).json(), alert)
        assert trend["notified"] is True and trend["acknowledged"] is False

    def test_acknowledging_does_not_return_who_else_acknowledged(self, alert):
        _, headers = _member(TENANT_A)
        response = http.post(f"/api/horizon/emerging-trends/{alert}/acknowledge", headers=headers)
        assert response.status_code == 200, response.text[:300]
        assert TENANT_B not in response.text and TENANT_C not in response.text
        body = response.json()
        assert body["acknowledged"] is True and body["acknowledged_organization_count"] == 2
        db = SessionLocal()
        try:
            stored = _json.loads(db.get(EmergingTrendAlert, alert).acknowledged_tenant_ids_json)
            assert sorted(stored) == sorted([TENANT_A, TENANT_B])      # the record itself is intact
        finally:
            db.close()

    def test_detection_does_not_return_the_participant_list(self, alert):
        _, headers = _member(TENANT_A)
        response = http.post("/api/horizon/emerging-trends/detect", headers=headers)
        assert response.status_code == 200, response.text[:300]
        assert TENANT_B not in response.text and TENANT_C not in response.text
