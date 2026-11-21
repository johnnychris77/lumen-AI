#!/usr/bin/env python3
"""Milestone 9 (Issue #191) — evidence freeze for independent review.

Freezes the evidence set **as it exists in a given commit** (the baseline SHA),
hashing each file from the git object store at that commit, not from the working tree.
A later edit to the working tree therefore cannot change the frozen record.

  write:   python backend/scripts/m9_evidence_freeze.py freeze --sha bed42c8 \
               --out docs/enterprise-readiness/evidence/m9/freeze-bed42c8.json
  verify:  python backend/scripts/m9_evidence_freeze.py verify \
               docs/enterprise-readiness/evidence/m9/freeze-bed42c8.json

``verify`` recomputes every SHA-256 from ``git show <sha>:<path>``. It also reports, without
failing, whether the working-tree copy still matches. It exits non-zero if any frozen
object differs, is missing, or if the commit's tree id changed.

Scope: the evidence manifest and records, CI run and job ids (from records.json), every
evidence directory, every P472-03 / governance / clinical document (including all preserved
versions of the registers, ledgers, packets and assertion change logs), the review kit and
reproduction scripts, every test file a tripwire depends on, the findings register, the
Alembic versions, and a digest of the whole ``backend/app`` source tree. Read-only: no
network, no database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip())

PREFIXES = (
    "docs/enterprise-readiness/evidence/p472-03-batch7/",
    "docs/enterprise-readiness/evidence/p472-03-batch8/",
    "docs/enterprise-readiness/evidence/p472-03-pa1-remediation/",
    "backend/alembic/versions/",
)
DOC_DIR = "docs/enterprise-readiness/"
DOC_NAME_PREFIXES = ("p472-03-", "gd1-gd4-", "gd3-")
EXTRA = (
    "backend/scripts/p472_03_tripwire_review_kit.py",
    "backend/scripts/p472_03_evidence_manifest.py",
    "backend/scripts/p472_03_pa1_remediation_repro.py",
    "backend/scripts/p472_03_pa1_env_probe.py",
    "backend/scripts/p472_03_gx_explanation_repro.py",
    "backend/scripts/tenant_isolation_matrix.py",
    "backend/tests/p472_03_findings_register.json",
    "backend/tests/test_p472_03_application_wide_findings.py",
    "backend/tests/test_p472_03_application_wide_isolation.py",
    "backend/tests/test_p472_03_batch2_remediation.py",
    "backend/tests/test_p472_03_batch5_genesis_gd6.py",
    "backend/tests/test_p472_03_batch5_guardianx_gd7.py",
    "backend/tests/test_p472_03_batch7_guardianx_source_ownership.py",
    "backend/tests/test_p472_03_batch8_guardianx_explanations.py",
    "backend/tests/test_p472_03_batch8_pa1_env_gates.py",
    "backend/tests/test_p472_03_pa1_remediation.py",
    "backend/app/core/environment.py",
    "render.yaml",
    ".github/workflows/pilot-zero-gate.yml",
)


def git(*args: str, binary: bool = False):
    out = subprocess.run(["git", *args], capture_output=True, cwd=ROOT, check=True).stdout
    return out if binary else out.decode().strip()


def tree_files(sha: str) -> list[str]:
    return git("ls-tree", "-r", "--name-only", sha).splitlines()


def entry(sha: str, path: str) -> dict:
    data = git("show", f"{sha}:{path}", binary=True)
    blob = git("rev-parse", f"{sha}:{path}")
    last = git("log", "-1", "--format=%h %cI", sha, "--", path)
    return {"path": path, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "git_blob": blob,
            "last_commit_at_or_before_sha": last}


def app_tree_digest(sha: str) -> dict:
    lines = git("ls-tree", "-r", sha, "backend/app").splitlines()
    return {"path": "backend/app (recursive ls-tree)", "files": len(lines),
            "sha256_of_ls_tree": hashlib.sha256("\n".join(lines).encode()).hexdigest()}


def select(sha: str) -> list[str]:
    files = tree_files(sha)
    chosen = [f for f in files if f.startswith(PREFIXES)]
    chosen += [f for f in files if f.startswith(DOC_DIR) and "/" not in f[len(DOC_DIR):]
               and f[len(DOC_DIR):].startswith(DOC_NAME_PREFIXES)]
    chosen += [f for f in EXTRA if f in files]
    return sorted(set(chosen))


def ci_records(sha: str) -> list[dict]:
    rec = json.loads(git("show", f"{sha}:docs/enterprise-readiness/evidence/p472-03-batch7/records.json"))
    return [{k: r.get(k) for k in ("id", "sha", "source", "status", "result")}
            for r in rec["records"] if r["class"] == "CI"]


def cmd_freeze(args):
    sha = git("rev-parse", args.sha)
    files = select(sha)
    freeze = {
        "purpose": "Milestone 9 evidence freeze for independent non-author review (Issue #191)",
        "frozen_sha": sha, "tree": git("rev-parse", f"{sha}^{{tree}}"),
        "commit": git("log", "-1", "--format=%H%n%an%n%cI%n%s", sha).splitlines(),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generated_by": "change author (LOCAL-AUTHOR); a freeze is custody, not review",
        "branch_history_from_main": git("log", "--format=%h %s", f"{args.base}..{sha}").splitlines(),
        "ci_records": ci_records(sha) + [dict(x) for x in args.extra_ci],
        "app_source": app_tree_digest(sha),
        "files": [entry(sha, f) for f in files],
    }
    freeze["file_count"] = len(freeze["files"])
    freeze["self_digest"] = hashlib.sha256(json.dumps(freeze["files"], sort_keys=True).encode()).hexdigest()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(freeze, indent=1) + "\n")
    print(f"froze {len(files)} files at {sha[:12]} -> {out} (digest {freeze['self_digest'][:16]})")


def cmd_verify(args):
    freeze = json.loads(Path(args.freeze).read_text())
    sha = freeze["frozen_sha"]
    bad, drift = [], []
    if git("rev-parse", f"{sha}^{{tree}}") != freeze["tree"]:
        bad.append(("<tree>", "tree id differs"))
    if app_tree_digest(sha)["sha256_of_ls_tree"] != freeze["app_source"]["sha256_of_ls_tree"]:
        bad.append(("backend/app", "source digest differs"))
    for f in freeze["files"]:
        try:
            now = entry(sha, f["path"])
        except subprocess.CalledProcessError:
            bad.append((f["path"], "missing at frozen sha"))
            continue
        if now["sha256"] != f["sha256"]:
            bad.append((f["path"], "sha256 differs"))
        wt = ROOT / f["path"]
        if not wt.exists() or hashlib.sha256(wt.read_bytes()).hexdigest() != f["sha256"]:
            drift.append(f["path"])
    print(f"frozen sha {sha[:12]}: {len(freeze['files'])} files checked; {len(bad)} integrity failures; "
          f"{len(drift)} working-tree copies differ from the frozen version (informational)")
    for p, why in bad:
        print(f"  FAIL {p}: {why}")
    for p in drift[:50]:
        print(f"  drift {p}")
    sys.exit(1 if bad else 0)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("freeze")
    f.add_argument("--sha", required=True)
    f.add_argument("--base", default="0f2ec588d24b7c64ccacd84adf67e89cb1ec1676", help="merge base with main")
    f.add_argument("--out", required=True)
    f.add_argument("--extra-ci", type=json.loads, nargs="*", default=[],
                   help='additional CI records as JSON objects, e.g. \'{"id": "CI-x", ...}\'')
    f.set_defaults(fn=cmd_freeze)
    v = sub.add_parser("verify")
    v.add_argument("freeze")
    v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
