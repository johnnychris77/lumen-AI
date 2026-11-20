#!/usr/bin/env python3
"""P472-03 tripwire review kit (RB-T01 ... RB-T28) for NON-AUTHOR reviewers.

The kit reproduces each security tripwire before and after its fix, in a
throw-away git worktree with a fresh database, and reports what the test did.
It decides nothing: dispositions are recorded by a reviewer in
``docs/enterprise-readiness/p472-03-batch7-tripwire-disposition-ledger-v1.md``.

For every test-based tripwire it runs up to four variants:

  before/original  code before the fix  + test file as it was while still marked xfail
  before/final     code before the fix  + test file as it is now (the assertions under review)
  after/final      code after the fix   + test file as it is now
  after/original   code after the fix   + test file as it was while still marked xfail

``--runxfail`` is always passed, so a marker never hides an outcome. The expected
picture for a genuine fix is: both ``before`` variants FAIL on an assertion (not
on set-up or import), both ``after`` variants PASS. Where the assertion was
amended (RB-T18) ``after/original`` is expected to fail; the reviewer judges
whether the amendment preserves the security intent (``diff`` sub-command).

Register-driven tripwires (RB-T01, RB-T12..RB-T14) are checked with the sweep
oracle that existed at each SHA (``sweep`` sub-command).

Nothing here touches production. Databases are local and created per run.

Usage (from the repository root or backend/):
  python backend/scripts/p472_03_tripwire_review_kit.py list
  python backend/scripts/p472_03_tripwire_review_kit.py diff RB-T18
  python backend/scripts/p472_03_tripwire_review_kit.py run --db sqlite --out /tmp/kit-sqlite
  python backend/scripts/p472_03_tripwire_review_kit.py run --db postgres \
      --pg-admin-url postgresql://USER:PW@localhost:5432/postgres --out /tmp/kit-pg
  python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha 4fdac4c --out /tmp/sweep-4fdac4c.json
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

F = "backend/tests/test_p472_03_application_wide_findings.py"
G = "backend/tests/test_p472_03_batch5_genesis_gd6.py"
X = "backend/tests/test_p472_03_batch5_guardianx_gd7.py"
H = "backend/tests/test_p472_03_batch2_remediation.py"
Y = "backend/tests/test_p472_03_batch7_guardianx_source_ownership.py"
Z = "backend/tests/test_p472_03_batch8_guardianx_explanations.py"
P = "backend/tests/test_p472_03_batch8_pa1_env_gates.py"

# Same-tenant / legitimate-access controls run on the code under review. A fix that
# refuses everyone would pass the tripwire and fail these.
CONTROLS: dict[str, list[tuple[str, str]]] = {
    F: [(F, "test_control_verified_context_routes_ignore_or_refuse_a_foreign_tenant"),
        (F, "test_control_tenant_role_dependency_verifies_the_header_it_uses"),
        (H, "owner")],  # route-wide harness: the owning tenant is served on every resolver route
    G: [(G, name) for name in (
        "test_the_submitting_tenant_sees_its_own_pending_update",
        "test_published_content_is_visible_network_wide",
        "test_an_update_is_stored_under_the_submitters_verified_tenant",
        "test_the_owning_tenant_can_still_review_its_own_update_and_it_is_audited",
        "test_the_publisher_filter_works_for_the_callers_own_tenant",
        "test_the_owner_sees_its_own_identities",
        "test_superseding_own_update_still_works",
        "test_another_tenants_id_and_a_missing_id_are_indistinguishable")],
    X: [(X, name) for name in (
        "test_the_owning_tenant_reads_lists_and_verifies_its_entry",
        "test_multi_member_sees_an_entry_only_while_selecting_its_tenant",
        "test_a_user_without_membership_is_refused",
        "test_a_legacy_pooled_entry_is_readable_by_no_tenant",
        "test_a_tampered_own_entry_stays_visible_to_its_owner_as_tampered",
        "test_a_write_cannot_claim_another_tenant",
        "test_the_owning_tenant_can_replay_its_execution_and_rule")],
    Y: [(Y, name) for name in (
        "test_owner_writes_evidence_for_its_inspection",
        "test_owner_writes_evidence_for_its_workflow_execution",
        "test_owner_can_write_repeatedly_to_its_own_ownerless_key",
        "test_a_fresh_ownerless_key_is_writable",
        "test_owner_attaches_an_explanation_to_its_inspection",
        "test_digital_twin_context_for_the_callers_own_tenant_still_works")],
    P: [(P, "test_control_render_configuration_is_closed"),
        (P, "test_control_unset_auth_mode_in_production_refuses_to_start")],
    Z: [(Z, name) for name in (
        "test_owner_lists_reads_and_overrides_its_explanation",
        "test_owner_can_add_several_explanations_to_its_own_key",
        "test_owner_sees_its_inspection_explanation_in_replay_and_package",
        "test_owner_replay_reports_its_own_audit_chain",
        "test_a_least_privileged_member_of_the_owner_reads_it",
        "test_explanation_for_a_deleted_source_is_refused",
        "test_unauthenticated_explanation_reads_are_refused")],
}


@dataclass
class Item:
    id: str
    finding: str
    test_file: str | None      # None for register-driven (sweep) items
    test: str | None
    before_code: str           # application code before the fix
    original_tests: str | None # test file while the tripwire was still marked
    converted_in: str          # commit that removed the marker / regenerated the register
    note: str = ""
    sweep_class: str | None = None
    supplementary: bool = False
    gov: str = ""
    open_finding: bool = False  # tripwire still failing on purpose (not fixed)


ITEMS: list[Item] = [
    Item("RB-T01", "AW-04 GET /api/genesis-ai/manufacturer-updates", None, None, "9f2b6e3", None, "38251e6",
         "register-driven; the route itself is RB-T18's route", sweep_class="AW-04", gov="GD-6"),
    Item("RB-T02", "AW-03", F, "test_aw03_a_member_of_a_cannot_opt_tenant_b_into_the_intelligence_network",
         "4fdac4c", "4fdac4c", "5adde8d"),
    Item("RB-T03", "AW-04", F, "test_aw04_a_member_of_a_cannot_create_an_accreditation_program_in_tenant_b",
         "5adde8d", "5adde8d", "76d7fc3"),
    Item("RB-T04", "AW-04", F, "test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs",
         "137e9b1", "5adde8d", "76d7fc3",
         "fixed by fbd2581 (AW-08a); before = fbd2581^. The Batch 5 packet's 30638f0^ was wrong: the test passes "
         "there (Batch 7 kit run)"),
    Item("RB-T05", "AW-04", F, "test_aw04_a_member_of_a_cannot_grant_data_sharing_consent_for_tenant_b",
         "5adde8d", "5adde8d", "76d7fc3"),
    Item("RB-T06", "AW-04", F, "test_aw04_a_member_of_a_cannot_read_tenant_b_network_registry_entry",
         "5adde8d", "5adde8d", "76d7fc3"),
    Item("RB-T07", "AW-06M", F, "test_aw06m_members_of_different_tenants_do_not_share_a_default_tenant",
         "4fdac4c", "4fdac4c", "5adde8d"),
    Item("RB-T08", "AW-06N", F,
         "test_aw06n_users_with_no_membership_are_still_pooled_where_the_default_is_a_literal",
         "4308443", "4308443", "cea6d7f"),
    Item("RB-T09", "AW-08a", F, "test_aw08_listing_accreditation_programs_does_not_return_other_tenants",
         "137e9b1", "cea6d7f", "c826fcc", "fix fbd2581 predates the marker removal c826fcc; before = fbd2581^"),
    Item("RB-T10", "AW-08b", F, "test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections",
         "4ee1674", "cea6d7f", "c826fcc", "fix 137e9b1; before = 137e9b1^"),
    Item("RB-T11", "AW-08c", F, "test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection",
         "b7b2295", "cea6d7f", "c826fcc", "fix ae54f5e; before = ae54f5e^"),
    Item("RB-T12", "AW-03 (sweep class)", None, None, "4fdac4c", None, "5adde8d", sweep_class="AW-03"),
    Item("RB-T13", "AW-06M (sweep class)", None, None, "4fdac4c", None, "5adde8d", sweep_class="AW-06M"),
    Item("RB-T14", "AW-06N (sweep class)", None, None, "4fdac4c", None, "cea6d7f", sweep_class="AW-06N"),
    *[
        Item(rb, f"GD6-{n:02d}", G, t, "9f2b6e3", "9f2b6e3", "38251e6", gov="GD-6",
             note="ASSERTION AMENDED in 38251e6 (request now refused): reviewer must judge" if rb == "RB-T18" else "")
        for rb, n, t in [
            ("RB-T15", 1, "test_another_tenant_cannot_read_a_pending_update_by_id"),
            ("RB-T16", 2, "test_the_feed_does_not_list_another_tenants_unpublished_updates"),
            ("RB-T17", 3, "test_status_filter_does_not_reveal_another_tenants_pending_updates"),
            ("RB-T18", 4, "test_publisher_filter_does_not_reveal_unpublished_content"),
            ("RB-T19", 5, "test_version_chain_does_not_disclose_unpublished_versions"),
            ("RB-T20", 6, "test_another_tenant_cannot_publish"),
            ("RB-T21", 7, "test_another_tenant_cannot_reject"),
            ("RB-T22", 8, "test_cannot_supersede_another_tenants_update"),
            ("RB-T23", 9, "test_other_tenants_do_not_see_submitter_identities"),
        ]
    ],
    *[
        Item(rb, f"GD7-{n:02d}", X, t, "e2173c2", "e2173c2", "3f479d9", gov="GD-7",
             note=("LIMITED COVERAGE: proves read-side filtering only (B6.2). It does NOT show that a foreign "
                   "write is refused; its set-up seeds the foreign entry through the service. Write-side "
                   "authorization is RB-T29/RB-T30/RB-T31/RB-T33 (Batch 7) and is only a partial floor (GD-7). "
                   "Do not cite RB-T28 as write authorization.") if rb == "RB-T28" else "")
        for rb, n, t in [
            ("RB-T24", 1, "test_another_tenant_cannot_read_an_entry_by_id"),
            ("RB-T25", 2, "test_listing_by_source_returns_only_own_entries"),
            ("RB-T26", 3, "test_another_tenant_cannot_verify_an_entry"),
            ("RB-T27", 4, "test_reviewer_identity_is_not_disclosed_cross_tenant"),
            ("RB-T28", 5, "test_another_tenant_cannot_contaminate_a_source"),
        ]
    ],
    # Batch 7 (GD7-05 write side): reproduced at 4667ab8. RB-T32 stayed a failing tripwire through
    # 83dbf70 and is converted in Batch 8 (c22a879); its own item follows below.
    *[
        Item(rb, finding, Y, t, "4667ab8", None, "6a661bb", gov="GD-7")
        for rb, finding, t in [
            ("RB-T29", "GD7-06 ledger write under a foreign owned source",
             "test_another_tenant_cannot_write_evidence_under_an_owned_inspection"),
            ("RB-T30", "GD7-07 ledger write into an ownerless key in use",
             "test_another_tenant_cannot_write_into_an_ownerless_key_in_use"),
            ("RB-T31", "GX-08 explanation under a foreign owned source",
             "test_another_tenant_cannot_attach_an_explanation_to_an_owned_inspection"),
            ("RB-T33", "GX-10 digital-twin tenant claim",
             "test_digital_twin_context_cannot_name_another_tenant"),
        ]
    ],
    Item("RB-T32", "GX-09 explanations disclosed cross-tenant", Y,
         "test_explanations_are_not_disclosed_to_another_tenant", "83dbf70", "6a661bb", "c22a879", gov="GD-7",
         note=("Failing strict tripwire from 6a661bb to 83dbf70 (also reproduced at 4667ab8). Converted by the "
               "audit-trail ownership floor, which chooses no GD-7 option; legacy explanations become unavailable "
               "to every tenant (R-GX-EXPLAIN-LEGACY).")),
    # Batch 8 (explanation ownership): committed failing at eec3bc8 (application code = 83dbf70).
    *[
        Item(rb, finding, Z, t, "83dbf70", "eec3bc8", "c22a879", gov="GD-7")
        for rb, finding, t in [
            ("RB-T34", "GX-11 human override on another tenant's explanation",
             "test_another_tenant_cannot_override_an_explanation"),
            ("RB-T35", "GX-12 explanation written into an ownerless key in use",
             "test_another_tenant_cannot_write_an_explanation_into_a_key_in_use"),
            ("RB-T36", "GX-13 unattributable (legacy) explanation served to every tenant",
             "test_an_unattributable_explanation_is_served_to_no_tenant"),
            ("RB-T37", "GX-14 replay reports another tenant's audit chain (GD-2 scope)",
             "test_replay_does_not_report_another_tenants_audit_chain"),
        ]
    ],
    # Batch 8 PA-1 investigation: OPEN findings, no fix (PA-1 unsigned). Expected to FAIL everywhere.
    *[
        Item(rb, finding, P, t, "c22a879", None, "-", gov="PA-1", open_finding=True,
             note="OPEN FINDING: strict xfail; PA-1 unsigned, no gate changed; expected to FAIL on the code under review")
        for rb, finding, t in [
            ("RB-T38", "PA1-01 dev tokens active with ENVIRONMENT=production, APP_ENV unset",
             "test_dev_tokens_are_inactive_whenever_any_production_signal_is_set"),
            ("RB-T39", "PA1-02 DEMO_MODE public dev-token on destructive /api/demo/reset in production",
             "test_demo_reset_is_not_reachable_with_the_public_token_in_production"),
            ("RB-T40", "PA1-03 enterprise JWT-shape check ignores APP_ENV / is case-sensitive",
             "test_enterprise_jwt_shape_check_follows_every_production_signal"),
        ]
    ],
    # Not tripwires: regressions found during B6.2 and fixed with them; reviewed in the same way.
    Item("S-REPLAY-EMBED", "replay embedded other tenants' ledger entries", X,
         "test_replay_by_source_embeds_only_the_callers_entries", "e2173c2", None, "3f479d9", supplementary=True),
    Item("S-REPLAY-WFX", "workflow-execution replay by id across tenants", X,
         "test_another_tenant_cannot_replay_a_workflow_execution", "3f479d9", None, "00aec32", supplementary=True),
    Item("S-REPLAY-RULE", "rule replay by id across tenants", X,
         "test_another_tenant_cannot_replay_a_workflow_rule", "3f479d9", None, "00aec32", supplementary=True),
]


@dataclass
class Result:
    id: str
    variant: str
    code_sha: str
    tests_sha: str
    db: str
    outcome: str  # passed | failed | error | skipped | not-collected | test-absent
    message: str = ""
    seconds: float = 0.0
    extra: dict = field(default_factory=dict)


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         cwd=Path(__file__).resolve().parent, check=True)
    return Path(out.stdout.strip())


def git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True,
                          cwd=cwd or repo_root()).stdout


def full_sha(ref: str) -> str:
    return git("rev-parse", ref).strip()


def show(sha: str, path: str) -> str | None:
    r = subprocess.run(["git", "show", f"{sha}:{path}"], capture_output=True, text=True, cwd=repo_root())
    return r.stdout if r.returncode == 0 else None


def function_source(src: str, name: str) -> str | None:
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            lines = src.splitlines()
            start = min([d.lineno for d in node.decorator_list] + [node.lineno]) - 1
            return "\n".join(lines[start:node.end_lineno]) + "\n"
    return None


def body_dump(src: str, name: str) -> str | None:
    """AST of a test function's arguments and body, ignoring decorators and formatting."""
    for node in ast.walk(ast.parse(src or "\n")):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.dump(node.args) + "".join(ast.dump(n) for n in node.body)
    return None


class Worktrees:
    def __init__(self, base: Path):
        self.base, self.trees = base, {}

    def get(self, sha: str) -> Path:
        if sha not in self.trees:
            path = self.base / f"wt-{sha[:12]}"
            git("worktree", "add", "--detach", "--force", str(path), sha)
            self.trees[sha] = path
        return self.trees[sha]

    def close(self):
        for path in self.trees.values():
            subprocess.run(["git", "worktree", "remove", "--force", str(path)], cwd=repo_root(),
                           capture_output=True)


def fresh_database(db: str, workdir: Path, pg_admin_url: str | None) -> tuple[str, callable]:
    if db == "sqlite":
        path = workdir / f"db-{uuid.uuid4().hex[:8]}.sqlite"
        return f"sqlite:///{path}", lambda: path.unlink(missing_ok=True)
    from sqlalchemy import create_engine, text  # the backend's own dependency
    name = f"rbkit_{uuid.uuid4().hex[:10]}"
    admin = create_engine(pg_admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{name}"'))
    url = pg_admin_url.rsplit("/", 1)[0] + "/" + name

    def drop():
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()
    return url, drop


def run_variant(item: Item, variant: str, code_sha: str, tests_sha: str, trees: Worktrees, db: str,
                workdir: Path, pg_admin_url: str | None) -> Result:
    import time
    src = show(tests_sha, item.test_file)
    if src is None or f"def {item.test}(" not in src:
        return Result(item.id, variant, code_sha, tests_sha, db, "test-absent",
                      f"{item.test} not in {item.test_file} at {tests_sha[:7]}")
    tree = trees.get(code_sha)
    target = tree / item.test_file
    target.parent.mkdir(parents=True, exist_ok=True)
    original = target.read_text() if target.exists() else None
    target.write_text(src)
    url, drop = fresh_database(db, workdir, pg_admin_url)
    junit = workdir / f"{item.id}-{variant.replace('/', '-')}-{db}.xml"
    env = {**os.environ, "DATABASE_URL": url}
    started = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", item.test_file.removeprefix("backend/"), "-q", "-p", "no:cacheprovider",
             "--runxfail", "-k", item.test, f"--junitxml={junit}"],
            cwd=tree / "backend", env=env, capture_output=True, text=True, timeout=900)
    finally:
        drop()
        if original is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(original)
    outcome, message = parse_junit(junit, item.test)
    if outcome == "not-collected":
        message = (proc.stdout + proc.stderr)[-600:]
    return Result(item.id, variant, code_sha, tests_sha, db, outcome, message, round(time.time() - started, 1))


def parse_junit(path: Path, test: str) -> tuple[str, str]:
    if not path.exists():
        return "not-collected", ""
    root = ET.parse(path).getroot()
    cases = [c for c in root.iter("testcase") if c.get("name") == test]
    if not cases:
        errors = [e.get("message", "") for e in root.iter("error")]
        return ("error", errors[0][:400]) if errors else ("not-collected", "")
    case = cases[0]
    for tag in ("failure", "error", "skipped"):
        node = case.find(tag)
        if node is not None:
            msg = (node.get("message") or (node.text or "")).strip().splitlines()
            return {"failure": "failed", "error": "error", "skipped": "skipped"}[tag], (msg[0] if msg else "")[:400]
    return "passed", ""


def run_controls(after: str, trees: Worktrees, db: str, workdir: Path, pg_admin_url: str | None) -> dict:
    """Run every group's legitimate-access controls once on the code under review."""
    tree = trees.get(after)
    by_file: dict[str, list[str]] = {}
    for group in CONTROLS.values():
        for path, name in group:
            by_file.setdefault(path, []).append(name)
    report = {}
    for path, names in by_file.items():
        url, drop = fresh_database(db, workdir, pg_admin_url)
        junit = workdir / f"controls-{Path(path).stem}-{db}.xml"
        try:
            subprocess.run(
                [sys.executable, "-m", "pytest", path.removeprefix("backend/"), "-q", "-p", "no:cacheprovider",
                 "-k", " or ".join(sorted(set(names))), f"--junitxml={junit}"],
                cwd=tree / "backend", env={**os.environ, "DATABASE_URL": url}, capture_output=True, text=True,
                timeout=3600)
        finally:
            drop()
        counts: dict[str, int] = {}
        failures = []
        if junit.exists():
            for case in ET.parse(junit).getroot().iter("testcase"):
                state = next((t for t in ("failure", "error", "skipped") if case.find(t) is not None), "passed")
                counts[state] = counts.get(state, 0) + 1
                if state in ("failure", "error"):
                    failures.append(case.get("name"))
        report[path] = {"selection": sorted(set(names)), "counts": counts, "failures": failures}
        print(f"controls {path}: {counts}", flush=True)
    return report


def cmd_report(args):
    """Render the review packets from kit-results-*.json (author evidence) as Markdown."""
    runs = {}
    for path in args.results:
        data = json.loads(Path(path).read_text())
        runs[data["meta"]["db"]] = data
    after = next(iter(runs.values()))["meta"]["after"]
    out = [f"<!-- generated by backend/scripts/p472_03_tripwire_review_kit.py report; code under review {after} -->"]
    for it in ITEMS:
        out.append(f"\n### {it.id} — {it.finding}" + (" (supplementary, not a tripwire)" if it.supplementary else ""))
        rows = [
            ("Test", f"`{it.test_file.removeprefix('backend/')}::{it.test}`" if it.test
             else f"register-driven `test_no_route_exhibits[{it.sweep_class}]` (sweep oracle)"),
            ("Before (code)", f"`{it.before_code}`" + (f" — {it.note}" if it.note and "before" in it.note else "")),
            ("Original assertions", f"`{it.original_tests}` (marked xfail)" if it.original_tests else "—"),
            ("Converted in", f"`{it.converted_in}`"),
            ("After (code under review)", f"`{after[:10]}`"),
            ("Governance dependency", it.gov or "—"),
        ]
        if it.note and "before" not in it.note:
            rows.append(("Reviewer note", f"**{it.note}**"))
        if it.test:
            orig_sha = it.original_tests or it.converted_in
            same =body_dump(show(orig_sha, it.test_file) or "", it.test) == body_dump(show(after, it.test_file) or "",
                                                                                  it.test)
            changed = ("unchanged (AST-identical body; only decorators differ)" if same else
                       "**CHANGED — read the diff (`kit diff " + it.id + "`)**")
            rows.append(("Assertion change", changed if it.original_tests else "new with the fix"))
            ctrl = CONTROLS.get(it.test_file, [])
            rows.append(("Same-tenant controls", ", ".join(f"`{n}`" for _, n in ctrl) or "—"))
        out.append("| Field | Value |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in rows))
        if it.test:
            out.append("\n| DB | Variant | Expected | Author run | Message (first line) |\n|---|---|---|---|---|")
            for db, data in sorted(runs.items()):
                for r in data["results"]:
                    if r["id"] == it.id:
                        out.append(f"| {db} | {r['variant']} | {r['extra']['expected']} | **{r['outcome']}** | "
                                   f"{r['message'][:140].replace('|', '/')} |")
        out.append(f"\nCommand: `python backend/scripts/p472_03_tripwire_review_kit.py run --ids {it.id} --db sqlite "
                   f"--out <dir>`" if it.test else
                   f"\nCommand: `python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha {it.before_code} "
                   f"--out before.json` and `--sha {after[:10]}`; count routes with `{it.sweep_class}`.")
        if not it.supplementary:
            out.append("\n| Reviewer field | Value |\n|---|---|\n| Reviewer (name, affiliation) | **UNASSIGNED** |\n"
                       "| Independence statement (not an author of the change) | — |\n| Commands run / evidence link | — |\n"
                       "| Authorization predicate inspected (file:line) | — |\n| Date | — |\n"
                       "| Disposition (ACCEPT-CONVERSION / REJECT-CONVERSION / ACCEPT-RISK + owner / PENDING) | "
                       "**PENDING** |")
    Path(args.out).write_text("\n".join(out) + "\n")
    print(f"wrote {args.out}")


def expected(item: Item, variant: str) -> str:
    if variant.startswith("before"):
        return "failed"
    if item.open_finding:
        return "failed (OPEN finding)"
    if variant == "after/original" and item.id == "RB-T18":
        return "failed (amended assertion; see diff)"
    if variant == "after/original" and item.id == "RB-T28":
        return "failed (original set-up's foreign write is now refused, Batch 7)"
    return "passed"


def cmd_list(_args):
    print(f"{'id':16} {'finding':48} before   original converted  test")
    for it in ITEMS:
        print(f"{it.id:16} {it.finding[:48]:48} {it.before_code:8} {str(it.original_tests or '-'):8} "
              f"{it.converted_in:9}  {it.test or ('sweep:' + str(it.sweep_class))}")


def cmd_diff(args):
    after = args.after
    for it in ITEMS:
        if it.id != args.id:
            continue
        if not it.test:
            print(f"{it.id} is register-driven: compare the findings register and the sweep instead.")
            return
        orig_sha = it.original_tests or it.converted_in
        old = function_source(show(orig_sha, it.test_file) or "", it.test) or ""
        new = function_source(show(after, it.test_file) or "", it.test) or ""
        print("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                           f"{it.test_file}@{orig_sha} (original)",
                                           f"{it.test_file}@{after[:7]} (final)")) or "(identical)")
        return
    sys.exit(f"unknown id {args.id}")


def cmd_run(args):
    if args.db == "postgres" and not args.pg_admin_url:
        sys.exit("--pg-admin-url is required for --db postgres")
    after = full_sha(args.after)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="rbkit-"))
    trees = Worktrees(work)
    results: list[Result] = []
    wanted = set(args.ids.split(",")) if args.ids else None
    try:
        for it in ITEMS:
            if not it.test or (wanted and it.id not in wanted):
                continue
            variants = [("before/final", it.before_code, after), ("after/final", after, after)]
            if it.original_tests:
                variants[1:1] = [("before/original", it.before_code, it.original_tests)]
                variants.append(("after/original", after, it.original_tests))
            for name, code, tests in variants:
                r = run_variant(it, name, full_sha(code), full_sha(tests), trees, args.db, work, args.pg_admin_url)
                r.extra["expected"] = expected(it, name)
                results.append(r)
                print(f"{r.id:16} {name:16} {r.outcome:13} expected={r.extra['expected']:10} {r.message[:110]}",
                      flush=True)
        if not args.ids:
            controls = run_controls(after, trees, args.db, work, args.pg_admin_url)
        else:
            controls = {}
    finally:
        trees.close()
        shutil.rmtree(work, ignore_errors=True)
    meta = {"after": after, "db": args.db, "python": sys.version.split()[0], "note":
            "author-generated reproduction; NOT an independent review"}
    (out / f"kit-results-{args.db}.json").write_text(
        json.dumps({"meta": meta, "results": [asdict(r) for r in results], "controls": controls}, indent=1))
    print(f"wrote {out / f'kit-results-{args.db}.json'}")


def cmd_sweep(args):
    sha = full_sha(args.sha)
    work = Path(tempfile.mkdtemp(prefix="rbkit-sweep-"))
    trees = Worktrees(work)
    try:
        tree = trees.get(sha)
        cmd = [sys.executable, "scripts/tenant_isolation_matrix.py", "--sweep", args.db,
               "--workdir", str(work / "sweepwd"), "--out", str(Path(args.out).resolve())]
        if args.db == "postgres":
            cmd += ["--postgres-url", args.pg_url]
        proc = subprocess.run(cmd, cwd=tree / "backend", capture_output=True, text=True, timeout=3600)
        print(proc.stdout[-1500:], proc.stderr[-800:])
    finally:
        trees.close()
        shutil.rmtree(work, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("diff")
    d.add_argument("id")
    d.add_argument("--after", default="HEAD")
    r = sub.add_parser("run")
    r.add_argument("--db", choices=["sqlite", "postgres"], default="sqlite")
    r.add_argument("--pg-admin-url")
    r.add_argument("--after", default="HEAD", help="SHA of the code under review (default HEAD)")
    r.add_argument("--ids", help="comma-separated subset, e.g. RB-T18,RB-T24")
    r.add_argument("--out", required=True)
    s = sub.add_parser("sweep")
    s.add_argument("--sha", required=True)
    s.add_argument("--db", choices=["sqlite", "postgres"], default="sqlite")
    s.add_argument("--pg-url")
    s.add_argument("--out", required=True)
    rp = sub.add_parser("report")
    rp.add_argument("results", nargs="+", help="kit-results-<db>.json files")
    rp.add_argument("--out", required=True)
    args = p.parse_args()
    {"list": cmd_list, "diff": cmd_diff, "run": cmd_run, "sweep": cmd_sweep, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
