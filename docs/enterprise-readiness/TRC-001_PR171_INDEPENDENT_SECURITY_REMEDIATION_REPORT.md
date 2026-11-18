# TRC-001 / PR #171 — Security Remediation Report

| | |
|---|---|
| **Recommendation** | **NO-GO** for merging PR #171 at the reviewed commit |
| **Reviewed commit** | `117e083841d987cddf7c9e46856d6584e48fa738` (head of PR #171, branch `trc-001-first-real-ingestion-20261113`) |
| **Pull request** | https://github.com/johnnychris77/lumen-AI/pull/171 (base `feat/stage6d-real-instrument-pilot-20261113`) |
| **Findings assessed** | SEC-171-01, SEC-171-02, SEC-171-03 |
| **Existing fix stack compared** | PRs #172, #173, #174 (+#175), #176 — tip `fdaee8e2135fea7d2a5581fbe7246014fe2b9219` |
| **Remediation branch** | `security/sec-171-pr171-adversarial-remediation` (stacked on `fdaee8e`) |
| **Failing-tests commit** | `8201189` (tests only, no implementation change) |
| **Remediation commit** | `c3daa38f9d8ad713fb3a4e4ebc3d9567a420e1c9` |
| **Report date** | 2026-11-18 |

## 0. Independence statement

The file name was specified by the requester. **This is not an independent review.** It
is an AI-assisted assessment produced in the same engineering session, by the same
author lineage, that wrote most of the code in PR #171 and in the fix stack above it.
It can reproduce or disprove a finding with evidence. It cannot supply a non-author
security sign-off, and it does not close any finding. Every "resolved" below means
"the failing test now passes", not "accepted by a reviewer".

No governance record, approval, signature or ingestion evidence was fabricated. No
TRC-001 operator photograph was read, loaded into a database, or committed: every
image in the tests is generated in-process. Ground truth stays `unknown` and research
images stay training-ineligible throughout.

---

## 1. Decision

**NO-GO — do not merge PR #171 at `117e083`.**

All three findings reproduce at the reviewed commit:

| Finding | Result at `117e083` | Severity |
|---|---|---|
| SEC-171-01 cross-purpose deduplication | **Confirmed** (10 exploit tests fail) | High |
| SEC-171-02 concurrent withdrawal | **Confirmed** (3 of 3 PostgreSQL races fail, 8 of 8 runs) | High |
| SEC-171-03 shared migration | **Partly confirmed** (3 sub-issues confirmed, 3 disproved) | Medium |

The fixes do not exist in PR #171. They live in commits stacked above it, so PR #171
cannot be authorized on its own at this SHA. A GO would require all of the following:

1. PR #171 is merged only together with the fix stack (PRs #172, #173, #174/#175, #176)
   **and** the remediation in this branch — never alone.
2. A non-author security reviewer re-reviews the combined head and records a decision.
3. The governance gates already recorded as open remain satisfied or are closed by the
   people who own them. PRs #176–#180 are frozen under HOLD, so that path is itself
   not currently authorized.

CI on PR #171 at `117e083` is fully green (7 of 7 checks, run `43667566862`). The three
findings exist underneath a green pipeline, so passing CI is not evidence of safety here.

---

## 2. Scope and method

- **Read** `retain_image()`, `retain_reference_image()`, every caller of both, the
  TRC-001 intake runner, the research API, the migration, the production schema path
  and the generic ML image routes — at `117e083` and at the fix-stack tip `fdaee8e`.
- **Wrote failing tests first** (commit `8201189`): 41 adversarial tests in three files,
  run unchanged against both commits before any implementation was touched.
- **Remediated** only what was still failing at `fdaee8e`, in a new branch stacked on it.
- **Verified** with Ruff, the full backend suite on SQLite and PostgreSQL 16, the real
  Alembic chain, and CI.

Two worktrees were used so each commit was tested as it stands, not as a diff.

---

## 3. Results at a glance

Counts are failing tests out of the 41 written before remediation, on PostgreSQL 16.

| Test file | Tests | `117e083` (PR #171) | `fdaee8e` (existing stack) | Remediation head |
|---|---|---|---|---|
| `test_sec171_01_cross_purpose_dedup.py` | 20 | 11 fail | 14 fail | 0 fail |
| `test_sec171_02_pg_concurrent_withdrawal.py` | 4 | 3 fail | 0 fail | 0 fail |
| `test_sec171_03_migration_and_isolation.py` | 17 | 11 fail | 11 fail | 0 fail |
| **Total** | **41** | **25 fail** | **25 fail** | **0 fail** |

Two further guard tests were added with the fix, giving 43 in the final files.

The existing stack fixed SEC-171-02 completely. It did **not** fix SEC-171-01: it fixed
some paths and removed a guard the reviewed commit had, so more tests fail there than
at `117e083`. It fixed part of SEC-171-03 and introduced one new defect in it.

---

## 4. SEC-171-01 — cross-purpose deduplication

### 4.1 Root cause at `117e083`

`retain_image()` and `retain_reference_image()` deduplicate on `(tenant_id, sha256)`
alone:

- `backend/app/services/image_retention_service.py:115-122` (`retain_image`)
- `backend/app/services/image_retention_service.py:194-201` (`retain_reference_image`)

Whoever submits identical bytes is handed back whatever row already holds them,
whatever authorization that row was retained under. Eight callers share this store:
inspection upload, capture device, dataset ingestion, Catalyst copilot, the generic ML
upload, baseline reference registration, research acquisition and the TRC-001 intake.

The intake runner guards one direction only. For the owner-attested basis it refuses a
mismatched row (`backend/research/lens_vision/trc001_intake.py:309-325`). For the
institutional basis it calls `retain_image(..., commit=True)` with no check at all
(`trc001_intake.py:303-307`).

### 4.2 What was demonstrated at `117e083`

| # | Demonstrated behaviour | Test |
|---|---|---|
| 1 | An inspection upload of identical bytes is handed the research owner's row | `test_inspection_retention_never_returns_a_research_row` |
| 2 | A baseline reference upload is bound to the research owner's row | `test_baseline_reference_never_returns_a_research_row` |
| 3 | The owner's withdrawal then deletes the image that baseline reference depends on | `test_owner_withdrawal_does_not_delete_another_purposes_copy` |
| 4 | A generic ML upload returns the research image's id, name and hash to a non-owner | `test_generic_ml_upload_of_identical_bytes_does_not_disclose_a_research_image` |
| 5 | A generic ML upload can create a row carrying the research-intake marker (`source` is a query parameter, `ml_images.py:77`) | `test_generic_ml_upload_cannot_mint_a_research_source_row` |
| 6 | The retention service accepts that marker from any caller | `test_retention_service_refuses_an_unscoped_research_source_row` |
| 7 | Research images are listed, and their bytes served, by the generic ML routes (`ml_images.py:156`, `:192`) | `test_generic_ml_routes_cannot_list_or_read_research_images` |
| 8 | A non-owner can label a research image, moving it out of `unlabeled` (`ml_images.py:224`, `:251`) | `test_generic_ml_labelling_cannot_modify_a_research_image` |
| 9, 10 | An institutional intake reports an owner-attested image as its own, in a different dataset and in the same one | `test_institutional_intake_never_claims_an_owner_attested_image[False]`, `[True]` |

An eleventh test, `test_institutional_images_survive_another_owners_withdrawal`, also
fails at `117e083`, but at its precondition: the owner's intake is refused because an
institutional row with the same bytes exists. That is fail-closed interference, not
deletion, and it is not counted as a demonstrated exploit.

Items 7 and 8 matter beyond disclosure. The generic ML routes feed the labelling queue
and the gold-label training export, so a research image that must stay
training-ineligible with unknown ground truth could be labelled and promoted. Those
routes also take the tenant from a request header (`enterprise_auth.py:59-64`), a
pre-existing weakness outside PR #171 that widens who can reach them.

Tests that pass at `117e083`, showing where it is already safe: a research intake does
not claim a pre-existing inspection, baseline or dataset-ingestion image (it refuses),
a withdrawal does not delete such an image, an owner-attested intake does not claim an
institutional image, and a second owner cannot reassign the first owner's image.

### 4.3 What the existing stack changed

Improved: research images are no longer listed, served or exported through the generic
ML routes, are refused as baseline references, and are excluded by the dataset builder.

Regressed: commit `793ed2f` (SEC-171-04) replaced the runner's conflict check with a
per-owner authorization attached to whatever row deduplication returns. At `fdaee8e` a
research intake therefore *does* reuse a pre-existing inspection, baseline or
dataset-ingestion image and attaches a research authorization to it, and it reuses an
institutional image the same way. Five tests that pass at `117e083` fail at `fdaee8e`.

Unchanged: items 1–6, 8, 9 and 10 above still reproduce at `fdaee8e`.

### 4.4 Remediation

| Change | Location |
|---|---|
| Deduplication is scoped to the caller's authorization scope. A research caller only matches research rows of the same research dataset; every other caller only matches non-research rows. | `image_retention_service.py:38-54` (`_dedup_candidates`), used at `:157` and `:239` |
| The research marker and a research dataset scope must be supplied together, or `RetentionScopeError` is raised. A generic caller can neither mint a research row nor be handed one. | `image_retention_service.py:128`, `:143-147` |
| New research rows are stamped with their dataset at creation. | `image_retention_service.py:188` |
| The runner passes the dataset scope, and refuses an image already retained in the same dataset under the other basis. | `trc001_intake.py:112-135`, `:339-352`, `:378-382` |
| The generic ML upload rejects the reserved research source with 422. | `ml_images.py:114-120` |
| Labelling, reading labels and adjudication treat a research image as not found. | `ml_images.py:60-74`, `:275`, `:333`, `:376` |

No schema change was needed. Identical bytes can now exist as separate rows, one per
authorization scope, which is what lets a withdrawal delete the research copy and
leave a baseline copy alone.

---

## 5. SEC-171-02 — concurrent withdrawal

### 5.1 Root cause at `117e083`

The owner attestation is checked once, before the kit is read
(`trc001_intake.py:226`), and never again. Neither the check nor the withdrawal takes
a row lock: there is no `with_for_update` anywhere in the authorization path, and the
withdrawal reads approved attestations with a plain query
(`trc001_research.py:220-230`). Each image is then committed in its own transaction
(`trc001_intake.py:330`). A withdrawal can commit between the check and either write.

### 5.2 Test design

`test_sec171_02_pg_concurrent_withdrawal.py` drives the race without timing
assumptions:

1. The intake runs on connection A and is paused at an exact point that is always
   after authorization has passed.
2. The withdrawal starts on connection B.
3. Connection C reads `pg_blocking_pids` until the withdrawal has either finished or
   is blocked by A's backend. Only then is the intake released.
4. After both finish, a new connection checks with raw SQL that the attestation is
   withdrawn and that no row scoped to that owner and dataset holds bytes.

Each session is pinned to one connection, so the backend pid observed in the lock
graph is the pid running every statement.

### 5.3 Results

| Test | `117e083` | `fdaee8e` |
|---|---|---|
| Withdrawal before any image is persisted | **Fail** — 2 rows hold bytes after the withdrawal committed | Pass |
| Withdrawal between the two images | **Fail** — 1 row holds bytes after the withdrawal committed | Pass |
| The intake holds a lock on its attestation while writing | **Fail** — lock was free | Pass |
| Sequential ingest, withdraw, verify absence (all databases) | Pass | Pass |

Both outcomes were identical in 8 of 8 consecutive runs at each commit.

### 5.4 Remediation

Already resolved by the existing stack; this branch changes nothing here. The fix is
in PR #172 (commits `7bbc687`…`15fe228`): the attestation row is locked `FOR UPDATE`
when resolved (`scientific_authorization.py:310`), re-resolved under that lock
immediately before each image is written (`trc001_intake.py:333`), and locked by the
withdrawal (`trc001_research.py:255`). The stack's own two-session tests cover the same
property; the tests added here reach it by a different hook point and a different
observation, and agree.

---

## 6. SEC-171-03 — shared migration and deployment isolation

Production does not run Alembic. Render builds `backend/Dockerfile.api`
(`render.yaml:6`), whose command is `uvicorn app.main:app` (`backend/Dockerfile.api:32`),
and schema changes arrive through `create_all` plus the startup
column back-fill (`backend/app/main.py:147`, `:164`;
`backend/app/db/column_migrator.py:68`). The back-fill adds columns **nullable**, with
a default, and creates no index. That is the context for (c) below.

| | Sub-issue | `117e083` | `fdaee8e` | Remediation head |
|---|---|---|---|---|
| a | Upgrade preserves historical images and infers no ownership | **Disproved** — safe | Safe | Safe |
| b | Downgrade drops ownership provenance and leaves the image bytes | **Confirmed** (`e8b2c6d49f10…py:42-52`) | Fixed by `6fef865` | Fixed |
| c | A database back-filled by application startup cannot be converged by Alembic | **Confirmed** — columns stay nullable | **Worse** — the upgrade fails outright | Fixed |
| d | Research endpoints are live on any deployment | **Confirmed** (`main.py:855-856`, `trc001_research.py:57`) | Still present | Fixed |
| e | Downgrade drops withdrawn-authorization history | Not applicable (table absent) | **Present** | Fixed |
| f | Importing the application loads the research stack | **Disproved** — it does not | Safe | Safe |
| g | Round trip with no research rows is lossless | **Disproved** — safe | Safe | Safe |

Notes on the confirmed items:

- **(b)** At `117e083` a downgrade removes `research_dataset_id`,
  `research_owner_subject` and `research_attestation_id` while the row and its bytes
  remain. No owner withdrawal can find those bytes afterwards.
- **(c)** At `fdaee8e` the hardened migration verifies `NOT NULL` as a post-condition
  (`migration_guards.py:41`, `verify_retained_provenance_columns`). On a database whose
  columns were added by the startup back-fill that check raises, so `alembic upgrade`
  can never pass revision `e8b2c6d49f10` there. The hardening introduced this.
- **(d)** Any verified tenant member on any deployment could record a self-approved
  owner attestation, withdraw it, or trigger an intake.

**Database compatibility.** The Alembic chain is PostgreSQL-only: an earlier, unrelated
revision issues `ALTER COLUMN … TYPE`, which SQLite rejects. That predates PR #171.
SQLite databases get their schema from `create_all` and the back-fill, and that path is
covered by `test_startup_backfill_preserves_historical_images_on_any_database`.

### 6.1 Remediation

| Change | Location |
|---|---|
| The upgrade blanks NULLs in back-filled columns (inferring no ownership) and enforces `NOT NULL`, so both schema paths end in the same shape. | `alembic/versions/e8b2c6d49f10_trc001_research_image_provenance.py:55-64`; `migration_guards.py:63-73` |
| The association downgrade guard refuses when any authorization row exists, active or withdrawn. | `migration_guards.py:109-128` |
| A router-level gate, evaluated before authentication, answers 404 on every research endpoint unless `TRC001_RESEARCH_API_ENABLED` is explicitly affirmative. | `trc001_research.py:57-79` |
| The gate is documented, and the flag is deliberately absent from `render.yaml`. | `docs/model-development/trc-001/TRC-001_RESEARCH_API.md` |

---

## 7. Existing tests that were changed

Three previously passing tests encoded behaviour this assessment judges unsafe. Each
was changed deliberately; none was weakened to obtain a green result.

| Test | Asserted before | Asserts now | Why |
|---|---|---|---|
| `test_trc001_research_api.py::test_same_tenant_two_owners_share_bytes_without_reassignment` | An owner's intake attaches an authorization to a row belonging to a **different dataset** | The foreign dataset's row is untouched and carries no authorization from this owner; the owner's own rows are deleted on withdrawal | A dataset is an authorization scope |
| `test_sec17104_image_authorization.py::test_same_owner_different_datasets_distinct_authorizations` | One row carries authorizations for two datasets | Each dataset has its own rows and its own authorization | Same reason |
| `test_trc001_provenance_migration.py::test_association_downgrade_guard` | Withdrawn-only rows permit a downgrade | Withdrawn rows block it; the explicit override and an empty table permit it | Withdrawn rows are the authorization history |

Sharing one row between two verified owners of the **same** dataset, the core of
SEC-171-04, is unchanged and its tests pass unmodified.

`tests/conftest.py` now sets `TRC001_RESEARCH_API_ENABLED=1` for the test process, so
the existing research API tests keep running. The production default (unset ⇒ 404) is
asserted separately with eight flag values.

---

## 8. Verification evidence

All commands were run from `backend/`.

| Check | Command | Result |
|---|---|---|
| Baseline, reviewed commit | TRC-001, retention, ML image and dataset-ingestion test files at `117e083` | 66 passed; Ruff clean |
| Baseline, existing stack | TRC-001, SEC-171-04, SEC-176 and migration test files at `fdaee8e` | 76 passed, 5 skipped |
| New tests before remediation | the three `test_sec171_*` files, PostgreSQL 16 | 25 of 41 fail at `117e083`; 25 of 41 fail at `fdaee8e` |
| Concurrency determinism | `test_sec171_02_*`, 8 consecutive runs per commit | 8 of 8 identical at each commit |
| New tests after remediation | the three files, PostgreSQL 16 / SQLite | 43 passed / 35 passed, 8 skipped |
| Ruff | `ruff check app tests research` | Passed |
| Full suite, SQLite (fresh database) | `python -m pytest tests -q -p no:cacheprovider` | 4152 passed, 27 skipped, 0 failed |
| Alembic, PostgreSQL 16 | `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` | Passed |
| Full suite, PostgreSQL 16 | `python -m pytest tests -q -p no:cacheprovider` | 4170 passed, 9 skipped, 0 failed |
| CI on the remediation pull request | GitHub Actions | Runs on the pull request head, which includes this file; the result is recorded in the pull request, not here |

The 27 SQLite skips are PostgreSQL-only tests (18) and tests needing the optional
research ML dependencies or seeded data (9); the 9 PostgreSQL skips are that second group. None is a skipped SQLite assertion of a
finding: every SEC-171-01 test and the deployment-isolation tests run on SQLite.

Limits of this evidence:

- The concurrency tests prove the two orderings PostgreSQL can produce at the two
  pause points chosen. They do not prove the absence of every possible interleaving.
- The migration tests run in a throwaway schema on a local PostgreSQL 16 and in CI.
  They were not run against a copy of a production database.
- Nothing was deployed. The deployment gate was tested in-process, not on Render.

---

## 9. Residual risks

1. **Two verified owners of the same dataset still share one row** (SEC-171-04, by
   design). The first owner's withdrawal revokes their authorization but the bytes
   remain while the second owner is authorized, and the row keeps the first owner's
   subject as a denormalized hint until the last owner withdraws. The withdrawal
   response reports such rows under `retained_images_kept_with_basis`. Whether this is
   acceptable, or rows should be strictly per-owner, needs a reviewer decision.
2. **Deduplication among non-research sources is still tenant-and-hash only.** An
   inspection upload and a baseline reference of identical bytes still share a row.
   That predates PR #171 and was left alone.
3. **The generic ML routes still take the tenant from a request header.** This
   assessment stops research images being reachable there; it does not fix the header.
4. **The downgrade override is destructive by design.** With
   `TRC001_ALLOW_PROVENANCE_DOWNGRADE=1` provenance columns are dropped, and the next
   application start re-adds them blank through the back-fill.
5. **The deployment gate is one environment variable.** Setting it on a production
   service enables the research API there. It is absent from `render.yaml`, but
   nothing technical prevents an operator adding it.
6. **Research endpoints still appear in the OpenAPI document** when disabled, because
   the router is mounted and gated per request rather than conditionally mounted.
7. **PR #171's description is stale.** It states that `app/` is unchanged and that no
   production code or schema is touched. At `117e083` the PR changes `app/main.py`,
   the `RetainedImage` model, the retention service and adds a migration.
8. **Institutional-basis intake has no revalidation or locking** against a concurrent
   revocation of its retention approval. SEC-171-02 as stated concerns owner
   attestation, and the institutional basis is not exposed through the API.

---

## 10. Freeze exception record

PRs #176–#180 are frozen. This work adds a new commit above `fdaee8e` and does not
rewrite any frozen commit.

| | |
|---|---|
| Requesting authority | The repository owner's instruction of 2026-11-18 to assess and remediate SEC-171-01/02/03 |
| Permitted exception | "A security finding requires corrective action" |
| Reason | SEC-171-01 and parts of SEC-171-03 remain exploitable at the frozen stack tip |
| Affected files | `backend/app/services/image_retention_service.py`, `backend/research/lens_vision/trc001_intake.py`, `backend/app/routes/ml_images.py`, `backend/app/routes/trc001_research.py`, `backend/app/db/migration_guards.py`, `backend/alembic/versions/e8b2c6d49f10_trc001_research_image_provenance.py`, `backend/tests/conftest.py`, three existing test files (section 7), three new test files, `docs/model-development/trc-001/TRC-001_RESEARCH_API.md`, this report |
| Supporting evidence | Sections 3–6 |
| Verification | Section 8 |
| Re-review required | Yes — non-author security review of the remediation commit |

No research methodology, dataset, model or P4.5/P4.6 document was modified.

---

## 11. Required before any GO

- Non-author security review of the remediation commit and of sections 4–6.
- A reviewer decision on residual risk 1 (shared rows between owners of one dataset).
- PR #171's description corrected to match its head.
- Confirmation that PR #171 will not be merged without the fix stack and this branch.
- The open governance gates closed by their owners. This report closes none of them.
