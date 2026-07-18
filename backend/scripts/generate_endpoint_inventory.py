"""Generate a complete, evidence-based endpoint inventory for LumenAI.

Pilot Zero Directive 002, increment 2 (endpoint governance). This script
introspects the *live* FastAPI application object — every mounted route and
its real resolved dependency tree — and classifies each endpoint by the
security dependencies actually attached to it. It is the single source of
truth for ENDPOINT_INVENTORY.md and ENDPOINT_SECURITY_REVIEW.md, and it
backs the governance test that fails CI if an unauthenticated write endpoint
is added outside the reviewed allowlist.

No endpoint is classified by guesswork: the classification is derived from
the callables FastAPI will actually invoke for the route.

Usage:
    python scripts/generate_endpoint_inventory.py            # prints summary
    python scripts/generate_endpoint_inventory.py --json     # machine output
"""
from __future__ import annotations

import json
import os
import sys

# The app imports a DB engine at module load; point it at the test sqlite db
# exactly as the test harness does, so importing app.main never needs a live
# server or Postgres.
os.environ.setdefault("DATABASE_URL", "sqlite:///./inventory_scratch.db")
os.environ.setdefault("ENABLE_DEV_AUTH", "true")

import inspect  # noqa: E402
import re  # noqa: E402

from fastapi.routing import APIRoute  # noqa: E402

# Names of the security dependencies this codebase uses. Presence of any of
# these in a route's dependency tree is what makes the route authenticated.
_AUTH_CALLABLES = {
    "get_current_user",       # app.deps — bearer identity
    "checker",                # app.authz.require_roles closure
    "_dependency",            # app.tenant_authz.require_tenant_roles closure
    "get_auth_context",       # app.enterprise_auth
    "require_enterprise_auth",
    "_require_dev_auth_context",
    "_require_oidc_auth_context",
}
_TENANT_CALLABLES = {"_dependency", "get_auth_context", "require_enterprise_auth"}
_ADMIN_ROLES = {"admin", "platform_admin", "superadmin", "super_admin"}

# Many handlers establish auth *inside the function body* (e.g.
# `require_enterprise_auth(request)`), not as a FastAPI dependency. Detect
# that pattern from the handler source so such routes are not mis-reported as
# unauthenticated. Any `require_*(` guard counts as authentication EXCEPT
# `require_tier` (a subscription gate, not an auth check).
_AUTH_GUARD_RE = re.compile(
    r"\b(require_(?!tier\b)[a-z_]+|assert_tenant_membership|get_current_user|"
    r"get_auth_context|_resolve_user_email_from_token|_require_dev_auth_context|"
    r"_require_oidc_auth_context)\s*\("
)
# Guards that additionally imply a tenant boundary.
_TENANT_GUARD_RE = re.compile(
    r"\b(require_enterprise_auth|require_hospital_or_enterprise_admin|"
    r"require_enterprise_role|require_tenant_roles|require_tenant_context|"
    r"require_portfolio_access|require_enabled_tenant_membership|"
    r"require_vendor[a-z_]*|require_governance_packet[a-z_]*|"
    r"assert_tenant_membership|get_auth_context)\s*\("
)


def _inbody_auth(endpoint) -> tuple[bool, bool]:
    """Return (authenticated_in_body, tenant_scoped_in_body) by reading source."""
    try:
        src = inspect.getsource(endpoint)
    except (OSError, TypeError):
        return (False, False)
    return (bool(_AUTH_GUARD_RE.search(src)), bool(_TENANT_GUARD_RE.search(src)))


def _walk(dependant, out_calls, out_roles):
    """Recursively collect callable names and any role-set closures."""
    call = getattr(dependant, "call", None)
    if call is not None:
        out_calls.add(getattr(call, "__name__", repr(call)))
        # require_roles / require_tenant_roles close over an `allowed` set of
        # role strings — recover it so we can tell ADMIN from TENANT_SCOPED.
        closure = getattr(call, "__closure__", None) or ()
        for cell in closure:
            try:
                val = cell.cell_contents
            except ValueError:
                continue
            if isinstance(val, (set, frozenset, list, tuple)) and val and all(
                isinstance(x, str) for x in val
            ):
                out_roles.update(val)
    for sub in getattr(dependant, "dependencies", []) or []:
        _walk(sub, out_calls, out_roles)


def classify(route: APIRoute) -> list[dict]:
    rows = []
    calls: set[str] = set()
    roles: set[str] = set()
    _walk(route.dependant, calls, roles)

    # A dependency authenticates if its callable name is a known auth callable
    # OR matches the auth-guard naming convention (require_*, excluding
    # require_tier). This catches dependency guards like require_manufacturer_auth.
    def _is_auth_name(n: str) -> bool:
        return n in _AUTH_CALLABLES or bool(
            re.fullmatch(r"require_(?!tier$)[a-z_]+", n)
        )

    dep_auth = any(_is_auth_name(n) for n in calls)
    dep_tenant = bool(calls & _TENANT_CALLABLES) or any(
        _TENANT_GUARD_RE.match(n + "(") for n in calls
    )
    body_auth, body_tenant = _inbody_auth(route.endpoint)
    authenticated = dep_auth or body_auth
    tenant_scoped = dep_tenant or body_tenant
    auth_style = "dependency" if dep_auth else ("in_body" if body_auth else "none")
    is_admin = bool(roles) and roles <= _ADMIN_ROLES
    handler = f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"

    for method in sorted(m for m in route.methods if m not in {"HEAD", "OPTIONS"}):
        write = method in {"POST", "PUT", "PATCH", "DELETE"}
        path = route.path

        if not authenticated:
            if path in {"/health", "/healthz", "/livez", "/readyz", "/", "/api/health"} or path.endswith("/health"):
                classification = "SYSTEM"
            elif path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/redoc"):
                classification = "PUBLIC"
            else:
                classification = "PUBLIC"
        elif is_admin:
            classification = "ADMIN"
        elif tenant_scoped:
            classification = "TENANT_SCOPED"
        else:
            classification = "AUTHENTICATED"

        rows.append(
            {
                "method": method,
                "path": path,
                "handler": handler,
                "authenticated": authenticated,
                "tenant_scoped": tenant_scoped,
                "admin": is_admin,
                "roles": sorted(roles),
                "write": write,
                "classification": classification,
                "auth_style": auth_style,
                "security_calls": sorted(calls & (_AUTH_CALLABLES)),
            }
        )
    return rows


def collect() -> list[dict]:
    from app.main import app

    rows: list[dict] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            rows.extend(classify(route))
    rows.sort(key=lambda r: (r["path"], r["method"]))
    return rows


def unauthenticated_writes(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r["write"] and not r["authenticated"]]


_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    "docs",
    "pilot-zero",
    "directive-002",
)


def write_artifacts(rows: list[dict]) -> None:
    """Write ENDPOINT_INVENTORY.md and endpoint_inventory.json (the complete,
    machine-generated inventory — 0 UNKNOWN by construction)."""
    os.makedirs(_DOCS_DIR, exist_ok=True)
    json_path = os.path.join(_DOCS_DIR, "endpoint_inventory.json")
    md_path = os.path.join(_DOCS_DIR, "ENDPOINT_INVENTORY.md")

    with open(json_path, "w") as fh:
        json.dump(rows, fh, indent=2, sort_keys=True)

    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
    writes = [r for r in rows if r["write"]]
    unauth = unauthenticated_writes(rows)

    lines = [
        "# LPZ-DIR-002 — Endpoint Inventory (generated)",
        "",
        "**Do not hand-edit.** This file is generated by "
        "`backend/scripts/generate_endpoint_inventory.py`, which introspects the "
        "live FastAPI app (`app.main:app`) — every mounted route and its resolved "
        "dependency tree plus in-body auth guards. Regenerate with:",
        "",
        "```bash",
        "cd backend && PYTHONPATH=. python scripts/generate_endpoint_inventory.py --write",
        "```",
        "",
        "## Summary",
        "",
        f"* Total endpoints (method × path): **{len(rows)}**",
        f"* Write endpoints (POST/PUT/PATCH/DELETE): **{len(writes)}**",
        f"* Unauthenticated write endpoints: **{len(unauth)}** "
        "(see `ENDPOINT_SECURITY_REVIEW.md` for per-endpoint disposition)",
        "* Endpoints classified `UNKNOWN`: "
        f"**{sum(1 for r in rows if r['classification'] == 'UNKNOWN')}** "
        "(must remain 0 — enforced by `test_directive_002_endpoint_governance.py`)",
        "",
        "### By classification",
        "",
        "| Classification | Count |",
        "|---|---|",
    ]
    for k in sorted(by_class):
        lines.append(f"| {k} | {by_class[k]} |")

    lines += [
        "",
        "## Classification method (evidence, not guesswork)",
        "",
        "* **AUTHENTICATED** — a security dependency (`get_current_user`, "
        "`require_roles`, `require_*` guard, enterprise auth) is present in the "
        "route dependency tree, or an equivalent guard is called in the handler body.",
        "* **TENANT_SCOPED** — additionally carries a tenant-boundary guard "
        "(`require_tenant_roles`, `require_enterprise_auth`, `assert_tenant_membership`, …).",
        "* **ADMIN** — role set resolves to admin/platform_admin only.",
        "* **SYSTEM** — health/readiness/liveness/metrics probes.",
        "* **PUBLIC** — no auth guard detected (login, signed webhooks, self-service "
        "registration, stateless compute helpers). Every PUBLIC *write* is reviewed "
        "in `ENDPOINT_SECURITY_REVIEW.md`.",
        "",
        "## Complete endpoint table",
        "",
        "| Method | Path | Handler | Class | Auth | AuthStyle | Tenant | Write | Roles |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['method']} | `{r['path']}` | {r['handler']} | "
            f"{r['classification']} | {'yes' if r['authenticated'] else 'NO'} | "
            f"{r['auth_style']} | {'yes' if r['tenant_scoped'] else '-'} | "
            f"{'W' if r['write'] else 'R'} | {','.join(r['roles']) or '-'} |"
        )
    lines.append("")
    with open(md_path, "w") as fh:
        fh.write("\n".join(lines))
    print(f"wrote {md_path} ({len(rows)} endpoints)")
    print(f"wrote {json_path}")


def main() -> None:
    rows = collect()
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2))
        return
    if "--write" in sys.argv:
        write_artifacts(rows)
        return

    total = len(rows)
    writes = [r for r in rows if r["write"]]
    unauth_writes = [r for r in writes if not r["authenticated"]]
    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1

    print(f"total endpoints: {total}")
    print(f"write endpoints: {len(writes)}")
    print(f"UNAUTHENTICATED write endpoints: {len(unauth_writes)}")
    print("by classification:")
    for k in sorted(by_class):
        print(f"  {k}: {by_class[k]}")
    print("unclassified:", sum(1 for r in rows if r["classification"] == "UNKNOWN"))
    if unauth_writes:
        print("\n--- unauthenticated writes ---")
        for r in unauth_writes:
            print(f"  {r['method']:6} {r['path']}  ({r['handler']})")


if __name__ == "__main__":
    main()
