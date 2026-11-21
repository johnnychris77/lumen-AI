"""P472-03 Batch 8 — PA-1 environment gates (tripwires RB-T38…RB-T40).

PA-1 REMEDIATION (author conversion; pending non-author disposition): the three
tripwires below were committed failing in ``6b2a8d6`` and are converted after the
canonical production determination (``app.core.environment``) landed. Their
assertion lines are unchanged. The shared ``_probe`` helper was amended — see
``docs/enterprise-readiness/p472-03-pa1-remediation-assertion-change-log-v1.md``:
the child no longer requires ``app.main`` to *start*. A production configuration
that enables dev auth or DEMO_MODE now refuses to start (fail closed), so the
child records the refusal and evaluates the same three gates at layer level
(``app.deps`` imported directly; the demo router mounted on a minimal app over
the same database). ``_probe_startup`` exposes the refusal for the new startup
tests. The original text of this file is preserved at ``6b2a8d6``.

Original investigation text (Batch 8):

``scripts/p472_03_pa1_env_probe.py`` showed that the privileged-access gates read
different environment variables:

* ``app.deps`` / ``app.auth``: dev tokens active iff ``ENABLE_DEV_AUTH`` and
  ``APP_ENV`` is not production — ``ENVIRONMENT`` is ignored;
* ``app.main`` startup guards: production iff ``APP_ENV`` **or** ``ENVIRONMENT``;
* ``enterprise_auth.require_enterprise_auth`` JWT-shape check: only
  ``ENVIRONMENT == "production"`` (exact, case-sensitive; ``APP_ENV`` ignored);
* ``/api/demo/*``: the public literal ``Bearer dev-token`` whenever
  ``DEMO_MODE=1``, with no production check.

PA-1 (privileged access) is **unsigned**, so this batch changes no gate. These
strict tripwires state the fail-closed expectation and FAIL today; they are
release blockers (RB-T38…RB-T40) until fixed under an approved PA-1 decision and
dispositioned by a non-author. The deployed ``render.yaml`` configuration
(APP_ENV=ENVIRONMENT=production, AUTH_MODE=oidc, ENABLE_DEV_AUTH=false, no
DEMO_MODE) is NOT affected — ``test_control_render_configuration_is_closed``.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
STRIP = ("APP_ENV", "ENVIRONMENT", "AUTH_MODE", "ENABLE_DEV_AUTH", "ALLOW_DEV_AUTH_IN_PROD", "DEMO_MODE",
         "DATABASE_URL", "DEV_AUTH_TOKEN", "PA1_PG_ADMIN_URL")
CHILD = r'''
import json, os
try:
    import app.main as m
    target, startup = m.app, "started"
except SystemExit as exc:  # PA-1: fail-closed startup refusal; probe the same gates at layer level
    from fastapi import FastAPI
    from app.routes.demo import router as demo_router
    target, startup = FastAPI(), "refused: " + str(exc)
    target.include_router(demo_router)
from app import deps, enterprise_auth
from fastapi.testclient import TestClient
c = TestClient(target, raise_server_exceptions=False)
print(json.dumps({
    "dev_token_admin": deps._DEV_ROLE_MAP.get(os.environ["DEV_AUTH_TOKEN"]) == "admin",
    "jwt_shape_check": enterprise_auth._AUTH_ENV == "production",
    "demo_reset_public_token": c.get("/api/demo/reset", headers={"Authorization": "Bearer dev-token"}).status_code,
    "_startup": startup,
}))
'''


def _tripwire(finding: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding}: {summary}")


def _database_url(tmp_path) -> str:
    """A fresh database for one probe: SQLite by default; PostgreSQL when ``PA1_PG_ADMIN_URL`` is set.

    Set-up only (PA-1 remediation): lets the same tripwires be reproduced on a fresh PostgreSQL
    database. It changes no assertion.
    """
    admin_url = os.environ.get("PA1_PG_ADMIN_URL", "").strip()
    if not admin_url:
        return f"sqlite:///{tmp_path}/pa1.db"
    import uuid

    import psycopg2
    from sqlalchemy.engine import make_url

    name = f"pa1_t_{uuid.uuid4().hex[:12]}"
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    conn.cursor().execute(f'CREATE DATABASE "{name}"')
    conn.close()
    _PG_CREATED.append((admin_url, name))
    return make_url(admin_url).set(drivername="postgresql+psycopg2", database=name).render_as_string(
        hide_password=False)


_PG_CREATED: list[tuple[str, str]] = []


@pytest.fixture(autouse=True)
def _drop_pg_databases():
    yield
    while _PG_CREATED:
        admin_url, name = _PG_CREATED.pop()
        import psycopg2

        conn = psycopg2.connect(admin_url)
        conn.autocommit = True
        conn.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        conn.close()


def _probe(tmp_path, **env) -> dict:
    result = _probe_startup(tmp_path, **env)
    result.pop("_startup")
    return result


def _probe_startup(tmp_path, **env) -> dict:
    child_env = {k: v for k, v in os.environ.items() if k not in STRIP}
    child_env.update({"SECRET_KEY": "pa1-test-strong-secret-value-0123456789abcdef",
                      "DEV_AUTH_TOKEN": "pa1-test-local-token", "DATABASE_URL": _database_url(tmp_path)})
    child_env.update(env)
    proc = subprocess.run([sys.executable, "-c", CHILD], cwd=BACKEND, env=child_env, capture_output=True,
                          text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-500:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


# CONVERTED (PA-1 remediation): was @_tripwire("PA1-01 / RB-T38", "ENVIRONMENT=production with APP_ENV unset
# still activates dev tokens as admin"). Assertion unchanged.
def test_dev_tokens_are_inactive_whenever_any_production_signal_is_set(tmp_path):
    result = _probe(tmp_path, ENVIRONMENT="production", AUTH_MODE="oidc", ENABLE_DEV_AUTH="true")
    assert result["dev_token_admin"] is False


# CONVERTED (PA-1 remediation): was @_tripwire("PA1-02 / RB-T39", "DEMO_MODE=1 in production accepts the
# public literal 'Bearer dev-token' on the destructive /api/demo/reset"). Assertion unchanged.
def test_demo_reset_is_not_reachable_with_the_public_token_in_production(tmp_path):
    result = _probe(tmp_path, APP_ENV="production", ENVIRONMENT="production", AUTH_MODE="oidc", DEMO_MODE="1")
    assert result["demo_reset_public_token"] in (401, 403, 404)


# CONVERTED (PA-1 remediation): was @_tripwire("PA1-03 / RB-T40", "the enterprise JWT-shape production check
# ignores APP_ENV and is case-sensitive"). Assertion unchanged; both configurations start (see below).
def test_enterprise_jwt_shape_check_follows_every_production_signal(tmp_path):
    for env in ({"APP_ENV": "production", "AUTH_MODE": "oidc"},
                {"APP_ENV": "Production", "ENVIRONMENT": "Production", "AUTH_MODE": "oidc"}):
        assert _probe(tmp_path, **env)["jwt_shape_check"] is True, env


def test_control_render_configuration_is_closed(tmp_path):
    result = _probe(tmp_path, APP_ENV="production", ENVIRONMENT="production", AUTH_MODE="oidc",
                    ENABLE_DEV_AUTH="false")
    assert result == {"dev_token_admin": False, "jwt_shape_check": True, "demo_reset_public_token": 403}


def test_control_unset_auth_mode_in_production_refuses_to_start(tmp_path):
    child_env = {k: v for k, v in os.environ.items() if k not in STRIP}
    child_env.update({"SECRET_KEY": "pa1-test-strong-secret-value-0123456789abcdef", "APP_ENV": "prod",
                      "DATABASE_URL": _database_url(tmp_path)})
    proc = subprocess.run([sys.executable, "-c", "import app.main"], cwd=BACKEND, env=child_env,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode != 0 and "AUTH_MODE is not set" in (proc.stderr + proc.stdout)


# --- PA-1 remediation: what the converted configurations do now ----------------------------------


def test_rb_t38_configuration_refuses_to_start(tmp_path):
    startup = _probe_startup(tmp_path, ENVIRONMENT="production", AUTH_MODE="oidc",
                             ENABLE_DEV_AUTH="true")["_startup"]
    assert startup.startswith("refused: FATAL") and "ENABLE_DEV_AUTH is enabled" in startup


def test_rb_t39_configuration_refuses_to_start(tmp_path):
    startup = _probe_startup(tmp_path, APP_ENV="production", ENVIRONMENT="production", AUTH_MODE="oidc",
                             DEMO_MODE="1")["_startup"]
    assert startup.startswith("refused: FATAL") and "DEMO_MODE is enabled" in startup


def test_rb_t40_configurations_start(tmp_path):
    for env in ({"APP_ENV": "production", "AUTH_MODE": "oidc"},
                {"APP_ENV": "Production", "ENVIRONMENT": "Production", "AUTH_MODE": "oidc"}):
        assert _probe_startup(tmp_path, **env)["_startup"] == "started", env
