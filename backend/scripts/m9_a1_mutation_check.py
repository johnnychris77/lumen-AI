#!/usr/bin/env python3
"""Milestone 9 — mutation check for the amended PA-1 probe helper (A-1).

Question for the reviewer: after A-1, do RB-T38 and RB-T39 still detect a broken production
gate, or do they now pass merely because startup refuses?

Each mutation re-opens exactly one gate in a throw-away git worktree of the code under review
and leaves every other gate, including the startup refusal, intact. It then runs
``tests/test_p472_03_batch8_pa1_env_gates.py`` on a fresh database (SQLite, or PostgreSQL when
``--pg-admin-url`` is given). Expected outcomes:

  M0 control                 no change                    every test passes
  M1 environment-always-dev  is_production() -> False     RB-T38, RB-T39, RB-T40 FAIL (startup still refuses)
  M2 deps-ignores-production _DEV_AUTH_ACTIVE ignores prod RB-T38 FAILS (startup still refuses)
  M3 demo-ignores-production demo router prod check gone  RB-T39 FAILS (startup still refuses)
  M4 jwt-shape-ignores-prod  _AUTH_ENV never production    RB-T40 FAILS
  M5 no-startup-refusal      sys.exit(...) removed         RB-T38..T40 still PASS (gates closed at layer
                                                           level); the two startup tests and the unset-
                                                           AUTH_MODE control FAIL

If M1-M3 FAIL as expected, the amended helper still tests the gates themselves, not only
startup. If M5 behaves as expected, the startup refusal is pinned by its own tests.

  python backend/scripts/m9_a1_mutation_check.py --sha HEAD --out /tmp/a1.json
  python backend/scripts/m9_a1_mutation_check.py --sha HEAD --pg-admin-url postgresql://... --out /tmp/a1-pg.json

Local only: no network, no production system. Worktrees are removed afterwards.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip())
TEST = "tests/test_p472_03_batch8_pa1_env_gates.py"
NAMES = {
    "RB-T38": "test_dev_tokens_are_inactive_whenever_any_production_signal_is_set",
    "RB-T39": "test_demo_reset_is_not_reachable_with_the_public_token_in_production",
    "RB-T40": "test_enterprise_jwt_shape_check_follows_every_production_signal",
    "startup-T38": "test_rb_t38_configuration_refuses_to_start",
    "startup-T39": "test_rb_t39_configuration_refuses_to_start",
    "startup-T40": "test_rb_t40_configurations_start",
    "control-render": "test_control_render_configuration_is_closed",
    "control-auth-mode": "test_control_unset_auth_mode_in_production_refuses_to_start",
}
MUTATIONS = {
    "M0-control": ([], {}),
    "M1-environment-always-dev": (
        [("backend/app/core/environment.py", "    return determine_environment(environ).is_production\n",
          "    return False  # M1 mutation\n")],
        {"RB-T38": "failed", "RB-T39": "failed", "RB-T40": "failed"}),
    "M2-deps-ignores-production": (
        [("backend/app/deps.py", "_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH and not _is_production()\n",
          "_DEV_AUTH_ACTIVE = _ENABLE_DEV_AUTH  # M2 mutation\n")],
        {"RB-T38": "failed"}),
    "M3-demo-ignores-production": (
        [("backend/app/routes/demo.py",
          "    if is_production():\n        raise HTTPException(status_code=403, detail=\"Demo routes are disabled in production.\")\n",
          "")],
        {"RB-T39": "failed"}),
    "M4-jwt-shape-ignores-production": (
        [("backend/app/enterprise_auth.py", '_AUTH_ENV = "production" if is_production() else',
          '_AUTH_ENV = "production" if False else')],
        {"RB-T40": "failed"}),
    "M5-no-startup-refusal": (
        [("backend/app/main.py", "    sys.exit(_STARTUP_REFUSAL)\n", "    pass  # M5 mutation\n")],
        # The unset-AUTH_MODE refusal is part of the same startup refusal, so its control fails too.
        # (This expectation was corrected after the first run, which showed it; see the M9 handbook.)
        {"startup-T38": "failed", "startup-T39": "failed", "control-auth-mode": "failed"}),
}


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def outcomes(junit: Path) -> dict:
    res = {}
    for case in ET.parse(junit).getroot().iter("testcase"):
        name = case.get("name")
        state = "passed"
        for tag in ("failure", "error"):
            if case.find(tag) is not None:
                state = "failed"
        if case.find("skipped") is not None:
            state = "skipped"
        res[name] = state
    return {k: res.get(v, "absent") for k, v in NAMES.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sha", default="HEAD")
    ap.add_argument("--pg-admin-url", default="")
    ap.add_argument("--only", help="comma-separated mutation ids")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    sha = run(["git", "rev-parse", args.sha], ROOT).stdout.strip()
    report = {"sha": sha, "db": "postgresql" if args.pg_admin_url else "sqlite", "mutations": {}}
    wanted = set(args.only.split(",")) if args.only else None
    for mid, (edits, expected_fail) in MUTATIONS.items():
        if wanted and mid not in wanted:
            continue
        tmp = Path(tempfile.mkdtemp(prefix="m9a1-"))
        wt = tmp / "wt"
        run(["git", "worktree", "add", "--detach", "-q", str(wt), sha], ROOT)
        try:
            applied = True
            for rel, old, new in edits:
                p = wt / rel
                text = p.read_text()
                if text.count(old) != 1:
                    applied = False
                    break
                p.write_text(text.replace(old, new))
            if not applied:
                report["mutations"][mid] = {"error": "mutation anchor not found exactly once"}
                continue
            env = {**os.environ, "DATABASE_URL": f"sqlite:///{tmp}/suite.db"}
            env.pop("PA1_PG_ADMIN_URL", None)
            if args.pg_admin_url:
                env["PA1_PG_ADMIN_URL"] = args.pg_admin_url
            junit = tmp / "junit.xml"
            run([sys.executable, "-m", "pytest", TEST, "-q", "-p", "no:cacheprovider", f"--junitxml={junit}"],
                wt / "backend", env)
            got = outcomes(junit) if junit.exists() else {}
            expected = {k: expected_fail.get(k, "passed") for k in NAMES}
            report["mutations"][mid] = {
                "expected": expected, "observed": got, "matches_expectation": got == expected,
            }
            print(f"{mid:34} {'MATCH' if got == expected else 'MISMATCH'}  "
                  + " ".join(f"{k}={v}" for k, v in got.items()), flush=True)
        finally:
            run(["git", "worktree", "remove", "--force", str(wt)], ROOT)
            shutil.rmtree(tmp, ignore_errors=True)
    run(["git", "worktree", "prune"], ROOT)
    report["all_match"] = all(m.get("matches_expectation") for m in report["mutations"].values())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    print(f"all mutations behaved as expected: {report['all_match']}")
    return 0 if report["all_match"] else 1


if __name__ == "__main__":
    sys.exit(main())
