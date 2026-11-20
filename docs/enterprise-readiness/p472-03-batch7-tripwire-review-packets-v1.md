# P472-03 Batch 7 (B7.1) — Non-Author Security Verification Packets, RB-T01 … RB-T28 (v1)

**Issue #189 · PR #181 (DRAFT) · code under review: `2976b4e` (= application code at `c6ba66c` and at the
Batch 7 head; Batch 7 changes only CI, scripts and documents).** Prepared by the author of the changes.
**These are requests, not reviews.** Every disposition is **PENDING** and every reviewer is **UNASSIGNED**:
the repository has one collaborator (the program owner) and PR #181 has no reviews. The author cannot
self-approve; the author's reproduction runs below are labelled LOCAL-AUTHOR evidence.

* Per-tripwire packets (generated from the kit's result files, so they cannot drift from the evidence):
  `p472-03-batch7-tripwire-review-packets-generated-v1.md`
* Disposition ledger (the only place a disposition may be recorded): `p472-03-batch7-tripwire-disposition-ledger-v1.md`
* Raw author results: `evidence/p472-03-batch7/kit/kit-results-sqlite.json`, `kit-results-postgres.json`

## 1. Reproduction kit (least privilege, no production data)

`backend/scripts/p472_03_tripwire_review_kit.py` — runs each test-based tripwire in a throw-away git worktree
with a **fresh** SQLite file or PostgreSQL database (created and dropped per run), always with `--runxfail`
so a marker never hides an outcome, and records the JUnit outcome and first message line.

| Variant | Code | Test file | Expected for a genuine fix |
|---|---|---|---|
| `before/original` | parent of the fix | as it was while still marked xfail | **fails on an assertion** |
| `before/final` | parent of the fix | as it is now | **fails on an assertion** (same assertions now enforced) |
| `after/final` | code under review | as it is now | passes |
| `after/original` | code under review | as it was while marked | passes — except RB-T18 (amended) |

A `before` run that *errors* (import or fixture failure) instead of failing on an assertion is **not**
reproduction; the packet shows the message so the reviewer can tell. Same-tenant controls (legitimate access
must still work) are run once on the code under review.

```bash
git clone https://github.com/johnnychris77/lumen-AI && cd lumen-AI && git checkout <code under review>
pip install -r backend/requirements-lock.txt          # Python 3.11
python backend/scripts/p472_03_tripwire_review_kit.py list
python backend/scripts/p472_03_tripwire_review_kit.py diff RB-T18            # original vs final assertion
python backend/scripts/p472_03_tripwire_review_kit.py run --db sqlite --out /tmp/kit
python backend/scripts/p472_03_tripwire_review_kit.py run --db postgres \
    --pg-admin-url postgresql://USER:PW@localhost:5432/postgres --out /tmp/kit   # PostgreSQL 16
python backend/scripts/p472_03_tripwire_review_kit.py report /tmp/kit/kit-results-*.json --out /tmp/packets.md
```
Register-driven tripwires (RB-T01, RB-T12…T14): `kit sweep --sha <before>` and `--sha <after>`, then count
routes carrying the class. **The reviewer must judge the oracle, not only the test** (§3).

## 2. Areas the issue asks the reviewer to scrutinise

| Area | What the author found when preparing the packets (not a review) | Reviewer question |
|---|---|---|
| **GD6-04 / RB-T18 assertion amendment** | Original (`9f2b6e3`): request returns 200 and the pending id is not listed. Final (`38251e6`): status must be 200 **or 403**; the pending id must not be listed; the pending body must not appear anywhere in the response. Status 500/404 still fail. `after/original` fails because the request is now refused with 403. | Does accepting 403 weaken the security intent? The author's view: it is strictly stronger on content (body check added) and accepts a refusal; but a reviewer must confirm a 403 is the intended contract (GD-6). |
| **Register-driven RB-T12…T14 (and RB-T01)** | `test_no_route_exhibits[<class>]` passes when the class is absent from `p472_03_findings_register.json`, and the isolation test fails if the sweep observes a route not in the register. Conversion therefore depends on (a) the sweep being run in the suite, (b) the oracle seeing the defect class. | Re-run both sweeps; confirm the oracle would have caught the original instances (before-SHA sweep counts); review the oracle's blind spots (§3). |
| **Genesis RB-T15…T23** | Behaviour is a fail-closed floor (B6.1). Note: owner-only publish means a tenant can still **self-publish** network-wide; this is the open GD-6 question, not a tripwire. | Inspect `_visible_to`, `_get_visible_or_404`, `_get_owned_or_404`, `review_update` and `_to_dict` redaction in `app/services/genesis_ai_manufacturer_portal_service.py`. |
| **GuardianX RB-T24…T28** | Read gate = `audit_owner_tenant` (single real tenant on the hash-chained trail). **RB-T28 passes through read-side filtering only**: tenant B's write under tenant A's `source_id` is still accepted (the test asserts what A sees, not that the write is refused). | Is RB-T28 a valid conversion **of a read-side control only**? Since `6a661bb` write-side refusal is a separate set of tripwires (RB-T29…T31, T33 converted; RB-T32 explanation disclosure still **failing**), see `p472-03-batch7-gd7-05-write-side-authorization-v1.md`. Review `app/services/guardianx_source_ownership.py`. |
| **Replay by id (supplementary S-REPLAY-WFX, S-REPLAY-RULE)** | Reproduced 200 before `00aec32`, 404 after; `replay_workflow_execution` / `replay_rule` filter by verified tenant. | Inspect `app/services/guardianx_audit_replay_service.py`; check other replay entry points for the same pattern. |

## 3. Sweep oracle blind spots (assessment for the reviewer)

The sweep (`tests/tenant_isolation_sweep_runner.py`) calls every mounted route as several identities and flags
a route when **SQL executed for the request binds a foreign tenant**. At `2976b4e`: 1,913 routes, 0 findings,
0 foreign-write routes; **733 (SQLite) / 727 (PG16) routes only partly exercised**, **164 role-gated** beyond
its identities, **354 unscoped-SQL leads**, 45 public routes.

| Blind spot | Why the oracle misses it | Existing compensating evidence | Residual |
|---|---|---|---|
| Authenticated multi-membership | Covered for "two memberships naming a third"; not for every route's behaviour when switching between two legitimate memberships mid-session | B5.1 browser E2E (multi-tenant switch), batch-2 harness owner/selected-membership cases | Medium |
| Role-gated routes (164) | Sweep identities lack the roles → 403 before any SQL | per-module tests where they exist | **Medium–High: not swept** |
| 2xx response leakage | Oracle inspects bound SQL parameters, not response bodies; a query **without** a tenant predicate returns other tenants' rows and binds nothing foreign | 354 unscoped-SQL leads listed in the matrix for manual review | **High until the leads are reviewed** |
| IDOR on object ids | Lookup by primary key binds no tenant; only caught where a test exists (AW-08, B6.2b were found by hand) | AW-08 tests, B6.2b replay tests | Medium–High |
| Pagination / totals | Counts across tenants leak volume without rows | none systematic | Low–Medium |
| Background jobs, schedulers, async consumers | Not request-scoped; never called by the sweep | AW-12 SLA-scan fix (single case) | Medium |
| Historical data | Code-level only; says nothing about past access | HIST plan (unauthorized) | Unknown |
| Privileged tokens (PA-1) | Platform admin / dev identities are not attackers in the sweep; their cross-tenant reach is by design | PA-1 log line | **High (standing privilege)** |
| Non-SQL stores (files, caches, in-memory) | Invisible to the SQL oracle (AW-10 was found this way) | pattern scan in matrix §1.4 | Medium |
| Partly exercised routes (727–733) | Request failed validation before reaching tenant logic | none | Medium |

**Conclusion for the reviewer:** a zero-finding sweep is necessary, not sufficient. It cannot by itself support
ACCEPT-CONVERSION for RB-T01/RB-T12…T14 without a review of the leads and blind spots above.

## 4. Reviewer roster required (none assigned)

| Package | Tripwires | Reviewer profile | Assigned |
|---|---|---|---|
| A — exploit tests | RB-T02…T11 | application-security engineer (multi-tenant authorization) | **UNASSIGNED** |
| B/C — sweep oracle | RB-T01, RB-T12…T14 | security engineer able to review the oracle and the 354 leads | **UNASSIGNED** |
| D — Genesis | RB-T15…T23 | security engineer + GD-6 owner for intent | **UNASSIGNED** |
| E — GuardianX | RB-T24…T28 + supplementary replay | security engineer + data/migration reviewer (GD-7) | **UNASSIGNED** |

Independence: the reviewer must not have authored the changes under review. Whether the program owner
qualifies for any package is a release-authority decision, not the author's.
