# P472-03 Batch 7 (B7.2) — PostgreSQL 16 CI Failure 135978365382: Investigation Report (v1)

**Issue #189 · PR #181 (DRAFT).** Conclusion: **ROOT CAUSE UNKNOWN — open risk R-CI-PG-INTERMITTENT.** Later
green jobs on equivalent code do **not** close it.

## 1. The failure

| | |
|---|---|
| Job | `Backend tests (PostgreSQL 16)`, run `44642957981`, job `135978365382` |
| Commit | `2976b4e` (application code identical to `e81b51d`, `33a1a47`, `c6ba66c`) |
| Runner | `ubuntu-latest`, service image `postgres:16` (16.16 per earlier job logs) |
| Steps | Alembic `upgrade head` / `downgrade -1` / `upgrade head` on `lumenai_test`: **success**; `Run full suite on PostgreSQL`: **failure** |
| Check-run output | empty (no title, summary, text) |
| Job-log tail via API | ≈5,000 lines of PostgreSQL service-container output (`Stop containers` step), including a `FATAL: database "lumenai" does not exist` line every 5 s |
| Full job log | `logs_url` redirects to `productionresultssa19.blob.core.windows.net`; that host is blocked by this environment's network policy. The repository's own cloud environment ("lumen-AI (Render verification)") cannot be edited or switched to from this session, so no network change was made |
| Artifacts | none for the backend jobs (only `dependency-audit-reports`, `gitleaks-results.sarif`) |

**The failing test(s) could not be identified.** Nothing below is a root cause.

## 2. Correlation (what is known)

| Factor | Observation |
|---|---|
| Same application code, CI PG16 | `e81b51d` job `135983149197` success; `33a1a47` job `135988689883` success; `c6ba66c` run `44652755666` success |
| Same code, CI SQLite | `2976b4e` job `135978365627`: 9223 passed, 3 skipped (same run as the PG failure) |
| Earlier PG16 CI failures | `3f479d9`, `c63d398`, `bc0cb94`: failing tests never observed either; cause **inferred** to be the census pin because the local PG16 run on `c63d398` failed only on it |
| Health-check noise | `pg_isready -U lumenai` connects to database `lumenai`, which does not exist → one FATAL line per 5 s. It does not fail the job, but it fills the retrievable log tail and hides pytest's output |
| Parallelism | none (single pytest process per job); the SQLite and PG jobs run on separate runners |
| Test ordering | deterministic (no randomisation plugin) |
| Resource limits | standard hosted runner; no memory/timeout message is visible in the retrievable tail; the job ran 39 min (00:05–00:45), comparable to passing PG jobs (`33a1a47`: 23 min suite) |
| Timing | the job started at 00:05 UTC, shortly after midnight; earlier failing PG jobs also spanned midnight (attributed to the census pin). Date-boundary sensitivity is a **hypothesis only** |

## 3. Reproduction attempts (isolated)

| Attempt | Environment | Result |
|---|---|---|
| CI-faithful: Alembic up/down/up on a **fresh** DB, then the full suite on the **same** DB (as the CI job does) | isolated git worktree at `2976b4e`, PostgreSQL 16.15, Python 3.11.18, `-rfEsxX --junitxml` | **9224 passed, 2 skipped, 0 failed, 0 xfailed** (33 m 03 s) — not reproduced. Script, log, JUnit, Alembic log: `evidence/p472-03-batch7/b72-ci-repro/` |
| Fresh DB without the Alembic pre-step | isolated worktree at `e81b51d` | 9224 passed, 2 skipped (Batch 6) |
| SQLite, alone | `e81b51d` | 9223 passed, 3 skipped (Batch 6) |
| SQLite **concurrently** with a PG run in the same `backend/` directory | `e81b51d` | 78 failed / 5 errors — **invalid run** (cross-run interference through shared working-directory state). Shows the suite is sensitive to shared state; it is **not** an explanation of the CI failure (CI jobs run on separate runners) |

Differences that remain between CI and the reproductions: PostgreSQL 16.16 (CI image) vs 16.15 (local); runner
CPU/IO; wall-clock date and time; network-dependent tests (none known); service health-check traffic.

## 4. Candidate classes for a reviewer (unconfirmed)

1. a time- or date-sensitive test (failure near 00:00–00:45 UTC);
2. a PostgreSQL-only test with a timing or concurrency element (e.g. the concurrent-withdrawal tests from SEC-171-02);
3. a PostgreSQL minor-version difference (16.16 vs 16.15);
4. infrastructure (runner/service) failure surfacing as a test failure.

## 5. Action taken to make the next failure diagnosable (`bd7af7c`)

* Both backend jobs run pytest with `-rfEsxX` (every failure, error, skip, xfail, xpass named) and
  `--junitxml`, `tee` the full log, and upload `test-results/` as an artifact on **every** run
  (`if: always()`, 14 days).
* A failure step writes failing test names as annotations and to the job summary
  (`.github/scripts/junit_failure_summary.py`).
* The PG health check names the existing database (`pg_isready -U lumenai -d lumenai_test`).
* Privacy/secrets review: test data is synthetic (no PHI); JUnit has no captured output (`junit_logging`
  default `no`); the jobs use no secrets; retention 14 days.

## 6. What an authorized operator should do (not possible from this session)

1. Open job `135978365382` in the GitHub UI (or download its log via an account allowed to reach the log host)
   and search for `FAILED`, `ERROR`, `short test summary`. Logs are kept for the repository's retention period
   (90 days by default), so do this before it expires.
2. Attach the failing test names to this report (new version), then re-run that test in a loop on PG16.16.
3. Until then: **R-CI-PG-INTERMITTENT stays OPEN** and the PG16 CI gate is "green on later runs, one
   unexplained failure", not "passing".
