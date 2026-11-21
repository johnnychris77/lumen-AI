#!/usr/bin/env python3
"""P472-03 PA-1 remediation — reproduce RB-T38, RB-T39 and RB-T40 on SQLite or PostgreSQL.

LOCAL ONLY. Every configuration runs in a fresh subprocess against a fresh
database (a throw-away SQLite file, or a newly created PostgreSQL database that
is dropped afterwards). No network beyond the local database, no production
system and no deployed secret: the probe tokens are fixed local strings.

For every configuration the child reports four layers separately, so a startup
refusal can never hide a gate that is still open underneath:

* ``startup``: whether ``import app.main`` starts or refuses (``sys.exit``);
* ``deps``: whether the dev-token map grants the configured ``DEV_AUTH_TOKEN``
  admin (RB-T38), imported **without** ``app.main``;
* ``enterprise``: whether the enterprise JWT-shape production check is on
  (RB-T40), and whether ``require_enterprise_auth`` accepts the configured dev
  token with client-supplied actor / role / tenant headers;
* ``demo``: the demo router mounted on a minimal app over the same database,
  with one seeded ``pilot_status`` row for tenant ``demo``: the status of
  ``GET /api/demo/reset`` with the public literal ``Bearer dev-token`` and
  whether the seeded row survived (RB-T39);
* ``app``: when the full app started, the same reset request through it.

  cd backend && python scripts/p472_03_pa1_remediation_repro.py --db sqlite
  cd backend && python scripts/p472_03_pa1_remediation_repro.py --db postgres \
      --pg-admin-url postgresql://postgres:PASSWORD@localhost:5432/postgres
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROBE_TOKEN = "pa1-repro-local-token"  # stands in for a configured DEV_AUTH_TOKEN

CHILD = r'''
import json, os, sys
out = {}
try:
    import app.main as m  # module-level production guards may sys.exit here
    out["startup"] = "started"
except SystemExit as exc:
    m = None
    out["startup"] = "refused"
    out["startup_reason"] = str(exc)[:240]

from app import deps, enterprise_auth
out["deps.dev_token_admin"] = deps._DEV_ROLE_MAP.get(os.environ["DEV_AUTH_TOKEN"]) == "admin"
out["enterprise.jwt_shape_check"] = enterprise_auth._AUTH_ENV == "production"

from fastapi import FastAPI, HTTPException
from starlette.requests import Request
def _req(headers):
    raw = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "query_string": b""})
try:
    ctx = enterprise_auth.require_enterprise_auth(_req({
        "Authorization": "Bearer " + os.environ["DEV_AUTH_TOKEN"],
        "X-LumenAI-Actor": "attacker@example.invalid", "X-LumenAI-Role": "admin",
        "X-LumenAI-Tenant-Id": "victim-tenant"}))
    out["enterprise.dev_token_with_header_identity"] = {"accepted": True, "role": getattr(ctx, "role", None),
                                                       "tenant_id": getattr(ctx, "tenant_id", None)}
except HTTPException as exc:
    out["enterprise.dev_token_with_header_identity"] = {"accepted": False, "status": exc.status_code}

from app.db.session import SessionLocal, engine
from app.models.pilot import PilotStatus
from datetime import datetime, timedelta, timezone
out["db_dialect"] = engine.dialect.name
PilotStatus.__table__.create(bind=engine, checkfirst=True)
def _seed():
    db = SessionLocal()
    try:
        db.add(PilotStatus(tenant_id="demo", facility_id="pa1-probe",
                           pilot_end_date=datetime.now(timezone.utc) + timedelta(days=30)))
        db.commit()
    finally:
        db.close()
def _count():
    db = SessionLocal()
    try:
        return db.query(PilotStatus).filter(PilotStatus.tenant_id == "demo").count()
    finally:
        db.close()

from fastapi.testclient import TestClient
from app.routes.demo import router as demo_router
mini = FastAPI(); mini.include_router(demo_router)
_seed(); before = _count()
r = TestClient(mini, raise_server_exceptions=False).get("/api/demo/reset", headers={"Authorization": "Bearer dev-token"})
out["demo.reset_public_token"] = {"status": r.status_code, "demo_rows_before": before, "demo_rows_after": _count()}

if m is not None:
    _seed(); before = _count()
    r = TestClient(m.app, raise_server_exceptions=False).get("/api/demo/reset",
                                                             headers={"Authorization": "Bearer dev-token"})
    out["app.reset_public_token"] = {"status": r.status_code, "demo_rows_before": before, "demo_rows_after": _count()}
print(json.dumps(out, default=str))
'''

BASE = {"SECRET_KEY": "pa1-repro-strong-secret-value-0123456789abcdef", "DEV_AUTH_TOKEN": PROBE_TOKEN}
# id -> (tripwire / control, environment)
CONFIGS = {
    "RB-T38 ENVIRONMENT=production only, AUTH_MODE=oidc, ENABLE_DEV_AUTH=true":
        {"ENVIRONMENT": "production", "AUTH_MODE": "oidc", "ENABLE_DEV_AUTH": "true"},
    "RB-T39 APP_ENV=ENVIRONMENT=production, AUTH_MODE=oidc, DEMO_MODE=1":
        {"APP_ENV": "production", "ENVIRONMENT": "production", "AUTH_MODE": "oidc", "DEMO_MODE": "1"},
    "RB-T40a APP_ENV=production only, AUTH_MODE=oidc": {"APP_ENV": "production", "AUTH_MODE": "oidc"},
    "RB-T40b APP_ENV=ENVIRONMENT=Production (capitalised), AUTH_MODE=oidc":
        {"APP_ENV": "Production", "ENVIRONMENT": "Production", "AUTH_MODE": "oidc"},
    "PA-1 APP_ENV=production, AUTH_MODE=dev, ALLOW_DEV_AUTH_IN_PROD=true":
        {"APP_ENV": "production", "AUTH_MODE": "dev", "ALLOW_DEV_AUTH_IN_PROD": "true"},
    "PA-1 conflict APP_ENV=development, ENVIRONMENT=production, AUTH_MODE=oidc":
        {"APP_ENV": "development", "ENVIRONMENT": "production", "AUTH_MODE": "oidc"},
    "control render.yaml (APP_ENV=ENVIRONMENT=production, AUTH_MODE=oidc, ENABLE_DEV_AUTH=false)":
        {"APP_ENV": "production", "ENVIRONMENT": "production", "AUTH_MODE": "oidc", "ENABLE_DEV_AUTH": "false"},
    "control development, ENABLE_DEV_AUTH=true (authorised dev workflow)": {"ENABLE_DEV_AUTH": "true"},
    "control development, DEMO_MODE=1 (authorised demo workflow)": {"DEMO_MODE": "1"},
}
STRIP = ("APP_ENV", "ENVIRONMENT", "AUTH_MODE", "ENABLE_DEV_AUTH", "ALLOW_DEV_AUTH_IN_PROD", "DEMO_MODE",
         "DATABASE_URL", "DEV_AUTH_TOKEN", "ENV")


def _pg_fresh(admin_url: str):
    import psycopg2
    from sqlalchemy.engine import make_url

    name = f"pa1_repro_{uuid.uuid4().hex[:10]}"
    conn = psycopg2.connect(admin_url)
    conn.autocommit = True
    conn.cursor().execute(f'CREATE DATABASE "{name}"')
    conn.close()
    url = make_url(admin_url).set(drivername="postgresql+psycopg2", database=name)

    def drop():
        c = psycopg2.connect(admin_url)
        c.autocommit = True
        c.cursor().execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        c.close()

    return url.render_as_string(hide_password=False), drop


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", choices=("sqlite", "postgres"), default="sqlite")
    ap.add_argument("--pg-admin-url", default=os.environ.get("PA1_PG_ADMIN_URL", ""))
    args = ap.parse_args()
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for i, (name, env) in enumerate(CONFIGS.items()):
            drop = None
            if args.db == "postgres":
                db_url, drop = _pg_fresh(args.pg_admin_url)
            else:
                db_url = f"sqlite:///{tmp}/pa1-{i}.db"
            child_env = {k: v for k, v in os.environ.items() if k not in STRIP}
            child_env.update(BASE)
            child_env.update(env)
            child_env["DATABASE_URL"] = db_url
            try:
                proc = subprocess.run([sys.executable, "-c", CHILD], cwd=BACKEND, env=child_env,
                                      capture_output=True, text=True, timeout=600)
            finally:
                if drop:
                    drop()
            line = (proc.stdout.strip().splitlines() or ["{}"])[-1]
            try:
                results[name] = json.loads(line)
            except ValueError:
                results[name] = {"error": (proc.stderr or proc.stdout)[-600:]}
    print(json.dumps({"db": args.db, "results": results}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
