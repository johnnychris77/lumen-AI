"""P472-03 application-wide tenant-isolation sweep — the runner.

NOT collected by the normal suite (the file name does not match ``test_*.py``).
``test_p472_03_application_wide_isolation.py`` runs it in a subprocess against a
throw-away database and compares what it observes with the committed findings
register. It can also be run by hand::

    P472_SWEEP_OUT=/tmp/sweep.json DATABASE_URL=sqlite:////tmp/sweep.db \
        python -m pytest tests/tenant_isolation_sweep_runner.py -q -p no:cacheprovider

What it does, for EVERY mounted route:

1. builds a schema-valid request from the OpenAPI description;
2. sends it as a verified member of tenant A (trying several role profiles
   until one is allowed), recording the SQL the request executes;
3. sends it again while naming tenant B through every channel the route
   exposes — tenant headers (including split-header combinations), query
   parameters, path parameters and body fields — and as unauthenticated,
   invalid-token and expired-token callers, and as a user who belongs to both
   tenants naming a third.

The oracle is the database, not the status code: a request made by tenant A is
a cross-tenant hit when SQL executed on its behalf binds tenant B's id against
any table other than the membership table used to check authorization. That
holds whether or not tenant B has data, and it separates "the route accepts a
tenant parameter" from "the route used someone else's tenant as its scope".

Everything is synthetic. Outbound network connections are blocked.
"""
from __future__ import annotations

import inspect
import json
import os
import re
import signal
import socket
import threading
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

TENANT_A, TENANT_B, TENANT_D = "sweep-tenant-alpha", "sweep-tenant-bravo", "sweep-tenant-delta"
# (global role, tenant-membership role). The global role "admin" is the documented
# platform administrator (app/security/tenant_context.py) and is deliberately absent:
# the sweep asks what an ordinary tenant user can reach.
PROFILES = [
    ("spd_manager", "spd_manager"), ("spd_manager", "tenant_admin"), ("executive", "admin"),
    ("operator", "operator"), ("vendor_user", "viewer"), ("viewer", "viewer"),
]
REFUSED = {401, 403}
MEMBERSHIP_TABLES = {"tenant_memberships"}
REQUEST_TIMEOUT_SECONDS = 30

_AUTH_GUARD_RE = re.compile(
    r"(?:^|[^A-Za-z0-9_])(_?require_(?!tier\b)[a-z_]+|assert_tenant_membership|authorized_tenant|"
    r"get_current_user|get_auth_context|resolve_verified_tenant|_resolve_user_email_from_token)\s*\(")
# ``current_user.tenant_id or <request header / literal>``: the tenant falls back to
# an unverified value whenever the principal has no single verified tenant.
_FALLBACK_RE = re.compile(r'getattr\(\w+,\s*"tenant_id",\s*None\)\s*or\s|\.tenant_id\s+or\s+get_request_tenant_id')


def _module_source(module_name: str) -> str:
    import importlib

    try:
        return inspect.getsource(importlib.import_module(module_name))
    except (OSError, TypeError, ImportError):
        return ""


_TABLE_RES = {
    "write": [re.compile(r'^\s*INSERT\s+INTO\s+"?(\w+)"?', re.I), re.compile(r'^\s*UPDATE\s+"?(\w+)"?', re.I),
              re.compile(r'^\s*DELETE\s+FROM\s+"?(\w+)"?', re.I)],
    "read": [re.compile(r'\bFROM\s+"?(\w+)"?', re.I), re.compile(r'\bJOIN\s+"?(\w+)"?', re.I)],
}


# ── SQL capture ───────────────────────────────────────────────────────────────

_captured: list[tuple[str, object]] = []
_capturing = threading.Event()


def _on_sql(_conn, _cursor, statement, parameters, _context, _executemany):
    if _capturing.is_set():
        _captured.append((statement, parameters))


event.listen(Engine, "before_cursor_execute", _on_sql)


def _values(parameters):
    if isinstance(parameters, dict):
        for value in parameters.values():
            yield from _values(value)
    elif isinstance(parameters, (list, tuple)):
        for value in parameters:
            yield from _values(value)
    elif isinstance(parameters, str):
        yield parameters


def _statement_tables(statement: str) -> tuple[str, set[str]]:
    for pattern in _TABLE_RES["write"]:
        match = pattern.search(statement)
        if match:
            return "write", {match.group(1).lower()}
    tables = {m.group(1).lower() for pattern in _TABLE_RES["read"] for m in pattern.finditer(statement)}
    return "read", tables


def _scope_hits(capture, tenant: str) -> dict[str, list[str]]:
    """Tables on which a statement bound ``tenant`` (membership checks excluded)."""
    hits: dict[str, set[str]] = {"read": set(), "write": set()}
    for statement, parameters in capture:
        if tenant not in statement and not any(tenant in value for value in _values(parameters)):
            continue
        kind, tables = _statement_tables(statement)
        hits[kind] |= tables - MEMBERSHIP_TABLES
    return {kind: sorted(tables) for kind, tables in hits.items()}


def _tables_touched(capture) -> dict[str, list[str]]:
    touched: dict[str, set[str]] = {"read": set(), "write": set()}
    for statement, _ in capture:
        kind, tables = _statement_tables(statement)
        touched[kind] |= tables
    return {kind: sorted(tables) for kind, tables in touched.items()}


def _unscoped_tenant_tables(capture, tenant_tables: set[str]) -> list[str]:
    """Tenant tables read, updated or deleted by a statement whose WHERE clause
    does not mention ``tenant_id``. A lead for manual review, not a finding."""
    unscoped: set[str] = set()
    for statement, _ in capture:
        kind, tables = _statement_tables(statement)
        if kind == "write" and statement.lstrip().upper().startswith("INSERT"):
            continue
        where = statement.upper().split(" WHERE ", 1)
        scoped = len(where) == 2 and "TENANT_ID" in where[1]
        if not scoped:
            unscoped |= tables & tenant_tables
    return sorted(unscoped - MEMBERSHIP_TABLES)


# ── request synthesis from OpenAPI ────────────────────────────────────────────

def _is_tenant_name(name: str) -> bool:
    lowered = name.lower().replace("-", "_")
    return lowered in {"tenant", "tenantid"} or (
        "tenant" in lowered and lowered.endswith(("_id", "_id_filter", "tenant")))


class _Spec:
    def __init__(self, spec: dict):
        self.spec = spec
        self.schemas = spec.get("components", {}).get("schemas", {})

    def resolve(self, schema: dict) -> dict:
        seen = 0
        while "$ref" in schema and seen < 10:
            schema = self.schemas[schema["$ref"].split("/")[-1]]
            seen += 1
        return schema

    def value(self, schema: dict, depth: int = 0):
        schema = self.resolve(schema)
        for key in ("anyOf", "oneOf"):
            if key in schema:
                options = [s for s in schema[key] if self.resolve(s).get("type") != "null"]
                return self.value(options[0], depth + 1) if options else None
        if "allOf" in schema:
            return self.value(schema["allOf"][0], depth + 1)
        if "enum" in schema:
            return schema["enum"][0]
        if "const" in schema:
            return schema["const"]
        kind = schema.get("type")
        if kind == "string":
            fmt = schema.get("format")
            if fmt == "date-time":
                return "2026-11-01T00:00:00"
            if fmt == "date":
                return "2026-11-01"
            if fmt == "uuid":
                return "00000000-0000-4000-8000-000000000001"
            if fmt == "email":
                return "sweep@example.com"
            return "sweep"[: schema.get("maxLength", 64)].ljust(schema.get("minLength", 0), "x")
        if kind == "integer":
            return max(1, int(schema.get("minimum", 1)))
        if kind == "number":
            return float(max(1, schema.get("minimum", 1)))
        if kind == "boolean":
            return False
        if kind == "array":
            item = self.value(schema.get("items", {}), depth + 1) if depth < 4 else None
            return [item] if schema.get("minItems", 0) and item is not None else []
        if kind == "object" or "properties" in schema:
            return self.body(schema, None, depth + 1)[0]
        return None

    def body(self, schema: dict, tenant: str | None, depth: int = 0) -> tuple[dict, list[str]]:
        """A minimal valid object. ``tenant``: value for every tenant-id field
        (``None`` = leave optional ones out). Returns (object, tenant field names)."""
        schema = self.resolve(schema)
        required = set(schema.get("required", []))
        out: dict = {}
        tenant_fields: list[str] = []
        for name, prop in (schema.get("properties") or {}).items():
            resolved = self.resolve(prop)
            types = {resolved.get("type")} | {
                self.resolve(o).get("type") for o in resolved.get("anyOf", []) + resolved.get("oneOf", [])}
            if _is_tenant_name(name) and "string" in types:
                tenant_fields.append(name)
                if tenant is not None:
                    out[name] = tenant
                elif name in required:
                    out[name] = TENANT_A
                continue
            if name in required and depth < 5:
                out[name] = self.value(prop, depth + 1)
        return out, tenant_fields


class _Plan:
    """Everything needed to call one route in any variant."""

    def __init__(self, spec: _Spec, method: str, path: str):
        operation = spec.spec["paths"].get(path, {}).get(method.lower(), {})
        self.method, self.path = method, path
        self.path_params, self.query, self.tenant_query, self.tenant_path = {}, {}, [], []
        self.required_tenant_query: list[str] = []
        for parameter in operation.get("parameters", []):
            name, where = parameter["name"], parameter["in"]
            schema = parameter.get("schema", {})
            if where == "path":
                if _is_tenant_name(name):
                    self.tenant_path.append(name)
                else:
                    value = spec.value(schema)
                    self.path_params[name] = "1" if isinstance(value, (int, float)) else str(value or "sweep")
            elif where == "query":
                if _is_tenant_name(name):
                    self.tenant_query.append(name)
                    if parameter.get("required"):
                        self.required_tenant_query.append(name)
                elif parameter.get("required"):
                    self.query[name] = spec.value(schema)
        self.body_schema, self.body_kind = None, "none"
        content = (operation.get("requestBody") or {}).get("content", {})
        if "application/json" in content:
            self.body_schema, self.body_kind = content["application/json"].get("schema", {}), "json"
        elif content:
            self.body_kind = "non-json"
        self.spec = spec
        self.tenant_body = []
        if self.body_schema is not None:
            resolved = spec.resolve(self.body_schema)
            if resolved.get("type") == "object" or "properties" in resolved:
                self.tenant_body = spec.body(resolved, None)[1]

    def request(self, *, path_tenant: str, query_tenant: str | None, body_tenant: str | None):
        url = self.path
        for name, value in self.path_params.items():
            url = url.replace("{" + name + "}", value)
        for name in self.tenant_path:
            url = url.replace("{" + name + "}", path_tenant)
        url = re.sub(r"\{[^}:]+(:[^}]+)?\}", "sweep", url)        # anything the spec did not describe
        params = dict(self.query)
        params.update({name: TENANT_A for name in self.required_tenant_query})
        if query_tenant is not None:
            params.update({name: query_tenant for name in self.tenant_query})
        body = None
        if self.body_kind == "json":
            resolved = self.spec.resolve(self.body_schema)
            if resolved.get("type") == "object" or "properties" in resolved:
                body = self.spec.body(resolved, body_tenant)[0]
            else:
                body = self.spec.value(resolved)
        return url, params, body


# ── identities ────────────────────────────────────────────────────────────────

def _token(user: str, *, expired: bool = False) -> str:
    from app.routers.auth_simple import ALGORITHM, SECRET_KEY, jwt

    now = datetime.now(timezone.utc)
    issued = now - timedelta(hours=3) if expired else now
    payload = {"sub": user, "iat": int(issued.timestamp()),
               "exp": int((issued + timedelta(hours=1)).timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _seed_identities() -> dict:
    from app.db import models
    from app.db.session import SessionLocal
    from app.models.user_role_assignment import UserRoleAssignment

    db = SessionLocal()
    users: dict = {"a": {}, "b": {}}
    try:
        def member(user: str, tenant: str, role: str) -> None:
            db.add(models.TenantMembership(tenant_id=tenant, user_email=user, role=role, is_enabled=True))

        for index, (global_role, tenant_role) in enumerate(PROFILES):
            for key, tenant in (("a", TENANT_A), ("b", TENANT_B)):
                user = f"sweep-{key}-{index}@example.com"
                db.add(UserRoleAssignment(username=user, role=global_role, assigned_by="sweep"))
                member(user, tenant, tenant_role)
                users[key][index] = user
        users["none"] = {}
        for index, (global_role, _tenant_role) in enumerate(PROFILES):
            user = f"sweep-nomember-{index}@example.com"
            db.add(UserRoleAssignment(username=user, role=global_role, assigned_by="sweep"))
            users["none"][index] = user
        both = "sweep-both@example.com"
        db.add(UserRoleAssignment(username=both, role="spd_manager", assigned_by="sweep"))
        member(both, TENANT_A, "spd_manager")
        member(both, TENANT_B, "spd_manager")
        users["both"] = both
        db.commit()
    finally:
        db.close()
    return users


# ── the sweep ─────────────────────────────────────────────────────────────────

class _Timeout(Exception):
    pass


def _alarm(_signum, _frame):
    raise _Timeout()


def _block_outbound_network(monkeypatch) -> None:
    real_connect = socket.socket.connect

    def guarded(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if self.family == socket.AF_UNIX or str(host) in {"127.0.0.1", "::1", "localhost"}:
            return real_connect(self, address, *args, **kwargs)
        raise OSError(f"outbound network blocked during the tenant-isolation sweep: {host!r}")

    monkeypatch.setattr(socket.socket, "connect", guarded)


def test_run_sweep(monkeypatch):
    if os.environ.get("P472_SWEEP_PREPARE_ONLY"):
        return      # the autouse fixtures have created the schema; that is all this run is for
    out_path = os.environ.get("P472_SWEEP_OUT")
    assert out_path, "set P472_SWEEP_OUT; this runner is not part of the normal suite"
    _block_outbound_network(monkeypatch)

    from app.db.base import Base
    from app.limiter import limiter
    from app.main import app

    tenant_tables = {t.name.lower() for t in Base.metadata.sorted_tables if "tenant_id" in t.c}
    users = _seed_identities()
    client = TestClient(app, raise_server_exceptions=False)
    spec = _Spec(app.openapi())
    signal.signal(signal.SIGALRM, _alarm)

    def call(plan: _Plan, headers: dict, *, path_tenant=TENANT_A, query_tenant=None, body_tenant=None,
             watch: str | None = None) -> dict:
        url, params, body = plan.request(path_tenant=path_tenant, query_tenant=query_tenant, body_tenant=body_tenant)
        if limiter is not None:
            try:
                limiter.reset()
            except Exception:  # noqa: BLE001 - not every limiter backend can reset
                pass
        del _captured[:]
        _capturing.set()
        signal.alarm(REQUEST_TIMEOUT_SECONDS)
        try:
            response = client.request(plan.method, url, headers=headers, params=params or None, json=body)
            status, text = response.status_code, response.text[:200000]
        except _Timeout:
            status, text = -1, ""
        except Exception as exc:  # noqa: BLE001 - a crashing handler is a result, not a sweep failure
            status, text = -2, type(exc).__name__
        finally:
            signal.alarm(0)
            _capturing.clear()
        capture = list(_captured)
        result = {"status": status}
        if watch:
            hits = _scope_hits(capture, watch)
            if hits["read"]:
                result["read"] = hits["read"]
            if hits["write"]:
                result["write"] = hits["write"]
            if watch in text:
                result["echo"] = True
        result["_capture"] = capture
        if not headers.get("Authorization") and 200 <= status < 300:
            # A request with NO credentials that succeeds: which tenant tables did it touch?
            touched = _tables_touched(capture)
            public_reads = sorted(set(touched["read"]) & tenant_tables)
            public_writes = sorted(set(touched["write"]) & tenant_tables)
            if public_reads:
                result["public_reads"] = public_reads
            if public_writes:
                result["public_writes"] = public_writes
        return result

    def deps(dependant, acc):
        for sub in dependant.dependencies:
            if sub.call is not None:
                acc.add(getattr(sub.call, "__name__", type(sub.call).__name__))
            deps(sub, acc)
        return acc

    # Optional sharding ("index/count"): each shard sweeps every count-th route in
    # its own database, so several can run in parallel.
    shard_index, shard_count = (int(x) for x in os.environ.get("P472_SWEEP_SHARD", "0/1").split("/"))

    records = []
    module_sources: dict[str, str] = {}
    seen: dict[tuple[str, str], str] = {}
    routes = [r for r in app.routes if isinstance(r, APIRoute)]
    position = -1
    for route in routes:
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            position += 1
            handler = f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"
            record: dict = {"index": position, "method": method, "path": route.path,
                            "module": route.endpoint.__module__, "handler": route.endpoint.__qualname__}
            if (method, route.path) in seen:
                record["shadowed_by"] = seen[(method, route.path)]
                if position % shard_count == shard_index:
                    records.append(record)
                continue
            seen[(method, route.path)] = handler
            if position % shard_count != shard_index:
                continue
            try:
                source = inspect.getsource(route.endpoint)
            except (OSError, TypeError):
                source = ""
            record["deps"] = sorted(deps(route.dependant, set()) - {"get_db"})
            module_source = module_sources.setdefault(
                route.endpoint.__module__, _module_source(route.endpoint.__module__))
            record["static"] = {
                "handler_reads_raw_tenant_header": "get_request_tenant_id(" in source,
                "module_header_fallback": bool(_FALLBACK_RE.search(module_source)),
                "module_reads_raw_tenant_header": "get_request_tenant_id(" in module_source,
                "handler_uses_authorized_tenant": "authorized_tenant(" in source,
            }
            record["guards"] = sorted({m.group(1) for m in _AUTH_GUARD_RE.finditer(source)})
            plan = _Plan(spec, method, route.path)
            record["tenant_inputs"] = {
                "path": plan.tenant_path, "query": plan.tenant_query, "body": plan.tenant_body,
                "header_dependency": "resolve_tenant" in record["deps"]}
            record["body_kind"] = plan.body_kind

            def hdr(user: str, **extra) -> dict:
                return {"Authorization": f"Bearer {_token(user)}", **extra}

            # 1. Unauthenticated, invalid and expired callers (naming tenant B everywhere).
            results: dict = {}
            results["anonymous"] = call(plan, {}, watch=TENANT_B)
            results["anonymous+claims"] = call(
                plan, {"X-Tenant-Id": TENANT_B, "X-LumenAI-Tenant-Id": TENANT_B}, path_tenant=TENANT_B,
                query_tenant=TENANT_B, body_tenant=TENANT_B, watch=TENANT_B)
            results["invalid-token"] = call(
                plan, {"Authorization": "Bearer not-a-jwt", "X-Tenant-Id": TENANT_B}, path_tenant=TENANT_B,
                query_tenant=TENANT_B, body_tenant=TENANT_B, watch=TENANT_B)
            results["expired-token"] = call(
                plan, {"Authorization": f"Bearer {_token(users['b'][0], expired=True)}", "X-Tenant-Id": TENANT_B},
                path_tenant=TENANT_B, query_tenant=TENANT_B, body_tenant=TENANT_B, watch=TENANT_B)

            # 2. Baseline: a verified member of tenant A, in the first profile that is let in.
            profile, baseline = None, None
            for index in range(len(PROFILES)):
                attempt = call(plan, hdr(users["a"][index], **{"X-Tenant-Id": TENANT_A}), watch=TENANT_A)
                if baseline is None or (baseline["status"] in REFUSED and attempt["status"] not in REFUSED):
                    profile, baseline = index, attempt
                if attempt["status"] not in REFUSED:
                    break
            capture = baseline.pop("_capture")
            touched = _tables_touched(capture)
            record["profile"] = "/".join(PROFILES[profile])
            record["baseline"] = {
                "status": baseline["status"], "reads": touched["read"], "writes": touched["write"],
                "membership_checked": bool(set(touched["read"]) & MEMBERSHIP_TABLES),
                "own_tenant_bound": bool(baseline.get("read") or baseline.get("write")),
                "unscoped_tenant_tables": _unscoped_tenant_tables(capture, tenant_tables),
            }
            user_a = users["a"][profile]

            # 3. Tenant A naming tenant B through every channel the route exposes.
            attacks = {
                "header:X-Tenant-Id": ({"X-Tenant-Id": TENANT_B}, {}),
                "header:split(verified A, X-Tenant-Id B)": (
                    {"X-LumenAI-Tenant-Id": TENANT_A, "X-Tenant-Id": TENANT_B}, {}),
                "header:X-LumenAI-Tenant-Id": ({"X-LumenAI-Tenant-Id": TENANT_B}, {}),
                "header:split(X-Tenant-Id A, X-LumenAI B)": (
                    {"X-Tenant-Id": TENANT_A, "X-LumenAI-Tenant-Id": TENANT_B}, {}),
            }
            own = {"X-Tenant-Id": TENANT_A}
            if plan.tenant_query:
                attacks["query"] = (own, {"query_tenant": TENANT_B})
            if plan.tenant_path:
                attacks["path"] = (own, {"path_tenant": TENANT_B})
            if plan.tenant_body:
                attacks["body"] = (own, {"body_tenant": TENANT_B})
            for name, (extra, kwargs) in attacks.items():
                results[f"A->B {name}"] = call(plan, hdr(user_a, **extra), watch=TENANT_B, **kwargs)

            # 3b. The same member sending NO tenant header: is the request scoped to the
            #     verified tenant, or pooled into a shared default tenant?
            results["A no-header"] = call(plan, hdr(user_a), watch="default-tenant")

            # 3c. An authenticated user with the same role but NO tenant membership.
            nomember = users["none"][profile]
            results["nomember->B header"] = call(plan, hdr(nomember, **{"X-Tenant-Id": TENANT_B}), watch=TENANT_B)
            results["nomember->B lumenai header"] = call(
                plan, hdr(nomember, **{"X-LumenAI-Tenant-Id": TENANT_B}), watch=TENANT_B)
            results["nomember no-header"] = call(plan, hdr(nomember), watch="default-tenant")

            # 4. A user who belongs to A and B: legitimate as B, and naming a third tenant.
            results["multi legit as B"] = call(plan, hdr(users["both"], **{"X-Tenant-Id": TENANT_B}), watch=TENANT_D)
            results["multi->D header"] = call(plan, hdr(users["both"], **{"X-Tenant-Id": TENANT_D}), watch=TENANT_D)
            if plan.tenant_query or plan.tenant_path or plan.tenant_body:
                results["multi->D claims"] = call(
                    plan, hdr(users["both"], **{"X-Tenant-Id": TENANT_A}), watch=TENANT_D,
                    path_tenant=TENANT_D, query_tenant=TENANT_D, body_tenant=TENANT_D)

            for result in results.values():
                result.pop("_capture", None)
            record["results"] = results
            records.append(record)

    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump({"run_id": uuid.uuid4().hex, "tenants": [TENANT_A, TENANT_B, TENANT_D],
                   "profiles": ["/".join(p) for p in PROFILES], "shard": [shard_index, shard_count],
                   "mounted": position + 1, "routes": records}, handle)
    assert position + 1 == sum(len(r.methods - {"HEAD", "OPTIONS"}) for r in routes)
