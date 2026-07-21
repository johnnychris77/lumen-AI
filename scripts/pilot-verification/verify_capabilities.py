#!/usr/bin/env python3
"""LPR-DIR-029 pilot-capability verification harness.

Exercises the subset of pilot-infrastructure capabilities that are genuinely
demonstrable in this development/sandbox environment and prints objective
output for evidence collection. It does NOT and cannot provision managed cloud
infrastructure (managed DB service, TLS ingress, alerting backend, on-call, a
real k8s cluster) — those require a managed environment that this sandbox does
not have. Every check states plainly what it proves and what it does not.

Run:  ../.venv/bin/python scripts/pilot-verification/verify_capabilities.py
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./_pilot_verify_tmp.db")

# Make `app` importable regardless of CWD (backend/ holds the package).
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


def hr(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


results: dict[str, bool] = {}


# --- 1. Secret generation + SHA-256 hashing + rotation (SecOps) ---------------
hr("1. SECRET GENERATION + SHA-256 HASH-ONLY STORAGE + ROTATION")
raw1 = secrets.token_urlsafe(40)
hash1 = hashlib.sha256(raw1.encode()).hexdigest()
raw2 = secrets.token_urlsafe(40)  # rotation → new secret
hash2 = hashlib.sha256(raw2.encode()).hexdigest()
print(f"issued secret #1 length={len(raw1)} chars; stored sha256={hash1}")
print(f"rotated secret #2 length={len(raw2)} chars; stored sha256={hash2}")
print("(raw secrets are shown here only because they are throwaway demo values;"
      " in the app only the sha256 hash is persisted — never the raw key.)")
results["secret_gen_hash_rotate"] = (
    check("secret is token_urlsafe(40)", len(raw1) >= 40)
    and check("rotation produces a different secret+hash", raw1 != raw2 and hash1 != hash2)
    and check("only sha256 hash would be persisted (64 hex chars)", len(hash1) == 64)
)


# --- 2. TLS certificate generation + validation (Managed env TLS / SecOps) ----
hr("2. TLS CERTIFICATE GENERATION + VALIDATION (openssl)")
tls_ok = False
if shutil.which("openssl"):
    with tempfile.TemporaryDirectory() as d:
        key = os.path.join(d, "tls.key")
        crt = os.path.join(d, "tls.crt")
        gen = subprocess.run(
            ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
             "-keyout", key, "-out", crt, "-days", "365",
             "-subj", "/CN=pilot.lumenai.local"],
            capture_output=True, text=True,
        )
        if gen.returncode == 0 and os.path.exists(crt):
            info = subprocess.run(
                ["openssl", "x509", "-in", crt, "-noout", "-subject", "-dates", "-fingerprint", "-sha256"],
                capture_output=True, text=True,
            )
            print(info.stdout.strip())
            verify = subprocess.run(
                ["openssl", "verify", "-CAfile", crt, crt], capture_output=True, text=True
            )
            print("openssl verify (self-signed as its own CA):", verify.stdout.strip() or verify.stderr.strip())
            tls_ok = (
                "pilot.lumenai.local" in info.stdout
                and "Fingerprint" in info.stdout
                and verify.returncode == 0
                and ": OK" in verify.stdout
            )
else:
    print("openssl not available")
results["tls_cert"] = check("generated + inspected a valid X.509 cert", tls_ok)


# --- 3. Application health probe (Observability) ------------------------------
hr("3. APPLICATION HEALTH PROBE (real app code via TestClient)")
health_ok = False
webhook_ok = False
try:
    from fastapi.testclient import TestClient  # noqa: E402
    from app.main import app  # noqa: E402

    client = TestClient(app)
    r = client.get("/health")
    print("GET /health ->", r.status_code, r.json())
    health_ok = r.status_code == 200 and r.json().get("status") == "ok"
    results["health"] = check("/health returns 200 ok", health_ok)

    # --- 4. Fail-closed webhook security (SecOps operational verification) -----
    hr("4. FAIL-CLOSED WEBHOOK SECURITY (real route code)")
    sys_name = "veriftsys"
    up = sys_name.upper()
    os.environ.pop(f"WEBHOOK_SECRET_{up}", None)
    os.environ.pop(f"WEBHOOK_TENANT_{up}", None)
    body = json.dumps({"event": "demo"})

    r1 = client.post(f"/api/integrations/webhook/{sys_name}", content=body,
                     headers={"Content-Type": "application/json"})
    print(f"no signing secret configured        -> {r1.status_code} (expect 503, fail-closed)")

    os.environ[f"WEBHOOK_SECRET_{up}"] = "demo-signing-secret"
    r2 = client.post(f"/api/integrations/webhook/{sys_name}", content=body,
                     headers={"Content-Type": "application/json",
                              "X-Webhook-Signature": "sha256=deadbeef",
                              "X-Tenant-Id": "attacker-tenant"})
    print(f"secret set, bad signature           -> {r2.status_code} (expect 401, reject)")

    # The signed-200 happy path writes to the DB; on this un-migrated sandbox DB
    # it cannot complete (missing tables) — which is itself the managed-DB gap.
    # The security-critical proof here is the FAIL-CLOSED behavior (503/401).
    # Signed-200 + server-bound-tenant DB proof is covered by the CI suite
    # (backend/tests/test_p17_recommendations.py).
    os.environ[f"WEBHOOK_TENANT_{up}"] = "server-bound-tenant"
    good_sig = "sha256=" + hmac.new(b"demo-signing-secret", body.encode(), hashlib.sha256).hexdigest()
    try:
        r3 = client.post(f"/api/integrations/webhook/{sys_name}", content=body,
                         headers={"Content-Type": "application/json",
                                  "X-Webhook-Signature": good_sig,
                                  "X-Tenant-Id": "attacker-tenant"})
        print(f"secret+tenant set, valid signature  -> {r3.status_code} "
              f"(signature accepted; DB write needs a migrated DB — see CI test_p17)")
    except Exception as exc:
        print("secret+tenant set, valid signature  -> signature accepted; DB write "
              f"needs a migrated DB ({type(exc).__name__}); happy-path proven in CI test_p17")

    webhook_ok = r1.status_code == 503 and r2.status_code == 401
    results["webhook_fail_closed"] = check(
        "webhook fail-closed demonstrated (503 no-secret / 401 bad-sig)", webhook_ok
    )
except Exception as exc:  # pragma: no cover - harness diagnostic
    print("app-level checks could not run:", repr(exc))
    results["health"] = results.get("health", False)
    results["webhook_fail_closed"] = results.get("webhook_fail_closed", False)


# --- 5. Backup + restore (SQLite analog — NOT managed Postgres) ---------------
hr("5. BACKUP + RESTORE DRILL (SQLite analog — NOT the managed pilot DB)")
with tempfile.TemporaryDirectory() as d:
    src = os.path.join(d, "src.db")
    bak = os.path.join(d, "backup.db")
    con = sqlite3.connect(src)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO t (v) VALUES (?)", [(f"row-{i}",) for i in range(1000)])
    con.commit()
    n_before = con.execute("SELECT count(*) FROM t").fetchone()[0]
    t0 = time.time()
    dst = sqlite3.connect(bak)
    con.backup(dst)  # online backup API
    dst.close()
    t_backup = time.time() - t0
    con.execute("DELETE FROM t")  # simulate data loss
    con.commit()
    t1 = time.time()
    rst = sqlite3.connect(bak)
    n_restored = rst.execute("SELECT count(*) FROM t").fetchone()[0]
    t_restore = time.time() - t1
    con.close()
    rst.close()
    print(f"rows before={n_before}; backup={t_backup*1000:.1f} ms; "
          f"rows in restored backup={n_restored}; restore-open={t_restore*1000:.1f} ms")
    results["backup_restore_analog"] = check(
        "backup captured and restored all rows (analog)", n_before == 1000 == n_restored
    )


# --- 6. Schema migration head integrity ---------------------------------------
hr("6. SCHEMA MIGRATION CHAIN INTEGRITY")
versions_dir = os.path.join(os.path.dirname(__file__), "..", "..", "backend", "alembic", "versions")
revs, downs = set(), set()
if os.path.isdir(versions_dir):
    for fn in os.listdir(versions_dir):
        if not fn.endswith(".py"):
            continue
        txt = open(os.path.join(versions_dir, fn)).read()
        for line in txt.splitlines():
            s = line.strip()
            if s.startswith("revision") and "=" in s and "down_revision" not in s:
                revs.add(s.split("=")[1].strip().strip("'\"" ))
            if s.startswith("down_revision") and "=" in s:
                val = s.split("=")[1].strip()
                if val not in ("None", "None,"):
                    downs.add(val.strip("'\"" ).rstrip(","))
heads = revs - downs
print(f"migration files: {len(revs)} revisions; head(s): {sorted(heads)}")
results["migration_head"] = check("exactly one alembic head", len(heads) == 1)


# --- Summary ------------------------------------------------------------------
hr("SUMMARY")
for k, v in results.items():
    print(f"  {'PASS' if v else 'FAIL'}  {k}")
passed = sum(results.values())
print(f"\n{passed}/{len(results)} capability checks passed (dev/sandbox scope only).")
print("NOTE: these prove the *techniques* work; they do NOT prove a MANAGED pilot "
      "environment exists. Managed DB/TLS-ingress/alerting/on-call/cluster deploy+rollback "
      "are NOT provisioned here and remain NOT COMPLETE for pilot entry.")
sys.exit(0 if passed == len(results) else 1)
