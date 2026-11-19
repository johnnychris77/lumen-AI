# P472-03 — Independent Review Packages for Tripwires RB-T01 … RB-T28 (Batch 5, B5.6)

**PR #181 (DRAFT) · Issue #187.** Prepared by the author of the code; **these are requests, not reviews.**
No reviewer is assigned: the repository has one collaborator (`johnnychris77`, program owner) and PR #181
has no reviews. A reviewer must be a qualified person who did not author the change; the release authority
decides whether the program owner qualifies. Every disposition below is **PENDING**.

A reviewer records, per item: identity, date, the commands run and their output, and one of
**ACCEPT-CONVERSION** · **REJECT-CONVERSION** · **ACCEPT-RISK** (named owner) · **KEEP-OPEN**.

## 0. Environment (any reviewer workstation)
```bash
git clone https://github.com/johnnychris77/lumen-AI && cd lumen-AI/backend
pip install -r requirements.txt            # Python 3.11
# PostgreSQL 16 variant: export DATABASE_URL=postgresql://<user>:<pw>@localhost:5432/<fresh db>
export DATABASE_URL=sqlite:////tmp/review.db   # fresh file per run
```

## Package A — RB-T02 … RB-T11 (author-converted exploit tripwires, Batch 4)
File `backend/tests/test_p472_03_application_wide_findings.py`.
1. **Assertions unchanged:** `git diff 4fdac4c 7cead8a -- backend/tests/test_p472_03_application_wide_findings.py`
   must show only removed `@_finding(...)` lines and comments.
2. **Fails before:** `git checkout 4fdac4c && rm -f /tmp/review.db && python -m pytest
   tests/test_p472_03_application_wide_findings.py -q -p no:cacheprovider --runxfail -k "<test name>"` → the
   test FAILS on its assertion (not on setup).
3. **Passes after:** `git checkout <final SHA>`; same command without `--runxfail` → PASSES.
4. For RB-T09…T11 (AW-08) also read the Day-3 fixes `fbd2581`, `137e9b1`, `ae54f5e`.

| ID | Test | Before (4fdac4c) | After |
|---|---|---|---|
| RB-T02 | `test_aw03_a_member_of_a_cannot_opt_tenant_b_into_the_intelligence_network` | must fail | must pass |
| RB-T03 | `test_aw04_a_member_of_a_cannot_create_an_accreditation_program_in_tenant_b` | must fail | must pass |
| RB-T04 | `test_aw04_a_member_of_a_cannot_list_tenant_b_accreditation_programs` | see note¹ | must pass |
| RB-T05 | `test_aw04_a_member_of_a_cannot_grant_data_sharing_consent_for_tenant_b` | must fail | must pass |
| RB-T06 | `test_aw04_a_member_of_a_cannot_read_tenant_b_network_registry_entry` | must fail | must pass |
| RB-T07 | `test_aw06m_members_of_different_tenants_do_not_share_a_default_tenant` | must fail | must pass |
| RB-T08 | `test_aw06n_users_with_no_membership_are_still_pooled_where_the_default_is_a_literal` | must fail | must pass |
| RB-T09 | `test_aw08_listing_accreditation_programs_does_not_return_other_tenants` | fail at the pre-Day-3 SHA² | must pass |
| RB-T10 | `test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections` | fail at the pre-Day-3 SHA² | must pass |
| RB-T11 | `test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` | fail at the pre-Day-3 SHA² | must pass |

¹ RB-T04's read path was made inert in batch 3 (`30638f0`) and refused in batch 4; reproduce at `30638f0^`.
² The AW-08 fixes predate `4fdac4c`; reproduce at the parent of each fix commit.

## Package B — RB-T12 … RB-T14 (register-driven sweep classes) and the sweep oracle
`test_no_route_exhibits[AW-03|AW-06M|AW-06N]` flip because the findings register no longer lists those
classes. The reviewer must verify the **oracle**, not only the test:
```bash
python scripts/tenant_isolation_matrix.py --sweep sqlite --workdir "$(mktemp -d)" --out /tmp/sweep.json
python scripts/tenant_isolation_matrix.py --from /tmp/sweep.json --write-register /tmp/register.json
diff <(jq -S .findings tests/p472_03_findings_register.json) <(jq -S .findings /tmp/register.json)
# PostgreSQL 16: add --sweep postgres --postgres-url <url> (scratch schemas, dropped afterwards)
```
Expected at the final SHA: 1 route with a finding (`GET /api/genesis-ai/manufacturer-updates`, AW-04).
Then at `4fdac4c`: AW-03 118, AW-04 32, AW-06M 122, AW-06N 28 routes. Review `tests/tenant_isolation_sweep_runner.py`
(what the oracle can and cannot see: only SQL through the app engine that binds the foreign tenant).

## Package C — RB-T01 (open; must remain blocking until a real fix + non-author validation)
`test_no_route_exhibits[AW-04]` (strict xfail). Same oracle commands as Package B. Linked to GD6-04 below.
Resolution requires GD-6 (Package D) and then a non-author re-run of both sweeps.

## Package D — RB-T15 … RB-T23 (new in Batch 5: Genesis, pending GD-6)
File `backend/tests/test_p472_03_batch5_genesis_gd6.py`. Verify each fails on its own assertion:
`python -m pytest tests/test_p472_03_batch5_genesis_gd6.py::TestOpenFindings --runxfail -q`.
| ID | Finding | Test |
|---|---|---|
| RB-T15 | GD6-01 read pending update by id | `test_another_tenant_cannot_read_a_pending_update_by_id` |
| RB-T16 | GD6-02 feed lists unpublished updates | `test_the_feed_does_not_list_another_tenants_unpublished_updates` |
| RB-T17 | GD6-03 status-filter side channel | `test_status_filter_does_not_reveal_another_tenants_pending_updates` |
| RB-T18 | GD6-04 publisher filter (= RB-T01 route) | `test_publisher_filter_does_not_reveal_unpublished_content` |
| RB-T19 | GD6-05 version chain discloses drafts | `test_version_chain_does_not_disclose_unpublished_versions` |
| RB-T20 | GD6-06 cross-tenant publish | `test_another_tenant_cannot_publish` |
| RB-T21 | GD6-07 cross-tenant reject | `test_another_tenant_cannot_reject` |
| RB-T22 | GD6-08 supersedes linkage / id oracle | `test_cannot_supersede_another_tenants_update` |
| RB-T23 | GD6-09 submitter identities disclosed | `test_other_tenants_do_not_see_submitter_identities` |

## Package E — RB-T24 … RB-T28 (new in Batch 5: GuardianX ledger, pending GD-7)
File `backend/tests/test_p472_03_batch5_guardianx_gd7.py`, class `TestOpenOwnershipFindings` (`--runxfail`).
RB-T24 GD7-01 read by id · RB-T25 GD7-02 list by source · RB-T26 GD7-03 cross-tenant verify ·
RB-T27 GD7-04 reviewer email disclosure · RB-T28 GD7-05 source contamination.
Also review the **implemented** integrity fix (`TestIntegrity`, reproduced before: tampered evidence and
signatures verified) and the read-only classifier (`TestOwnershipClassificationDryRun`).

## Package F — Batch 5 implemented changes (not tripwires; need review before closure)
| Change | Commit | Reviewer focus |
|---|---|---|
| B5.1 tenant context (`/api/auth/tenants`, `TenantProvider`, removal of hard-coded tenants and `dev-token` fallbacks) | `189094d` | API test 8/23 fail before; browser e2e `frontend/tests/e2e/tenantContext.e2e.mjs` 0/6 on `7cead8a`, 6/6 after (run per header of that file) |
| B5.5 role lookup on canonical schema; legacy users-table login disabled (AUTH-1) | `e226ee2`, `06394c0` | 6/13 fail before on SQLite and PG16; contract change: `users.role` now applied |
| B5.2 manufacturer lifecycle (expiry, audited revocation, gated grants, migration `b5a2c7e19d40`) | `de80b7b` | grant gate closed; downgrade guard; no HTTP surface |
| B5.4 ledger content sealing + verify contract | `3c8d347` | legacy rows now report `verified: false` |
