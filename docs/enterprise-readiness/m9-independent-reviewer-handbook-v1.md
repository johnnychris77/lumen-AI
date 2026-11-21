# Milestone 9 — Independent Reviewer Handbook (v1)

**Issue #191 · PR #181 (DRAFT) · baseline `bed42c86f982efc845130ec65d3b46bdc2d06899` (application code `829f36a`).**
This handbook tells an **independent, non-author reviewer** how to reproduce and judge the 40 P472-03 security
tripwires and the PA-1 remediation from scratch, on fresh SQLite and PostgreSQL 16 databases.

It was written by the change author. **Following it is the review; reading it is not.** Nothing in this
repository is an independent review until a reviewer who meets §0 has run it and recorded the result under
their own identity.

## 0. Who may review, and what independence means

| Requirement | Detail |
|---|---|
| Not an author | Did not write, co-author or direct any commit in `0f2ec58..bed42c8` touching `backend/app`, `backend/tests` or `backend/scripts` (author list: `git log --format='%an %ae' 0f2ec58..bed42c8 \| sort -u`). Commits in this range were produced by an AI coding agent working for the repository owner; **neither the agent nor the owner who directed it is independent.** |
| No conflict | Not in the reporting line of the person whose work is reviewed for PA-1 (governance workflow A1); declares any commercial or personal interest. |
| Appointed | Appointed by the release authority (governance workflow A1). At the time of writing the repository has **one** collaborator (the owner): **no eligible reviewer exists in the repository.** The release authority must appoint one (internal security team, external assessor). |
| Own identity | Records results from their own GitHub account (or a signed report linked from the PR by them). |
| Least privilege | Needs read access to the repository only. **No production access, no production data, no deployed secret.** All data is synthetic and created by the tests. |

## 1. Prerequisites

- Linux or macOS, Python 3.11, `git`, PostgreSQL **16** server you control (local or container), Node 20+ and
  Chromium (only for §7 browser E2E).
- About 4 GB disk. Allow a working day for P1, two for everything.

```bash
git clone https://github.com/johnnychris77/lumen-AI.git && cd lumen-AI   # full history: the kit checks out old SHAs
git checkout --detach bed42c86f982efc845130ec65d3b46bdc2d06899
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-lock.txt
export REVIEW=$HOME/m9-review && mkdir -p "$REVIEW"
# PostgreSQL 16: an admin URL for a server you control; the kit creates and drops one database per test
export PG_ADMIN_URL=postgresql://postgres:<password>@localhost:5432/postgres
export PG_URL=postgresql://postgres:<password>@localhost:5432/m9_sweep   # create this empty DB for sweeps
psql "$PG_ADMIN_URL" -c 'select version()'   # must say PostgreSQL 16.x
```

## 2. Verify you have the frozen evidence

```bash
python backend/scripts/m9_evidence_freeze.py verify docs/enterprise-readiness/evidence/m9/freeze-bed42c8.json
```

Expected: `230 files checked; 0 integrity failures`. The freeze hashes every evidence file, register, ledger,
packet, assertion change log, test file and script **from the git object at `bed42c8`**, plus a digest of all
of `backend/app`. Any integrity failure means you are not reviewing the frozen baseline: stop and report.

Two further checks you should make yourself, because the author computed the freeze:

```bash
git cat-file -p bed42c8 | head -1     # tree id; compare with "tree" in the freeze file
git log --oneline 0f2ec58..bed42c8 | wc -l   # branch history; compare with branch_history_from_main
```

## 3. The 40 tripwires — run the review kit

The kit (`backend/scripts/p472_03_tripwire_review_kit.py`) runs each tripwire's test in throw-away git
worktrees, in up to four variants, on a fresh database each time:

| Variant | Code | Tests | What it proves |
|---|---|---|---|
| before/final | before the fix | final tests | the final test detects the defect |
| before/original | before the fix | tests as committed when the tripwire was still marked | the original tripwire failed |
| after/final | `bed42c8` | final tests | the fix holds |
| after/original | `bed42c8` | original tests | the fix satisfies the **original** assertion (fails by design only for RB-T18, RB-T28, RB-T38, RB-T39; see the ledger) |

**Per tripwire**, in priority order (the exact commands for each of the 40 are in
`m9-forty-tripwire-review-and-disposition-ledger-v1.md`):

```bash
python backend/scripts/p472_03_tripwire_review_kit.py run --ids RB-T32 --after bed42c8 --db sqlite   --out $REVIEW/RB-T32/sqlite
python backend/scripts/p472_03_tripwire_review_kit.py run --ids RB-T32 --after bed42c8 --db postgres --pg-admin-url "$PG_ADMIN_URL" --out $REVIEW/RB-T32/postgres
python backend/scripts/p472_03_tripwire_review_kit.py diff RB-T32 --after bed42c8          # original vs final test body
```

**All test-backed tripwires at once** (several hours):

```bash
python backend/scripts/p472_03_tripwire_review_kit.py run --after bed42c8 --db sqlite   --out $REVIEW/all/sqlite
python backend/scripts/p472_03_tripwire_review_kit.py run --after bed42c8 --db postgres --pg-admin-url "$PG_ADMIN_URL" --out $REVIEW/all/postgres
python backend/scripts/p472_03_tripwire_review_kit.py report $REVIEW/all/*/kit-results-*.json --out $REVIEW/packets.md
```

Compare your `kit-results-*.json` with the author's (`evidence/m9/rehearsal-bed42c8/`,
`evidence/p472-03-pa1-remediation/kit/`, `evidence/p472-03-batch8/kit/`). **A match is not enough to accept a
conversion** — also do §3.1.

### 3.1 What to examine for every tripwire (the kit cannot do this for you)

1. **The authorization predicate.** Read the code the fix added (`git show <converted_in> -- backend/app`).
   Does it check the verified tenant / owner, or only something the attacker controls?
2. **Negative and positive controls.** The test must refuse the foreign tenant *and* still serve the owner.
   The kit's `controls` section lists the same-tenant controls per test file.
3. **Spoofing.** Try the request with each tenant channel the code reads: `X-Tenant-Id`,
   `X-LumenAI-Tenant-Id`, query, path and body `tenant_id`, conflicting pairs.
4. **Persistence.** For writes, confirm a refused request persists **nothing** (count rows before/after).
5. **Audit attribution.** Writes that succeed must create an audit event under the verified tenant and actor,
   not a header value.
6. **Replay.** Replayed audit chains must stay inside the caller's tenant (GD-2).
7. **Assertion changes.** For RB-T18, RB-T28 (set-up), RB-T38/RB-T39 (helper A-1) read the change logs and
   decide whether the amendment weakens the original intent.

### 3.2 Priority order and what each group is about

| Priority | Tripwires | Focus |
|---|---|---|
| **P1** | RB-T38, RB-T39, RB-T40 | PA-1 production gates (§5 for A-1) |
| **P1** | RB-T28 | **Read-side coverage only.** It must never be cited as proof of write authorization; writes are RB-T29…T31, T33 |
| **P1** | RB-T29, RB-T30, RB-T31, RB-T33 | GuardianX cross-tenant writes: foreign owned source, ownerless key in use, explanation under a foreign source, digital-twin tenant claim |
| **P1** | RB-T32, RB-T34…RB-T37 | GuardianX explanations: disclosure (list, by id, replay, audit package), foreign override, key injection, legacy quarantine, replay scope |
| P2 | RB-T24…RB-T27 | GuardianX ledger reads |
| P2 | RB-T15…RB-T23 | Genesis network content; RB-T18 assertion amended |
| P3 | RB-T02…RB-T11 | tenant-isolation exploit tests (AW-03/04/06M/06N/08) |
| P3 | RB-T01, RB-T12, RB-T13, RB-T14 | register-driven sweep classes (§4) |

GuardianX background for the reviewer: ownership is the single real tenant on a source's hash-chained audit
trail (`audit_trail_owner`); rows with no provable owner are quarantined (served to no tenant); fresh ownerless
keys are first-writer (open risk R-GX-OWNERLESS-KEYS, not a tripwire). Design:
`p472-03-b54-guardianx-ledger-adr-v1.md`, `p472-03-batch8-guardianx-explanation-ownership-v1.md`.

## 4. Register-driven tripwires (RB-T01, RB-T12…RB-T14) and the route sweep

```bash
python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha bed42c8 --db sqlite   --out $REVIEW/sweep-sqlite.json
python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha bed42c8 --db postgres --pg-url "$PG_URL" --out $REVIEW/sweep-pg.json
# then the "before" code for a class, e.g. AW-06N:
python backend/scripts/p472_03_tripwire_review_kit.py sweep --sha 4fdac4c --db sqlite --out $REVIEW/sweep-before.json
```

Expected at `bed42c8` (author runs, `evidence/p472-03-pa1-remediation/final-829f36a/`): 1,913 mounted routes,
`with_finding: 0`, `foreign_write_routes: 0`; role-gated 164; partly exercised 735 (SQLite) / 729 (PG16);
unscoped SQL leads 353. The before-sweep should show the class reproduce.

## 5. Amendment A-1 — review it separately

**What changed.** RB-T38 and RB-T39 share a probe helper. Originally the probe ran `import app.main` in a
child process and asserted it exited 0. After the fix, those production configurations **refuse to start**,
so the original probe cannot run. The amended probe records the refusal and evaluates the *same three
expressions* at layer level: `app.deps` imported directly, `enterprise_auth._AUTH_ENV`, and the demo router
on a minimal app over the same database. Assertion lines are unchanged. Full text:
`p472-03-pa1-remediation-assertion-change-log-v1.md` (A-1…A-4).

**The question.** Does the amended helper still detect a broken gate, or does it pass merely because startup
refuses?

**Reproduce the author's mutation check, then extend it:**

```bash
python backend/scripts/m9_a1_mutation_check.py --sha bed42c8 --out $REVIEW/a1-sqlite.json
python backend/scripts/m9_a1_mutation_check.py --sha bed42c8 --pg-admin-url "$PG_ADMIN_URL" --out $REVIEW/a1-pg.json
git diff 6b2a8d6 829f36a -- backend/tests/test_p472_03_batch8_pa1_env_gates.py
```

| Mutation (one gate re-opened; all else intact) | Expected | Author result (SQLite / PG16) |
|---|---|---|
| M0 control | all pass | match / match |
| M1 `is_production()` always False (startup still refuses) | RB-T38, T39, T40 **fail** | match / match |
| M2 `deps._DEV_AUTH_ACTIVE` ignores production | RB-T38 **fails** | match / match |
| M3 demo router production check removed | RB-T39 **fails** | match / match |
| M4 JWT-shape `_AUTH_ENV` never production | RB-T40 **fails** | match / match |
| M5 startup refusal removed (gates intact) | RB-T38…T40 **pass**; both startup tests and the unset-`AUTH_MODE` control **fail** | match / match |

Evidence: `evidence/m9/a1-mutation/`. **Disclosure:** the author's first M5 expectation omitted the
unset-`AUTH_MODE` control; the run showed it also fails (correctly — it is part of the same refusal). The
expectation was corrected and re-run; the first output is preserved as
`a1-mutation-sqlite-run1-expectation-incomplete.json`.

Things the mutation check does **not** prove, for you to judge: whether the layer probe matches what a real
production worker would load (see PA-1 packet §2.6); whether other dev-token readers exist beyond those the
layer tests cover (`grep -rn "dev-token\|DEMO_MODE\|_DEV_ROLE_MAP" backend/app`).

## 6. Known blind spots — probe them independently

The author's sweep oracle sees only SQL issued through the application engine that binds the foreign tenant.
It does **not** see, and nothing in this package claims to cover:

- **164 role-gated routes** beyond the sweep's identities;
- **~729–735 partly exercised routes**;
- **353 unscoped SQL leads**;
- response-body leakage without SQL binding;
- IDOR by guessable ids;
- untyped `payload: dict` bodies;
- non-SQL stores.

`p472-03-application-wide-authorization-matrix.md` (and its CSV) lists them per route. A reviewer should
sample from each category (suggested: 20 role-gated, 30 partly exercised, 30 leads) with hand-written
requests. Record any new finding as a new row in the risk register; do not edit the findings register by hand.

## 7. Reproduce the release evidence (optional but recommended)

| Check | Command (from `backend/`) | Author result at `829f36a`/`bed42c8` |
|---|---|---|
| Full suite, fresh SQLite | `rm -f test.db && python -m pytest tests -q -rfEsxX` | 9317 passed, 3 skipped, 0 xfailed, 0 failed |
| Full suite, PG16 + Alembic up/down/up | `bash ../docs/enterprise-readiness/evidence/p472-03-batch7/b72-ci-repro/ci_pg_repro.sh <worktree> <db> <outdir>` (edit its `DATABASE_URL` for your server) | Alembic exit 0; 9318 passed, 2 skipped, 0 failed |
| PA-1 reproduction | `python scripts/p472_03_pa1_remediation_repro.py --db sqlite` and `--db postgres --pg-admin-url ...`, at `c2014ff` and at `bed42c8` | before: findings reproduce; after: closed |
| Browser E2E | header of `frontend/tests/e2e/tenantContext.e2e.mjs`; **start the backend with `CORS_ORIGINS=http://127.0.0.1:5173`** | 6/6 twice |
| CI | GitHub Actions on `bed42c8`, run `44840371217` | SQLite 9317/3/0/0 (job 136646947604); PG16 9318/2/0/0 (job 136646947540) |

## 8. Recording a disposition

1. In `m9-forty-tripwire-review-and-disposition-ledger-v1.md`, **append** a row below the table (never edit
   the generated rows): ID, your name and affiliation, reviewed SHA, link to your evidence, date, disposition.
2. Commit it from your own account, or post it as a PR #181 comment and link the comment.
3. Dispositions: **ACCEPT-CONVERSION** (fix verified, conversion sound), **REJECT-CONVERSION** (with
   reasons), **ACCEPT-RISK** (needs a named risk owner with authority and an expiry date), **PENDING**.
4. RB-T38…T40: ACCEPT-CONVERSION only after §5 and only alongside a signed PA-1 decision (governance matrix).
5. Write your independence statement once (§0) and reference it in each row.

## 9. What the author has and has not done

| Done by the author (LOCAL-AUTHOR / CI) | Not done — needs you |
|---|---|
| Evidence freeze at `bed42c8` (230 files, verify passes) | Independent verification of the freeze |
| Kit rehearsal at `bed42c8` for RB-T24…T37 on SQLite and PG16 | A run by someone other than the author |
| A-1 mutation check on SQLite and PG16 | Judgement of A-1 |
| CI and local full suites, sweeps, E2E | Any disposition |
| This handbook | Probing the blind spots (§6) |
