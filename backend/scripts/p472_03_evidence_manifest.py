#!/usr/bin/env python3
"""P472-03 SHA-indexed evidence manifest (Batch 7, B7.0).

Builds ``docs/enterprise-readiness/evidence/p472-03-batch7/manifest.json`` and a
Markdown rendering from:

* ``records.json`` (hand-maintained data: every CI job, local run, review and
  signature, each with its evidence class), and
* the repository files it names (preserved artifacts and governing documents),
  hashed with SHA-256 and identified by their git blob id at HEAD.

Evidence classes are kept separate on purpose:
  CI            GitHub Actions job results (author-triggered pushes)
  LOCAL-AUTHOR  runs by the change author in the development container
  INDEPENDENT   runs or reviews by a non-author reviewer   (none exist)
  GOVERNANCE    signed decisions / release authorizations  (none exist)

It also runs consistency checks between code, registers and documents and
reports discrepancies; it never edits a record. Usage:
  python backend/scripts/p472_03_evidence_manifest.py [--check-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           cwd=Path(__file__).resolve().parent, check=True).stdout.strip())
EVID = ROOT / "docs/enterprise-readiness/evidence/p472-03-batch7"
CLASSES = ("CI", "LOCAL-AUTHOR", "INDEPENDENT", "GOVERNANCE")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT, check=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def file_entry(rel: str) -> dict:
    path = ROOT / rel
    if not path.exists():
        return {"path": rel, "missing": True}
    blob = subprocess.run(["git", "rev-parse", f"HEAD:{rel}"], capture_output=True, text=True, cwd=ROOT)
    last = subprocess.run(["git", "log", "-1", "--format=%h %cI", "--", rel], capture_output=True, text=True,
                          cwd=ROOT).stdout.strip()
    return {"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size,
            "git_blob_at_HEAD": blob.stdout.strip() if blob.returncode == 0 else "not committed",
            "last_commit": last or "not committed"}


def alembic_heads() -> list[str]:
    revs, downs = set(), set()
    for f in (ROOT / "backend/alembic/versions").glob("*.py"):
        text = f.read_text()
        rev = re.search(r'^revision\s*[:=][^\n]*?["\']([0-9a-z_]+)["\']', text, re.M)
        down = re.search(r'^down_revision\s*[:=]\s*(.+)$', text, re.M)
        if rev:
            revs.add(rev.group(1))
        if down:
            downs.update(re.findall(r'["\']([0-9a-z_]+)["\']', down.group(1)))
    return sorted(revs - downs)


def checks(records: dict) -> list[dict]:
    out = []

    def add(name, ok, detail):
        out.append({"check": name, "result": "OK" if ok else "DISCREPANCY", "detail": detail})

    heads = alembic_heads()
    add("alembic single head", len(heads) == 1, f"heads={heads}")
    expected_head = records.get("expected_alembic_head")
    add("alembic head matches documented head", heads == [expected_head], f"documented={expected_head}")
    reg = json.loads((ROOT / "backend/tests/p472_03_findings_register.json").read_text())
    add("findings register empty (matches 0-finding sweeps)", not reg.get("findings"),
        f"findings={reg.get('findings')} baseline={reg.get('baseline_commit')}")
    for cls in ("INDEPENDENT", "GOVERNANCE"):
        n = sum(1 for r in records["records"] if r["class"] == cls)
        add(f"{cls} records exist", n > 0, f"{n} record(s) — expected 0 at Batch 7 (none performed)")
    for r in records["records"]:
        if r["class"] not in CLASSES:
            add("record class valid", False, f"{r['id']}: {r['class']}")
        res = r.get("result", {})
        if r.get("status") == "pass" and (res.get("failed") or res.get("errors")):
            add("pass record has no failures", False, r["id"])
        if r.get("status") == "pass" and res.get("skipped") and "skipped" not in r.get("notes", "").lower() \
                and not r.get("skips"):
            add("skips listed for passing record", False, f"{r['id']}: skips not itemised")
    for d in records.get("known_discrepancies", []):
        out.append({"check": d["where"], "result": "DISCREPANCY (recorded)", "detail": d["what"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true")
    args = ap.parse_args()
    records = json.loads((EVID / "records.json").read_text())
    result = checks(records)
    for c in result:
        print(f"{c['result']:24} {c['check']}: {c['detail']}")
    if args.check_only:
        return
    for r in records["records"]:
        if r.get("artifact"):
            p = ROOT / r["artifact"]
            r["artifact_sha256"] = sha256(p) if p.exists() else "MISSING"
    files = [file_entry(rel) for rel in records["governing_files"]]
    for evid_dir in (EVID, ROOT / "docs/enterprise-readiness/evidence/p472-03-batch8",
                     ROOT / "docs/enterprise-readiness/evidence/p472-03-pa1-remediation"):
        files += [file_entry(str(p.relative_to(ROOT))) for p in sorted(evid_dir.rglob("*")) if p.is_file()
                  and p.name not in ("manifest.json", "records.json")]
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "head": git("rev-parse", "HEAD"), "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "note": "Manifest of the tree at 'head' plus any uncommitted evidence it names; the commit that adds "
                "this file is recorded in the release-gate index.",
        "classes": {c: sum(1 for r in records["records"] if r["class"] == c) for c in CLASSES},
        "records": records["records"], "files": files, "checks": result,
    }
    (EVID / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {EVID / 'manifest.json'}: {len(records['records'])} records, {len(files)} files")


if __name__ == "__main__":
    sys.exit(main())
