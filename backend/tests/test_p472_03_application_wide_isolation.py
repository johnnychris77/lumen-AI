"""P472-03 — application-wide tenant-isolation sweep, as a regression test.

Runs ``tests/tenant_isolation_sweep_runner.py`` over EVERY mounted route (in
parallel shards, against throw-away databases, with outbound network blocked)
and compares what it observes with the committed findings register,
``tests/p472_03_findings_register.json``.

What the tests in this file mean:

* ``test_no_route_exhibits`` states the REQUIRED behaviour for each root cause —
  no route may show it — and is ``xfail(strict=True)`` for every root cause that
  still has open routes. These are open security findings, not accepted
  behaviour. The suite fails as soon as a root cause is fully remediated without
  its marker being removed.
* ``test_no_route_outside_the_register_shows_a_finding`` fails if a NEW route
  starts using another tenant's id as its scope.
* ``test_registered_findings_still_reproduce`` fails if a registered finding
  stops reproducing, so the register and the matrix cannot quietly go stale.

The sweep's oracle is the SQL a request executes (see the runner's docstring),
so it does not depend on either tenant having data.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.routing import APIRoute

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from scripts.tenant_isolation_matrix import (  # noqa: E402
    FINDINGS,
    REMEDIATED_PREFIXES,
    classify,
    is_remediated,
    route_key,
    run_sweep,
)

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

REGISTER = json.loads((Path(__file__).parent / "p472_03_findings_register.json").read_text(encoding="utf-8"))
DIALECT = engine.dialect.name
# Routes whose result is not the same on every run or database; listed in the
# register with what was seen, and excluded from the exact comparisons below.
UNSTABLE = set(REGISTER.get("unstable", {}))
EXPECTED = {key: set(classes) for key, classes in REGISTER["findings"].items() if key not in UNSTABLE}
OPEN_CLASSES = sorted({name for classes in EXPECTED.values() for name in classes})


@pytest.fixture(scope="module")
def sweep(tmp_path_factory) -> dict:
    postgres_url = engine.url.render_as_string(hide_password=False) if DIALECT == "postgresql" else None
    return run_sweep(tmp_path_factory.mktemp("p47203-sweep"), postgres_url)


@pytest.fixture(scope="module")
def observed(sweep) -> dict[str, set[str]]:
    return {route_key(r): set(classify(r)) for r in sweep["routes"] if classify(r)}


def test_every_mounted_route_was_swept(sweep):
    # Other tests add probe routes to the shared ``app`` object at run time; the
    # sweep runs in fresh subprocesses and sees the application as it is deployed.
    # Only handlers defined in the application package count as mounted.
    mounted = sorted(
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.endpoint.__module__.split(".")[0] == "app"
        for method in route.methods - {"HEAD", "OPTIONS"}
    )
    swept = sorted((r["method"], r["path"]) for r in sweep["routes"])
    assert swept == mounted
    exercised = [r for r in sweep["routes"] if "results" in r]
    shadowed = sorted(route_key(r) for r in sweep["routes"] if "shadowed_by" in r)
    assert len(exercised) + len(shadowed) == len(mounted)
    assert shadowed == sorted(REGISTER["shadowed"])


def test_no_unauthenticated_or_invalid_token_caller_reaches_tenant_data(observed):
    """Anonymous, malformed-token and expired-token requests, naming tenant B in
    every channel, never cause tenant-scoped SQL. This one passes."""
    exposed = sorted(key for key, classes in observed.items() if "AW-UNAUTH" in classes)
    assert exposed == []


def test_remediated_route_groups_show_no_finding(sweep, observed):
    """The CV routes (c13c5eb), the regulatory, predictions, benchmarks and
    vendor-intelligence routes (6c3072c), the enterprise intake, vendor
    governance and CAPA modules (batch 1), the audit-log, tenant-analytics,
    ML image, operations and capture modules (batch 2), and the thirteen
    modules that re-read the tenant header (batch 4, AW-03/AW-06M) stay clean
    under every variant."""
    covered = 0
    for record in sweep["routes"]:
        if is_remediated(record):
            covered += 1
            assert route_key(record) not in observed, (route_key(record), observed.get(route_key(record)))
    assert covered == 13 + 39 + 77 + 8 + 9 + 5 + 5 + 8 + 21 + 4 + 142


def test_no_route_outside_the_register_shows_a_finding(observed):
    unregistered = {
        key: sorted(classes - EXPECTED.get(key, set()))
        for key, classes in observed.items()
        if key not in UNSTABLE and classes - EXPECTED.get(key, set())
    }
    assert unregistered == {}, (
        "New cross-tenant behaviour not in tests/p472_03_findings_register.json. Fix the route; "
        f"do not add it to the register without review: {dict(list(unregistered.items())[:15])}")


def test_registered_findings_still_reproduce(observed):
    gone = {
        key: sorted(classes - observed.get(key, set()))
        for key, classes in EXPECTED.items()
        if classes - observed.get(key, set())
    }
    assert gone == {}, (
        "Registered findings no longer reproduce. If they were fixed, remove them from the register "
        f"and regenerate the authorization matrix: {dict(list(gone.items())[:15])}")


@pytest.mark.parametrize(
    "finding",
    [
        pytest.param(name, marks=pytest.mark.xfail(strict=True, reason=(
            f"OPEN FINDING {name}: {FINDINGS[name]['title']} — "
            f"{sum(1 for classes in EXPECTED.values() if name in classes)} routes in the register")))
        if name in OPEN_CLASSES else name
        for name in sorted(FINDINGS)
    ],
)
def test_no_route_exhibits(observed, finding):
    """REQUIRED: no mounted route shows this root cause."""
    affected = sorted(key for key, classes in observed.items() if finding in classes)
    assert affected == [], f"{finding} ({FINDINGS[finding]['title']}): {len(affected)} routes, e.g. {affected[:5]}"


def test_the_register_is_internally_consistent():
    assert set(REGISTER["classes"]) == set(FINDINGS)
    for key, classes in REGISTER["findings"].items():
        assert classes and set(classes) <= set(FINDINGS), key
    assert not any(
        key.split(" ", 1)[1] == prefix or key.split(" ", 1)[1].startswith(prefix + "/")
        for key in REGISTER["findings"] for prefix in REMEDIATED_PREFIXES)


# ── GD-3 oracle: the unscoped-table detector must read the WHERE clause the way
#    SQLAlchemy renders it (on its own line), or it mis-reports a scoped statement.
from tenant_isolation_sweep_runner import _unscoped_tenant_tables  # noqa: E402

_TENANT_TABLES = {"accreditation_programs"}


def test_unscoped_detector_reads_where_regardless_of_whitespace():
    """A statement whose tenant_id WHERE clause is rendered on its own line
    (``...\\nWHERE ...tenant_id...``), as SQLAlchemy does, is tenant-scoped and
    must NOT be reported as unscoped. A plain ``" WHERE "`` match missed it and
    produced a false positive; the fix must not re-introduce one."""
    newline_scoped = [(
        "SELECT accreditation_programs.id \nFROM accreditation_programs \n"
        "WHERE accreditation_programs.tenant_id = ?", ("t-a",))]
    space_scoped = [(
        "SELECT accreditation_programs.id FROM accreditation_programs "
        "WHERE accreditation_programs.tenant_id = ?", ("t-a",))]
    assert _unscoped_tenant_tables(newline_scoped, _TENANT_TABLES) == []
    assert _unscoped_tenant_tables(space_scoped, _TENANT_TABLES) == []


def test_unscoped_detector_still_flags_genuinely_unscoped_statements():
    """The fix must not weaken detection: a statement with no WHERE, or a WHERE
    that does not mention tenant_id, is still reported for manual review."""
    no_where = [("SELECT accreditation_programs.id FROM accreditation_programs", ())]
    where_without_tenant = [(
        "SELECT accreditation_programs.id FROM accreditation_programs "
        "WHERE accreditation_programs.id = ?", (1,))]
    newline_without_tenant = [(
        "SELECT accreditation_programs.id \nFROM accreditation_programs \n"
        "WHERE accreditation_programs.id = ?", (1,))]
    assert _unscoped_tenant_tables(no_where, _TENANT_TABLES) == ["accreditation_programs"]
    assert _unscoped_tenant_tables(where_without_tenant, _TENANT_TABLES) == ["accreditation_programs"]
    assert _unscoped_tenant_tables(newline_without_tenant, _TENANT_TABLES) == ["accreditation_programs"]
