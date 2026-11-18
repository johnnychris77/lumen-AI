"""P472-03 application-wide tenant isolation: sweep orchestration, classification
and the authorization matrix.

The sweep itself lives in ``tests/tenant_isolation_sweep_runner.py`` (it needs
the test environment). This module:

* runs it in parallel shards against throw-away databases (``run_sweep``);
* turns each route's raw result into finding classes (``classify``);
* renders the endpoint-by-endpoint matrix and the findings register.

Usage, from ``backend/``::

    python scripts/tenant_isolation_matrix.py --sweep sqlite --out /tmp/sweep.json
    python scripts/tenant_isolation_matrix.py --from /tmp/sweep.json \
        --write-register tests/p472_03_findings_register.json \
        --write-matrix ../docs/enterprise-readiness/p472-03-application-wide-authorization-matrix.md

Nothing here imports the application; the sweep runs in subprocesses.
"""
from __future__ import annotations

import argparse
import csv
import concurrent.futures
import json
import os
import subprocess
import sys
import uuid
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
RUNNER = BACKEND / "tests" / "tenant_isolation_sweep_runner.py"
SHARDS = 4                      # fixed, so every run partitions the routes the same way
REFUSED = {401, 403}

# ── finding classes ───────────────────────────────────────────────────────────

FINDINGS: dict[str, dict[str, str]] = {
    "AW-01": {
        "title": "Tenant header trusted with no membership check",
        "who": "any authenticated user holding the route's role",
        "cause": "The handler scopes data by the X-Tenant-Id header (``resolve_tenant`` or "
                 "``get_request_tenant_id``) and the route's only guard is a global role.",
        "risk": "High",
    },
    "AW-02": {
        "title": "Membership checked on one tenant header, data scoped by another",
        "who": "any verified member of any tenant",
        "cause": "``require_tenant_roles`` verifies membership for X-LumenAI-Tenant-Id (preferred) "
                 "while ``resolve_tenant`` scopes data by X-Tenant-Id. Sending both splits them.",
        "risk": "High",
    },
    "AW-03": {
        "title": "Handler re-reads the tenant from a header the auth layer did not verify",
        "who": "any verified member of any tenant",
        "cause": "After ``require_enterprise_auth`` the handler calls ``get_request_tenant_id(request)``, "
                 "which prefers X-LumenAI-Tenant-Id. The auth layer only verifies an explicit X-Tenant-Id.",
        "risk": "High",
    },
    "AW-04": {
        "title": "Tenant taken from a query, path or body parameter",
        "who": "any authenticated user allowed on the route",
        "cause": "The handler uses a client-supplied ``tenant_id`` as its data scope without comparing "
                 "it with the caller's verified tenant.",
        "risk": "High",
    },
    "AW-05": {
        "title": "Header trusted when the user has no single verified tenant",
        "who": "an authenticated user with no tenant membership, or with several",
        "cause": "``current_user.tenant_id or get_request_tenant_id(request)``: the verified tenant is "
                 "empty for a user with zero or several memberships, and the code falls back to the header.",
        "risk": "High",
    },
    "AW-06M": {
        "title": "Verified members without a tenant header are pooled in ``default-tenant``",
        "who": "every client that sends no tenant header, with no attack",
        "cause": "The handler reads the tenant from the raw header, which defaults to ``default-tenant``, "
                 "instead of the verified context.",
        "risk": "High",
    },
    "AW-06N": {
        "title": "Users with no membership are pooled in ``default-tenant``",
        "who": "authenticated users with no tenant membership",
        "cause": "``current_user.tenant_id or ... or 'default-tenant'``: no verified tenant degrades to "
                 "a shared literal instead of a refusal.",
        "risk": "Medium",
    },
    "AW-09": {
        "title": "Unauthenticated request reads or writes tenant tables",
        "who": "anyone, with no credentials",
        "cause": "The handler has no authentication and queries tenant-owned tables, usually with no "
                 "tenant predicate at all, so one response can span every tenant.",
        "risk": "Critical",
    },
    "AW-UNAUTH": {
        "title": "Tenant-scoped SQL executed for an unauthenticated or invalid-token caller",
        "who": "anyone",
        "cause": "No authentication before tenant data access.",
        "risk": "Critical",
    },
}

_AUDIT_TABLE_MARKERS = ("audit", "usage", "meter", "_log")

# Route groups already remediated on this branch (prefix -> commit).
REMEDIATED_PREFIXES = {
    "/api/enterprise/cv": "c13c5eb",
    "/api/regulatory": "6c3072c",
    "/api/predictions": "6c3072c",
    "/api/enterprise/benchmarks": "6c3072c",
    "/api/vendor-intelligence": "6c3072c",
}


def _hit(result: dict | None) -> bool:
    return bool(result and (result.get("read") or result.get("write")))


def classify(record: dict) -> list[str]:
    """Finding classes observed for one route (empty list: none observed)."""
    results = record.get("results")
    if not results:
        return []
    get = lambda name: results.get(name) or {}  # noqa: E731
    out: set[str] = set()
    if any(_hit(get(name)) for name in ("anonymous", "anonymous+claims", "invalid-token", "expired-token")):
        out.add("AW-UNAUTH")
    anonymous = get("anonymous")
    if anonymous.get("public_reads") or anonymous.get("public_writes"):
        out.add("AW-09")
    if _hit(get("A->B header:X-Tenant-Id")):
        out.add("AW-01")
    elif _hit(get("A->B header:split(verified A, X-Tenant-Id B)")):
        out.add("AW-02")
    if _hit(get("A->B header:X-LumenAI-Tenant-Id")) or _hit(get("A->B header:split(X-Tenant-Id A, X-LumenAI B)")):
        out.add("AW-03")
    if any(_hit(get(f"A->B {channel}")) for channel in ("query", "path", "body")) or _hit(get("multi->D claims")):
        out.add("AW-04")
    if "AW-01" not in out and any(
        _hit(get(name)) for name in ("nomember->B header", "nomember->B lumenai header", "multi->D header")
    ):
        out.add("AW-05")
    if _hit(get("A no-header")):
        out.add("AW-06M")
    if _hit(get("nomember no-header")):
        out.add("AW-06N")
    return sorted(out)


def foreign_writes(record: dict) -> list[str]:
    """Non-audit tables written under a tenant the caller does not belong to."""
    tables: set[str] = set()
    for name, result in (record.get("results") or {}).items():
        if name.startswith(("A->B", "nomember->B", "multi->D", "anonymous", "invalid", "expired")):
            tables |= {t for t in result.get("write", []) if not any(m in t for m in _AUDIT_TABLE_MARKERS)}
    return sorted(tables)


def route_key(record: dict) -> str:
    return f"{record['method']} {record['path']}"


def build_register(sweeps: list[dict], baseline_commit: str) -> dict:
    """The findings register from one or more sweeps of the same code.

    A route whose classes differ between the given sweeps (different runs or
    databases) goes under ``unstable`` with what each sweep saw; it is still an
    open finding, but the regression test does not compare it exactly."""
    per_sweep = [{route_key(r): classify(r) for r in sweep["routes"] if classify(r)} for sweep in sweeps]
    keys = sorted(set().union(*per_sweep))
    findings: dict[str, list[str]] = {}
    unstable: dict[str, dict[str, list[str]]] = {}
    for key in keys:
        seen = [observed.get(key, []) for observed in per_sweep]
        findings[key] = sorted(set().union(*seen))
        if any(item != seen[0] for item in seen):
            unstable[key] = {f"{sweep['database']}#{index}": item
                             for index, (sweep, item) in enumerate(zip(sweeps, seen, strict=True))}
    return {
        "description": "P472-03 application-wide tenant-isolation findings observed by the sweep. "
                       "Each entry is an OPEN finding. tests/test_p472_03_application_wide_isolation.py "
                       "fails if a route appears that is not listed here, and if a listed route stops "
                       "reproducing without being removed.",
        "baseline_commit": baseline_commit,
        "sweeps": [sweep["database"] for sweep in sweeps],
        "classes": {key: value["title"] for key, value in FINDINGS.items()},
        "shadowed": sorted(route_key(r) for r in sweeps[0]["routes"] if "shadowed_by" in r),
        "unstable": unstable,
        "findings": findings,
    }


def update_document(path: Path, table: str) -> None:
    """Replace the generated per-endpoint table between the markers in ``path``."""
    begin, end = "<!-- BEGIN GENERATED MATRIX -->", "<!-- END GENERATED MATRIX -->"
    text = path.read_text(encoding="utf-8")
    head, rest = text.split(begin, 1)
    _old, tail = rest.split(end, 1)
    path.write_text(f"{head}{begin}\n{table}\n{end}{tail}", encoding="utf-8")


# ── running the sweep ─────────────────────────────────────────────────────────

def _run_shard(index: int, database_url: str, workdir: Path, *, prepare_only: bool = False) -> dict:
    shard_dir = workdir / f"shard-{index}"
    shard_dir.mkdir(parents=True, exist_ok=True)
    out = shard_dir / "sweep.json"
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "P472_SWEEP_OUT": str(out),
        "P472_SWEEP_SHARD": f"{index}/{SHARDS}",
        "PYTHONPATH": os.pathsep.join(filter(None, [str(BACKEND), os.environ.get("PYTHONPATH", "")])),
    }
    if prepare_only:
        env["P472_SWEEP_PREPARE_ONLY"] = "1"
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "pytest", str(RUNNER), "-q", "-x", "-p", "no:cacheprovider",
         "--rootdir", str(BACKEND)],
        cwd=shard_dir, env=env, capture_output=True, text=True, timeout=3000, check=False)
    if completed.returncode != 0 or (not prepare_only and not out.exists()):
        raise RuntimeError(f"sweep shard {index} failed:\n{completed.stdout[-3000:]}\n{completed.stderr[-2000:]}")
    return {} if prepare_only else json.loads(out.read_text(encoding="utf-8"))


def run_sweep(workdir: Path, postgres_url: str | None = None) -> dict:
    """Sweep every mounted route in ``SHARDS`` parallel shards.

    With no ``postgres_url`` each shard gets its own SQLite file under
    ``workdir``; with one, each shard gets its own scratch schema, dropped afterwards."""
    workdir.mkdir(parents=True, exist_ok=True)
    schemas: list[str] = []
    engine = None
    if postgres_url:
        import sqlalchemy as sa

        engine = sa.create_engine(postgres_url)
        run = uuid.uuid4().hex[:10]
        urls = []
        for index in range(SHARDS):
            schema = f"p47203_sweep_{run}_{index}"
            with engine.begin() as conn:
                conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
            schemas.append(schema)
            joiner = "&" if "?" in postgres_url else "?"
            urls.append(f"{postgres_url}{joiner}options=-csearch_path={schema}")
    else:
        urls = [f"sqlite:///{workdir / f'shard-{index}.db'}" for index in range(SHARDS)]
    try:
        if postgres_url:
            # Creating (and dropping) several hundred tables takes one lock per object.
            # Doing that for every shard at once exhausts PostgreSQL's shared lock
            # table, so the schemas are built one at a time before the parallel sweep.
            for index, url in enumerate(urls):
                _run_shard(index, url, workdir, prepare_only=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=SHARDS) as pool:
            parts = list(pool.map(lambda pair: _run_shard(pair[0], pair[1], workdir), enumerate(urls)))
    finally:
        if engine is not None:
            import sqlalchemy as sa

            for schema in schemas:
                with engine.begin() as conn:          # one transaction per schema, for the same reason
                    conn.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            engine.dispose()
    routes = sorted((r for part in parts for r in part["routes"]), key=lambda r: r["index"])
    mounted = {part["mounted"] for part in parts}
    assert len(mounted) == 1 and len(routes) == mounted.pop(), "shards disagree on the mounted route count"
    return {"profiles": parts[0]["profiles"], "tenants": parts[0]["tenants"],
            "database": "postgresql" if postgres_url else "sqlite", "routes": routes}


# ── the matrix ────────────────────────────────────────────────────────────────

def _auth(record: dict) -> str:
    results, deps, guards = record["results"], set(record["deps"]), set(record["guards"])
    anonymous = results["anonymous"]["status"]
    if 200 <= anonymous < 300:
        return "none (public)"
    parts = []
    if "_dependency" in deps:
        parts.append("bearer + tenant role")
    if "checker" in deps:
        parts.append("bearer + global role")
    if "require_gateway_auth" in deps:
        parts.append("gateway key or bearer")
    if "require_manufacturer_auth" in deps:
        parts.append("bearer + X-Manufacturer-ID")
    for name in ("require_portfolio_access", "require_inspection_runner", "require_developer_auth", "_check"):
        if name in deps:
            parts.append(name)
    if not parts and "get_current_user" in deps:
        parts.append("bearer")
    in_body = sorted(guards - {"require_roles", "require_tenant_roles", "get_current_user"})
    if in_body and not parts:
        parts.append("in handler: " + ", ".join(in_body[:2]))
    if not parts:
        parts.append(f"undetermined (anonymous {anonymous})")
    return "; ".join(parts)


def _tenant_source(record: dict) -> str:
    deps, static, inputs = set(record["deps"]), record["static"], record["tenant_inputs"]
    parts = []
    if static["handler_uses_authorized_tenant"]:
        parts.append("verified context")
    if "resolve_tenant" in deps:
        parts.append("X-Tenant-Id (resolve_tenant)")
    for channel in ("path", "query", "body"):
        if inputs[channel]:
            parts.append(f"{channel}: {', '.join(inputs[channel])}")
    if static["handler_reads_raw_tenant_header"]:
        parts.append("raw header in handler")
    elif static["module_header_fallback"] and "get_current_user" in deps:
        parts.append("principal, else header/default")
    if "_dependency" in deps and "resolve_tenant" not in deps:
        parts.append("tenant-role dependency")
    if not parts and "require_enterprise_auth" in record["guards"]:
        parts.append("enterprise auth context")
    return "; ".join(parts) or "none identified"


def _tables(names: list[str], limit: int | None = 3) -> str:
    if not names:
        return "—"
    if limit is None or len(names) <= limit:
        return ", ".join(names)
    return ", ".join(names[:limit]) + f" +{len(names) - limit}"


def _remediated(path: str) -> str | None:
    for prefix, commit in REMEDIATED_PREFIXES.items():
        if path == prefix or path.startswith(prefix + "/"):
            return commit
    return None


BATCH = {"AW-UNAUTH": 0, "AW-09": 0, "AW-01": 1, "AW-02": 1, "AW-03": 2, "AW-06M": 2, "AW-04": 3, "AW-05": 4, "AW-06N": 4}
IMPACT = {
    "AW-01": "foreign X-Tenant-Id: 200 -> 403",
    "AW-02": "mismatched tenant headers: 200 -> 403",
    "AW-03": "foreign X-LumenAI-Tenant-Id: 200 -> 403",
    "AW-04": "foreign tenant parameter: 200 -> 403",
    "AW-05": "no/multiple membership + header: 200 -> 403",
    "AW-06M": "no header: default-tenant -> caller's tenant",
    "AW-06N": "no membership: default-tenant -> 403",
    "AW-UNAUTH": "unauthenticated: 200 -> 401",
    "AW-09": "unauthenticated: 200 -> 401 (unless confirmed public by design)",
}


def matrix_row(record: dict, limit: int | None = 3) -> list[str]:
    """One matrix row. ``limit`` caps how many table names a cell lists (None: all)."""
    if "shadowed_by" in record:
        return [record["method"], f"`{record['path']}`", record["module"].removeprefix("app."), "—", "—", "—", "—",
                "—", "—", f"unreachable: shadowed by `{record['shadowed_by'].removeprefix('app.')}`", "—", "Info",
                "Review", "Not reviewed"]
    classes = classify(record)
    baseline = record["baseline"]
    refused = baseline["status"] in REFUSED
    fixed = _remediated(record["path"])
    if refused:
        membership, objects = "n/a (refused)", "n/a (refused)"
    else:
        membership = "membership table queried" if baseline["membership_checked"] else "not queried"
        if baseline["unscoped_tenant_tables"]:
            objects = "SQL without tenant predicate: " + _tables(baseline["unscoped_tenant_tables"], limit)
        elif baseline["own_tenant_bound"]:
            objects = "tenant-bound SQL"
        else:
            objects = "no tenant-bound SQL"
    if classes:
        writes = foreign_writes(record)
        result = ", ".join(classes) + (f" (foreign write: {_tables(writes, limit)})" if writes else "")
        if "AW-09" in classes:
            anonymous = record["results"]["anonymous"]
            reached = anonymous.get("public_reads", []) + anonymous.get("public_writes", [])
            result += f" (anonymous reach: {_tables(reached, limit)})"
        rank = {"Critical": 4, "High": 3, "Medium": 2}
        risk = max((FINDINGS[c]["risk"] for c in classes), key=lambda r: rank.get(r, 0))
        impact = "; ".join(IMPACT[c] for c in classes)
        status = f"Open — batch {min(BATCH[c] for c in classes)}"
    elif refused:
        result, risk, impact = "not reachable with tenant roles", "Not assessed", "—"
        status = "Review (platform-admin or special credential)"
    else:
        attacked = [r["status"] for name, r in record["results"].items() if name.startswith("A->B")]
        result = "refused" if attacked and all(s in REFUSED for s in attacked) else "no foreign-tenant SQL observed"
        impact = "—"
        if baseline["unscoped_tenant_tables"]:
            risk, status = "Lead", "Review (unscoped SQL lead)"
        elif baseline["status"] >= 400:
            # The legitimate request itself failed, so the handler's data access
            # was not (fully) executed: absence of a finding is not evidence.
            risk, status = "Incomplete", "Review (not fully exercised)"
        else:
            risk, status = "None observed", "None required by this evidence"
    if fixed and not classes:
        status = f"Remediated ({fixed})"
    if baseline["status"] >= 400 and not refused and not classes:
        result += f" (baseline HTTP {baseline['status']}: partly exercised)"
    return [record["method"], f"`{record['path']}`", record["module"].removeprefix("app."), _auth(record),
            _tenant_source(record), membership, objects, _tables(baseline["reads"], limit),
            _tables(baseline["writes"], limit), result, impact, risk, status, "Not reviewed"]


MATRIX_HEADER = ["Method", "Route", "Module", "Authentication", "Tenant source", "Membership verification",
                 "Object-level authorization", "DB reads", "DB writes", "Cross-tenant adversarial result",
                 "Contract impact", "Risk", "Remediation", "Independent review"]


# The Markdown table abbreviates recurring phrases so that the document stays
# within the size GitHub renders (about 500 KiB); the CSV written by
# ``--write-csv`` carries the same rows unabbreviated, with full table lists.
# Every abbreviation is explained in the document's "How to read the matrix".
_ABBREVIATIONS = [
    ("membership table queried", "queried"),
    ("not queried", "no"),
    ("n/a (refused)", "n/a"),
    ("SQL without tenant predicate: ", "unscoped: "),
    ("no tenant-bound SQL", "—"),
    ("tenant-bound SQL", "tenant-bound"),
    ("no foreign-tenant SQL observed", "none observed"),
    ("not reachable with tenant roles", "role-gated"),
    (": partly exercised)", ")"),
    ("baseline HTTP ", "baseline "),
    ("bearer + global role", "global role"),
    ("bearer + tenant role", "tenant role"),
    ("bearer + X-Manufacturer-ID", "manufacturer header"),
    ("none (public)", "public"),
    ("in handler: ", "handler: "),
    ("principal, else header/default", "principal/header"),
    ("tenant-role dependency", "verified header"),
    ("X-Tenant-Id (resolve_tenant)", "resolve_tenant"),
    ("enterprise auth context", "enterprise context"),
    ("raw header in handler", "raw header"),
    ("none identified", "—"),
    ("None required by this evidence", "—"),
    ("Review (unscoped SQL lead)", "Review: SQL lead"),
    ("Review (not fully exercised)", "Review: incomplete"),
    ("Review (platform-admin or special credential)", "Review: role-gated"),
    ("Open — batch ", "Open B"),
]
_IDENTITY_TABLES = {"tenant_memberships", "user_role_assignments", "users"}
_IMPACT_CODE = {"AW-01": "403", "AW-02": "403", "AW-03": "403", "AW-04": "403", "AW-05": "403", "AW-06N": "403",
                "AW-06M": "own tenant", "AW-09": "401*", "AW-UNAUTH": "401"}


def _compact_row(record: dict) -> list[str]:
    row = matrix_row(record, limit=2)
    for old, new in _ABBREVIATIONS:
        row = [cell.replace(old, new) for cell in row]
    row[1] = row[1].strip("`")
    row[2] = row[2].removeprefix("routes.")
    if "results" in record:
        # The identity tables are read by the auth layer on almost every route;
        # the "Membership verification" column already reports that.
        row[7] = _tables([t for t in record["baseline"]["reads"] if t not in _IDENTITY_TABLES], 2)
    classes = classify(record) if "results" in record else []
    row[10] = "; ".join(dict.fromkeys(_IMPACT_CODE[c] for c in classes)) or "—"
    return row


def render_matrix_table(sweep: dict) -> str:
    lines = ["| " + " | ".join(MATRIX_HEADER) + " |", "|" + "---|" * len(MATRIX_HEADER)]
    for record in sweep["routes"]:
        lines.append("| " + " | ".join(cell.replace("|", "\\|") for cell in _compact_row(record)) + " |")
    return "\n".join(lines)


def write_csv(path: Path, sweep: dict) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(MATRIX_HEADER + ["Handler", "Baseline HTTP status", "Finding classes"])
        for record in sweep["routes"]:
            live = "results" in record
            row = matrix_row(record, limit=None)
            row[1] = row[1].strip("`")
            writer.writerow(row + [
                record.get("handler", ""),
                record["baseline"]["status"] if live else "",
                " ".join(classify(record)) if live else "",
            ])


def summary(sweep: dict) -> dict:
    live = [r for r in sweep["routes"] if "results" in r]
    per_class: Counter = Counter()
    per_module: dict[str, Counter] = {}
    with_any = 0
    for record in live:
        classes = classify(record)
        with_any += bool(classes)
        for name in classes:
            per_class[name] += 1
            per_module.setdefault(name, Counter())[record["module"].removeprefix("app.routes.")] += 1
    return {
        "mounted": len(sweep["routes"]),
        "shadowed": sum(1 for r in sweep["routes"] if "shadowed_by" in r),
        "with_finding": with_any,
        "per_class": dict(sorted(per_class.items())),
        "modules_per_class": {k: len(v) for k, v in sorted(per_module.items())},
        "top_modules": {k: v.most_common(8) for k, v in sorted(per_module.items())},
        "public": sum(1 for r in live if 200 <= r["results"]["anonymous"]["status"] < 300),
        "role_gated": sum(1 for r in live if r["baseline"]["status"] in REFUSED),
        "partly_exercised": sum(1 for r in live if r["baseline"]["status"] >= 400
                                and r["baseline"]["status"] not in REFUSED),
        "unscoped_leads": sum(1 for r in live if r["baseline"]["unscoped_tenant_tables"] and not classify(r)
                              and r["baseline"]["status"] not in REFUSED),
        "foreign_write_routes": sum(1 for r in live if foreign_writes(r)),
        "foreign_write_tables": len({t for r in live for t in foreign_writes(r)}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sweep", choices=["sqlite", "postgres"], help="run the sweep")
    parser.add_argument("--postgres-url", default=os.environ.get("P472_SWEEP_POSTGRES_URL"))
    parser.add_argument("--workdir", default="/tmp/p47203-sweep")
    parser.add_argument("--out", help="write the merged sweep JSON here")
    parser.add_argument("--from", dest="source", help="read a merged sweep JSON instead of running")
    parser.add_argument("--also", nargs="*", default=[], help="more sweep JSONs of the same code, "
                        "used to mark routes whose result varies between runs or databases")
    parser.add_argument("--update-document", help="replace the generated table in this Markdown file")
    parser.add_argument("--baseline-commit", default="6c3072c")
    parser.add_argument("--write-register")
    parser.add_argument("--write-matrix-table", help="write the per-endpoint Markdown table here")
    parser.add_argument("--write-csv", help="write the unabbreviated per-endpoint matrix as CSV here")
    args = parser.parse_args()

    if args.sweep:
        sweep = run_sweep(Path(args.workdir), args.postgres_url if args.sweep == "postgres" else None)
        if args.out:
            Path(args.out).write_text(json.dumps(sweep), encoding="utf-8")
    elif args.source:
        sweep = json.loads(Path(args.source).read_text(encoding="utf-8"))
    else:
        parser.error("give --sweep or --from")
    if args.write_register:
        others = [json.loads(Path(extra).read_text(encoding="utf-8")) for extra in args.also]
        Path(args.write_register).write_text(
            json.dumps(build_register([sweep, *others], args.baseline_commit), indent=1) + "\n", encoding="utf-8")
    if args.update_document:
        update_document(Path(args.update_document), render_matrix_table(sweep))
    if args.write_matrix_table:
        Path(args.write_matrix_table).write_text(render_matrix_table(sweep) + "\n", encoding="utf-8")
    if args.write_csv:
        write_csv(Path(args.write_csv), sweep)
    print(json.dumps(summary(sweep), indent=1))


if __name__ == "__main__":
    main()
