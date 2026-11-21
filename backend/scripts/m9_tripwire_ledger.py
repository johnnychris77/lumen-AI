#!/usr/bin/env python3
"""Milestone 9 — generate the forty-tripwire review and disposition ledger.

The ledger is generated from the review kit's own item table
(``p472_03_tripwire_review_kit.ITEMS``), so the reviewer commands, SHAs and test names
cannot drift from what the kit actually runs. Author evidence is summarised from kit result
files given on the command line (latest first); it is labelled LOCAL-AUTHOR and is never a
disposition.

  python backend/scripts/m9_tripwire_ledger.py --baseline bed42c8 \
      --results <kit-results-*.json> ... \
      --out docs/enterprise-readiness/m9-forty-tripwire-review-and-disposition-ledger-v1.md

Every reviewer column is written as UNASSIGNED / PENDING. The script refuses to write
anything else into those columns.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kit", HERE / "p472_03_tripwire_review_kit.py")
kit = importlib.util.module_from_spec(spec)
sys.modules["kit"] = kit
spec.loader.exec_module(kit)

PRIORITY = {
    **{t: ("P1", "privileged authentication (PA-1) + amended helper A-1") for t in ("RB-T38", "RB-T39")},
    "RB-T40": ("P1", "privileged authentication (PA-1)"),
    "RB-T28": ("P1", "GuardianX ownership — READ-SIDE ONLY; must not be accepted as write authorization"),
    **{t: ("P1", "GuardianX cross-tenant writes") for t in ("RB-T29", "RB-T30", "RB-T31", "RB-T33")},
    "RB-T32": ("P1", "GuardianX explanation disclosure"),
    "RB-T34": ("P1", "GuardianX cross-tenant explanation write (override)"),
    "RB-T35": ("P1", "GuardianX ownerless-key write"),
    "RB-T36": ("P1", "GuardianX legacy explanation quarantine"),
    "RB-T37": ("P1", "GuardianX replay scope (GD-2)"),
    **{t: ("P2", "GuardianX ledger reads") for t in ("RB-T24", "RB-T25", "RB-T26", "RB-T27")},
    **{f"RB-T{n}": ("P2", "Genesis network content (GD-6)") for n in range(15, 24)},
    "RB-T18": ("P2", "Genesis — ASSERTION AMENDED (accepts 403 + body-absence)"),
    **{f"RB-T0{n}": ("P3", "tenant-isolation exploit test") for n in range(2, 10)},
    **{t: ("P3", "tenant-isolation exploit test (AW-08 object level)") for t in ("RB-T10", "RB-T11")},
    **{t: ("P3", "register-driven sweep class") for t in ("RB-T01", "RB-T12", "RB-T13", "RB-T14")},
}
PG = "postgresql://postgres:<password>@localhost:5432/postgres"


def author_summary(results_files: list[Path]) -> dict:
    """{(id, db): (matched, total, source)} from the first file that has the id for that db."""
    out: dict = {}
    for path in results_files:
        data = json.loads(path.read_text())
        rows = data["results"] if isinstance(data, dict) else data
        by: dict = {}
        for r in rows:
            by.setdefault((r["id"], r["db"]), []).append(r)
        for key, rs in by.items():
            if key in out:
                continue
            matched = sum(1 for r in rs if r["outcome"] == r["extra"]["expected"].split(" (")[0])
            sha = sorted({r["code_sha"][:7] for r in rs if r["variant"].startswith("after")})
            out[key] = (matched, len(rs), path.as_posix().split("evidence/")[-1], ",".join(sha))
    return out


def assertion_state(it) -> str:
    if it.id == "RB-T18":
        return "**AMENDED** (see diff)"
    if it.id in ("RB-T38", "RB-T39"):
        return "line unchanged; **helper A-1 amended**"
    if it.id == "RB-T28":
        return "unchanged; **set-up changed** (6a661bb)"
    if not it.test:
        return "register-driven"
    return "unchanged (kit AST check)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--results", nargs="+", type=Path, default=[])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    items = [it for it in kit.ITEMS if not it.supplementary]
    assert len(items) == 40, len(items)
    auth = author_summary(args.results)
    order = sorted(items, key=lambda it: (PRIORITY[it.id][0], int(it.id.split("T")[1])))

    lines = [
        "| # | ID | Priority | Finding | Gov | Converted in | Assertion | Author kit (SQLite) | Author kit (PG16) |"
        " Reviewer (name, affiliation) | Independence statement | Evidence link (reviewer's own) | Reviewed SHA |"
        " Date | Disposition |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    detail = []
    for n, it in enumerate(order, 1):
        pr, why = PRIORITY[it.id]

        def a(db):
            v = auth.get((it.id, db))
            return f"{v[0]}/{v[1]} @ {v[3]}" if v else "sweep (see §4)" if not it.test else "—"
        lines.append(
            f"| {n} | {it.id} | {pr} | {it.finding} | {it.gov or '—'} | `{it.converted_in}` | {assertion_state(it)} |"
            f" {a('sqlite')} | {a('postgres')} | UNASSIGNED | — | — | — | — | **PENDING** |")
        if it.test:
            cmd_s = (f"python backend/scripts/p472_03_tripwire_review_kit.py run --ids {it.id} --after {args.baseline} "
                     f"--db sqlite --out $REVIEW/{it.id}/sqlite")
            cmd_p = (f"python backend/scripts/p472_03_tripwire_review_kit.py run --ids {it.id} --after {args.baseline} "
                     f"--db postgres --pg-admin-url \"$PG_ADMIN_URL\" --out $REVIEW/{it.id}/postgres")
            diff = f"python backend/scripts/p472_03_tripwire_review_kit.py diff {it.id} --after {args.baseline}"
            body = (f"- Test: `{it.test_file.removeprefix('backend/')}::{it.test}`\n"
                    f"- Code before fix: `{it.before_code}` · original (marked) tests: `{it.original_tests or '—'}` · "
                    f"converted in: `{it.converted_in}`\n"
                    f"- Expected kit outcomes: before/* **failed**; after/final **passed**; after/original "
                    f"**{kit.expected(it, 'after/original')}**\n"
                    f"- Run: `{cmd_s}`\n- Run: `{cmd_p}`\n- Assertion diff: `{diff}`\n")
        else:
            body = (f"- Register-driven sweep class `{it.sweep_class}`; fixed in `{it.converted_in}` (before `{it.before_code}`).\n"
                    f"- Run: `python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha {args.baseline} --db sqlite "
                    f"--out $REVIEW/{it.id}/sweep-sqlite.json` and the same with `--db postgres --pg-url \"$PG_URL\"`; "
                    f"expect `with_finding: 0` and no route in class {it.sweep_class}. Repeat at `{it.before_code}` to "
                    f"see the class reproduce. Remember the oracle blind spots (handbook §6).\n")
        detail.append(f"### {n}. {it.id} — {it.finding} ({pr}: {why})\n\n{body}"
                      + (f"- Author note: {it.note}\n" if it.note else ""))

    text = HEADER.format(baseline=args.baseline) + "\n".join(lines) + "\n\n" + FOOTER + "\n## Per-tripwire instructions\n\n" \
        + "\n".join(detail)
    for bad in ("ACCEPT-CONVERSION |", "REJECT-CONVERSION |", "ACCEPT-RISK |"):
        assert bad not in "\n".join(lines), "the generator must not write a disposition"
    Path(args.out).write_text(text)
    print(f"wrote {args.out}: 40 tripwires, all PENDING / UNASSIGNED")


HEADER = """# Milestone 9 — Forty-Tripwire Review and Disposition Ledger (v1)

**Issue #191 · PR #181 (DRAFT) · baseline `{baseline}` (application code `829f36a`).** Generated by
`backend/scripts/m9_tripwire_ledger.py` from the review kit's own item table. Supersedes ledger v3 for
Milestone 9 (v3 preserved). **This is the only place a disposition is recorded.**

**State at generation: 40 PENDING · 0 reviewers assigned · 0 dispositions.** "Author kit" columns are
LOCAL-AUTHOR runs (variants matched expectation / variants run, at the after-SHA shown); they are evidence
for the reviewer to reproduce, not a review.

Rules (unchanged from ledger v1–v3, plus Milestone 9 additions):
1. A row is completed only by a reviewer who did not author the change under review, under their own GitHub
   identity, in a commit or PR comment they make. The author fills **no** reviewer column.
2. Allowed dispositions: **ACCEPT-CONVERSION**, **REJECT-CONVERSION**, **ACCEPT-RISK** (named risk owner with
   authority + expiry), **PENDING**. Green CI is never a disposition.
3. The reviewer records the exact SHA they reviewed and links their own evidence (kit output, notes). The
   SHA must be `{baseline}` or a descendant whose application code is identical (`git diff {baseline} <sha>
   -- backend/app` empty); otherwise re-run.
4. Rows are never edited afterwards; a changed disposition is a new row appended below the table.
5. RB-T38/RB-T39 require a separate judgement of amendment A-1 (handbook §5) before ACCEPT-CONVERSION.
   RB-T38…T40 may be accepted only together with the PA-1 decision that ratifies (or replaces) the floor.
   RB-T28 may never be cited as write authorization.

Priority: **P1** privileged authentication, GuardianX ownership, cross-tenant writes, explanation disclosure;
**P2** GuardianX ledger reads and Genesis; **P3** remaining tenant-isolation tripwires.

"""

FOOTER = """**Totals: 40 PENDING · 0 ACCEPT-CONVERSION · 0 REJECT-CONVERSION · 0 ACCEPT-RISK · 0 reviewers.**

Appended dispositions (reviewer-authored rows only; none exist):

| ID | Reviewer | Reviewed SHA | Evidence | Date | Disposition | Risk owner + expiry (ACCEPT-RISK) |
|---|---|---|---|---|---|---|
"""


if __name__ == "__main__":
    main()
