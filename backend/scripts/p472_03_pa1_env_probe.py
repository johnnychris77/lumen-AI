#!/usr/bin/env python3
"""P472-03 Batch 8 — PA-1 probe: how each privileged-access gate reads the environment.

LOCAL ONLY. Each configuration runs in a fresh subprocess with a throw-away SQLite
database, so module-level environment reads are evaluated exactly as at process
start. No network, no production systems, no secrets: the probe token values are
fixed local strings. Prints one JSON document.

  cd backend && python scripts/p472_03_pa1_env_probe.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROBE_TOKEN = "pa1-probe-local-token"  # stands in for a configured DEV_AUTH_TOKEN

CHILD = r'''
import json, os, sys
out = {}
try:
    import app.main as m  # module-level production guards may sys.exit here
    out["startup"] = "started"
except SystemExit as exc:
    print(json.dumps({"startup": "refused", "reason": str(exc)[:160]})); sys.exit(0)
from app import deps, enterprise_auth
from app.config import get_settings
from fastapi.testclient import TestClient
s = get_settings()
out["config.is_production(APP_ENV only)"] = s.is_production
out["config.validate issues (logged, not fatal)"] = s.validate()
out["main._ANY_PRODUCTION(APP_ENV or ENVIRONMENT)"] = m._ANY_PRODUCTION
out["deps._DEV_AUTH_ACTIVE(ENABLE_DEV_AUTH and APP_ENV)"] = deps._DEV_AUTH_ACTIVE
out["enterprise_auth AUTH_MODE"] = enterprise_auth.get_auth_mode()
out["enterprise_auth JWT-shape check (ENVIRONMENT=='production' only)"] = enterprise_auth._AUTH_ENV == "production"
c = TestClient(m.app, raise_server_exceptions=False)
tok = os.environ.get("DEV_AUTH_TOKEN", "")
out["deps accepts DEV_AUTH_TOKEN as admin"] = deps._DEV_ROLE_MAP.get(tok) == "admin"
out["GET /api/demo/reset with literal 'Bearer dev-token'"] = c.get("/api/demo/reset", headers={"Authorization": "Bearer dev-token"}).status_code
print(json.dumps(out, default=str))
'''

BASE = {"SECRET_KEY": "pa1-probe-strong-secret-value-0123456789abcdef", "DEV_AUTH_TOKEN": PROBE_TOKEN}
CONFIGS = {
    "1 render.yaml (APP_ENV=ENVIRONMENT=production, AUTH_MODE=oidc, ENABLE_DEV_AUTH=false)":
        {"APP_ENV": "production", "ENVIRONMENT": "production", "AUTH_MODE": "oidc", "ENABLE_DEV_AUTH": "false"},
    "2 APP_ENV=production only, AUTH_MODE=oidc": {"APP_ENV": "production", "AUTH_MODE": "oidc"},
    "3 ENVIRONMENT=production only, AUTH_MODE=oidc, ENABLE_DEV_AUTH=true":
        {"ENVIRONMENT": "production", "AUTH_MODE": "oidc", "ENABLE_DEV_AUTH": "true"},
    "4 APP_ENV=prod (alias), AUTH_MODE unset": {"APP_ENV": "prod"},
    "5 APP_ENV=production, AUTH_MODE=dev, ALLOW_DEV_AUTH_IN_PROD=true":
        {"APP_ENV": "production", "AUTH_MODE": "dev", "ALLOW_DEV_AUTH_IN_PROD": "true"},
    "6 APP_ENV=production, AUTH_MODE=oidc, DEMO_MODE=1":
        {"APP_ENV": "production", "ENVIRONMENT": "production", "AUTH_MODE": "oidc", "DEMO_MODE": "1"},
    "7 APP_ENV=Production (capitalised), ENVIRONMENT=Production, AUTH_MODE=oidc":
        {"APP_ENV": "Production", "ENVIRONMENT": "Production", "AUTH_MODE": "oidc"},
    "8 development defaults (APP_ENV unset, ENABLE_DEV_AUTH=true)": {"ENABLE_DEV_AUTH": "true"},
}
STRIP = ("APP_ENV", "ENVIRONMENT", "AUTH_MODE", "ENABLE_DEV_AUTH", "ALLOW_DEV_AUTH_IN_PROD", "DEMO_MODE",
         "DATABASE_URL", "DEV_AUTH_TOKEN")


def main():
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, env) in enumerate(CONFIGS.items()):
            child_env = {k: v for k, v in os.environ.items() if k not in STRIP}
            child_env.update(BASE)
            child_env.update(env)
            child_env["DATABASE_URL"] = f"sqlite:///{tmp}/pa1-{i}.db"
            proc = subprocess.run([sys.executable, "-c", CHILD], cwd=BACKEND, env=child_env,
                                  capture_output=True, text=True, timeout=300)
            line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
            try:
                results[name] = json.loads(line)
            except ValueError:
                results[name] = {"error": (proc.stderr or proc.stdout)[-400:]}
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
