# P472-03 — Batch 5 Evidence Freeze (B5.0)

**Issue #187** · **PR #181 (DRAFT)** · Baseline `7cead8a462092487cc3847807ebd869942afb839`
Disposition at baseline: **P472-03 OPEN · release HOLD / NO-GO.** Batch 4 is not repeated here.

## Repository state
| Check | Result |
|---|---|
| `HEAD` | `7cead8a` = `origin/engineering/render-local-inference-p47` |
| Working tree | clean (no modified or untracked files) |
| Code under test | identical to `c826fcc` (`d62dddc`, `7cead8a` are documentation-only) |

## Sweep re-run on the baseline
`python scripts/tenant_isolation_matrix.py --sweep sqlite --workdir <fresh dir>` → **1,912 routes, 1 with a
finding** (`GET /api/genesis-ai/manufacturer-updates`: AW-04), `unstable: {}`; identical to the committed
`tests/p472_03_findings_register.json`. (A first attempt with the default `--workdir /tmp/p47203-sweep`
failed on a `UNIQUE constraint failed: user_role_assignments.username` from stale shard databases left by an
earlier run — an environment artefact, not a finding; a fresh work directory is required.)

## Final Batch 4 counts (carried forward, tied to SHAs)
| Run | SHA | Result |
|---|---|---|
| CI SQLite, job `135840665336` | `d62dddc` | 9111 passed, 3 skipped, 1 xfailed, 0 failed |
| CI PostgreSQL 16, job `135840665397` | `d62dddc` | success; pytest summary not retrievable from the log API |
| Local PostgreSQL 16.15 | `d62dddc` | 9112 passed, 2 skipped, 1 xfailed, 0 failed |
| CI on `7cead8a` | `7cead8a` | all check suites completed, none failed (docs-only commit) |

## Tripwire register (`p472-03-security-tripwire-disposition-v1.md`)
RB-T01 (strict xfail `test_no_route_exhibits[AW-04]`) still fails; RB-T02…RB-T14 are author conversions.
**No disposition is recorded for any of the 14.** All remain release blockers.

## Gates G1–G15 at baseline
G2, G9, G11 not passing; G1, G3–G8, G13–G15 pending; G12 blocked; G10 pass (CI security/lint/quality).
No gate is closed.

## Reviewer facts (not assignments)
* Repository collaborators (GitHub API): **one** — `johnnychris77` (role `admin`), the program owner who
  directs this work.
* Reviews on PR #181: **none**.
* Consequently **no qualified non-author reviewer can be identified from the repository**. No reviewer
  identity is invented; every routing slot stays **UNASSIGNED — HUMAN ACTION REQUIRED**. Whether the program
  owner counts as independent of agent-authored commits is itself a decision for the release authority.
