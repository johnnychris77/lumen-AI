"""P472-03 Batch 8 — PA-1 environment gates (investigation tripwires; no application change).

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
         "DATABASE_URL", "DEV_AUTH_TOKEN")
CHILD = r'''
import json, os
import app.main as m
from app import deps, enterprise_auth
from fastapi.testclient import TestClient
c = TestClient(m.app, raise_server_exceptions=False)
print(json.dumps({
    "dev_token_admin": deps._DEV_ROLE_MAP.get(os.environ["DEV_AUTH_TOKEN"]) == "admin",
    "jwt_shape_check": enterprise_auth._AUTH_ENV == "production",
    "demo_reset_public_token": c.get("/api/demo/reset", headers={"Authorization": "Bearer dev-token"}).status_code,
}))
'''


def _tripwire(finding: str, summary: str):
    return pytest.mark.xfail(strict=True, reason=f"OPEN FINDING {finding}: {summary}")


def _probe(tmp_path, **env) -> dict:
    child_env = {k: v for k, v in os.environ.items() if k not in STRIP}
    child_env.update({"SECRET_KEY": "pa1-test-strong-secret-value-0123456789abcdef",
                      "DEV_AUTH_TOKEN": "pa1-test-local-token", "DATABASE_URL": f"sqlite:///{tmp_path}/pa1.db"})
    child_env.update(env)
    proc = subprocess.run([sys.executable, "-c", CHILD], cwd=BACKEND, env=child_env, capture_output=True,
                          text=True, timeout=300)
    assert proc.returncode == 0, proc.stderr[-500:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


@_tripwire("PA1-01 / RB-T38", "ENVIRONMENT=production with APP_ENV unset still activates dev tokens as admin")
def test_dev_tokens_are_inactive_whenever_any_production_signal_is_set(tmp_path):
    result = _probe(tmp_path, ENVIRONMENT="production", AUTH_MODE="oidc", ENABLE_DEV_AUTH="true")
    assert result["dev_token_admin"] is False


@_tripwire("PA1-02 / RB-T39", "DEMO_MODE=1 in production accepts the public literal 'Bearer dev-token' on "
                              "the destructive /api/demo/reset")
def test_demo_reset_is_not_reachable_with_the_public_token_in_production(tmp_path):
    result = _probe(tmp_path, APP_ENV="production", ENVIRONMENT="production", AUTH_MODE="oidc", DEMO_MODE="1")
    assert result["demo_reset_public_token"] in (401, 403, 404)


@_tripwire("PA1-03 / RB-T40", "the enterprise JWT-shape production check ignores APP_ENV and is case-sensitive")
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
                      "DATABASE_URL": f"sqlite:///{tmp_path}/pa1.db"})
    proc = subprocess.run([sys.executable, "-c", "import app.main"], cwd=BACKEND, env=child_env,
                          capture_output=True, text=True, timeout=300)
    assert proc.returncode != 0 and "AUTH_MODE is not set" in (proc.stderr + proc.stdout)
