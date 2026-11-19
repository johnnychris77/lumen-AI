# P472-03 B6.1 — Genesis Manufacturer Updates: Fail-Closed Isolation (v1)

**Issue #188 · PR #181 (DRAFT).** **GD-6 is NOT signed and is NOT decided here.** Only changes compatible
with documented existing rules (tenant data isolation; Batch 4 tenant-claim rule; anonymized hospital
identities) were made. Nothing designates a new publisher or curator.

## Reproduction (HEAD `9f2b6e3`, before)
`pytest tests/test_p472_03_batch5_genesis_gd6.py::TestOpenFindings --runxfail` → **9 failed** on their own
assertions (200≠404; pending ids listed/enumerable/in chains; cross-tenant publish 200, reject 200,
supersede 201; submitter email disclosed). Sweep at `3c8d347`: 1 route with an AW-04 finding (RB-T01).

## Behaviour now (fail closed)
| Surface | Before | Now |
|---|---|---|
| `GET /{id}`, version chain, list, status filter | every tenant saw every status | an update is visible to its **submitting tenant**, and to others **only when published**; others get **404** (same as a missing id) |
| Publisher filter `manufacturer_tenant_id=` | served any named tenant | may name **only the caller's own tenant**; another tenant → **403** (Batch 4 claim rule) |
| `POST /{id}/review` (publish/reject) | any tenant's leadership | **only the submitting tenant's** leadership (unchanged otherwise); cross-tenant → 404. Each decision writes a hash-chained audit event `genesis.manufacturer_update.{published|rejected}` |
| `supersedes_id` | any id (link into others' chains; 201/404 id oracle) | must be the submitter's own update, else 404 |
| `submitted_by`, `reviewed_by`, publisher tenant id | disclosed to all | `null` for non-owners; `owned_by_caller` flag added |

## Blocked pending GD-6 (not implemented — would require a governance decision)
* A cross-tenant **curator / moderation role** (who may publish or reject another tenant's update).
* Whether the **submitter may self-publish** (today's behaviour is kept, restricted to its own tenant).
* Whether publishers of published content are **public or pseudonymous** (now pseudonymous: fail closed).
* Filtering **other** publishers' published content (now refused).

## Evidence (after)
* `test_p472_03_batch5_genesis_gd6.py`: **21 passed** (6 controls, 9 converted findings, 6 new B6.1
  controls). 8 markers removed with assertions unchanged; **GD6-04's assertion was amended** (the request
  is now refused, so "not listed" is checked as "status in (200, 403), pending id and body absent") —
  flagged for the reviewer.
* Existing Genesis suites: 138 passed.
* Sweeps (SQLite and PostgreSQL 16.15): **1,913 routes, 0 findings** (was 1). Register and matrix
  regenerated; `test_no_route_exhibits[AW-04]` now passes → **RB-T01 is an author conversion**.

## Contract changes (API/frontend owner)
Non-owners get `null` identities and no unpublished content; the publisher filter is own-tenant only;
cross-tenant review is 404. Frontend: `IntelligenceCloudCenter.tsx` calls the unfiltered list and renders only `title`, `update_type`, `version`, `status` — compatible. (Correction: an earlier draft of this note, in commit `38251e6`, wrongly said no frontend file calls these routes.)
