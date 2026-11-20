# P472-03 Batch 7 (B7.2) — PostgreSQL 16 CI Failure 135978365382: Investigation Report (v2)

**Issue #189 · PR #181 (DRAFT).** Supersedes v1 (preserved; v1 concluded "root cause unknown" because the job
log could not be read from this session at that point).

**Conclusion (author-generated, LOCAL-AUTHOR + CI evidence; not independently verified):** the failure was a
**test-oracle defect**, not a tenant-authorization defect. The nightly intelligence job
(`register_intelligence_scheduler`, cron 00:30 UTC) ran on an APScheduler thread during one case of the
route-wide harness. The harness records **every SQL statement in the process** while a request runs, so it
attributed the job's per-tenant SQL to the request. The route itself returned **403** (the status assertion
passed). A harness guard is in place, two regression tests pin it, and the mechanism was reproduced
deterministically. **R-CI-PG-INTERMITTENT: root cause identified, harness-remediated, review pending — not
closed.** Three application-level residuals are recorded below.

## 1. The failure (from the job log)

| | |
|---|---|
| Job | `Backend tests (PostgreSQL 16)`, run `44642957981`, job `135978365382`, commit `2976b4e` |
| Log source | GitHub MCP `get_job_logs` (the API returned the log content directly; v1's blocked blob host was not needed). Source log sha256 `3346e983…eee1` |
| Result line | `1 failed, 9223 passed, 2 skipped, 1881 warnings in 2496.76s (0:41:36)` |
| Failing test | `tests/test_p472_03_batch2_remediation.py::test_unverified_tenant_requests_are_refused_and_change_nothing[GET /api/pulse/command-center]` |
| Assertion | `two memberships, none selected: SQL bound to b2-alpha-43b3ec56 on ['emerging_risk_signals', 'instrument_quality_signals']` (line 509, the SQL-oracle assertion; the status assertion on the line before it passed) |
| HTTP status of the probe | `403 Forbidden` (captured log, `00:30:00,010`) |
| Concurrent event | captured log of the same test: `00:30:00,000 Running job "register_intelligence_scheduler.<locals>._run_nightly_intelligence (trigger: cron[hour='0', minute='30'] …)"`, `00:30:00,010 … executed successfully` |
| Extract | `evidence/p472-03-batch7/b72-ci-repro/ci-job-135978365382-failure-extract.txt` (1,425 lines plus count line and source hash) |

The job queried exactly the two tables the oracle reported. `run_risk_analysis(db, tid)` reads
`emerging_risk_signals` and `instrument_quality_signals` for each tenant in `tenant_memberships`, and the
harness had created memberships for `b2-alpha-*`.

## 2. Mechanism

1. Earlier tests start the app lifespan (`TestClient(app)`), which creates a `BackgroundScheduler` and a
   `scheduler-leader` thread that starts it (`backend/app/main.py`).
2. On lifespan shutdown, the app sets the stop event and releases the lease. It **never calls
   `_scheduler.shutdown()`**, so the scheduler and its cron jobs stay alive for the rest of the pytest process.
3. The harness listens on `Engine.before_cursor_execute` **process-wide** and checks whether any statement
   captured during the request binds a forbidden tenant.
4. At 00:30:00 UTC the nightly job ran on an executor thread while the "two memberships, none selected" probe
   was being captured. Its `b2-alpha` SQL was attributed to the request.

Why it was intermittent: the job fires once a day, and the window is about 10 ms in the CI run. Only a CI run
whose route-wide harness passes through this case at 00:30 UTC is exposed. The `2976b4e` job started at 00:05
and reached this file at about 00:30.

## 3. Earlier PG16 CI failures, now read from their logs (were "inferred")

| Job | Commit | Result | Failing test |
|---|---|---|---|
| `135967501020` | `3f479d9` | 1 failed, 9220 passed, 2 skipped | `test_the_route_table_is_the_mounted_application` — `{'dependency': 195, 'handler': 715}` (census pin) |
| `135969896426` | `c63d398` | 1 failed, 9223 passed, 2 skipped | same (census pin) |
| `135970191686` | `bc0cb94` | 1 failed, 9223 passed, 2 skipped | same (census pin) |

These three finished at 00:10, 00:25 and 00:26 UTC, before the 00:30 job, so they are unrelated to the
scheduler. Their cause is now **confirmed from CI logs**; v1 and records.json called it inferred. Extract:
`evidence/p472-03-batch7/b72-ci-repro/earlier-pg16-failures-census-pin-extract.txt`.

## 4. Deterministic reproduction (LOCAL-AUTHOR, SQLite)

* Plugin `b72_repro_plugin.py` starts a `BackgroundScheduler` whose job runs tenant-A-bound SQL. It does this
  only for the `GET /api/pulse/command-center` case. `B72_GUARD=off` replaces the guard with a no-op, which is
  the pre-B7.2 harness behaviour.
* Result (`b72_deterministic_repro.txt`):

| Guard | Runs | Failed with the CI assertion text (`two memberships, none selected: SQL bound to b2-alpha-…`) |
|---|---|---|
| off | 5 + 2 | 3 of 5, and 1 of 2 in an earlier pair |
| on | 5 + 2 | 0 of 7 |

  A guard-off pass means the job did not overlap the capture; timing varies between runs.
* The CI-faithful PG16 reproduction from v1 §3 (`2976b4e`, 9224 passed / 2 skipped) did not reproduce the
  failure. That is consistent with this cause: it ran at a different time of day.

## 5. Harness remediation (test code only; no application change)

`backend/tests/test_p472_03_batch2_remediation.py`:

* `_pause_running_schedulers()` finds every live APScheduler `BaseScheduler` (via `gc`) and pauses the running
  ones. It then waits, bounded at 60 s, for job runs already in flight, because pausing stops only new runs.
* The module `caller` fixture pauses schedulers at set-up and resumes them at teardown. `call()` re-pauses them
  before every capture, because the leader loop can resume a scheduler after a lease change.
* **No request SQL is excluded from the oracle.** An earlier idea, filtering by thread name, was rejected:
  TestClient's portal can itself run on a `ThreadPoolExecutor` thread, so that filter could hide request SQL.
* Regression tests:
  * `test_b72_an_unguarded_capture_attributes_a_background_jobs_sql_to_the_request` pins the hazard.
  * `test_b72_the_harness_pauses_running_schedulers_before_capturing` pins the guard.

Verification of the changed file, LOCAL-AUTHOR, on `7cc7bfb` plus this change: **SQLite 1926 passed; PostgreSQL
16.15 1926 passed** (0 failed, 0 skipped, 0 xfailed in either run).

## 6. Residuals (open; not fixed here)

| ID | Residual | Why not fixed in B7.2 |
|---|---|---|
| R-SCHED-SHUTDOWN | App lifespan shutdown never calls `_scheduler.shutdown()`. A process that restarts its lifespan accumulates schedulers. In tests, schedulers persist across the session | Application lifecycle change; needs owner review of leader-election semantics |
| R-NIGHTLY-SILENT | `_run_nightly_intelligence` iterates every tenant in `tenant_memberships` and swallows all exceptions (`except: pass`) with no log or audit. A failing tenant analysis is invisible | Operational/observability decision; no tenant-isolation breach found (the job runs per tenant with its own `tid`) |
| R-ORACLE-SESSION-WIDE | Other tests that use process-wide SQL listeners or global state could be contaminated by any background thread, not only APScheduler jobs | The guard covers schedulers; other background threads were not inventoried |

## 7. Status

R-CI-PG-INTERMITTENT moves from **UNKNOWN ROOT CAUSE** to **root cause identified (author analysis),
harness-remediated, independent review pending**. It is not closed. A reviewer should confirm §1–§4 from the
CI log and the reproduction, and decide the §6 residuals. The CI change from v1 §5 (`bd7af7c`: `-rfEsxX`,
JUnit, artifacts on every run, health-check database) stays in place.
