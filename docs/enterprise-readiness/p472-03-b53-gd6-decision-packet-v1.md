# P472-03 B5.3 — Genesis Manufacturer Updates: GD-6 Decision Packet (v1)

**Issue #187 · PR #181 (DRAFT) · RB-T01 stays OPEN.** Author-assembled evidence; **not a decision**.
GD-6 owner: network / clinical governance — **UNSIGNED**. No access behaviour was changed in Batch 5.

## 1. Surface (`app/routes/genesis_ai_intelligence_cloud.py`, `genesis_ai_manufacturer_portal_service.py`)
| Route | Roles | Behaviour today |
|---|---|---|
| `POST /api/genesis-ai/manufacturer-updates` | admin, spd_manager of the **verified** tenant | stored as `pending_review` under the verified tenant (body tenant ignored) |
| `POST /…/{id}/review` (`published` / `rejected`→draft) | admin, spd_manager of **any** tenant | no ownership check |
| `GET /…/{id}`, `GET /…/{id}/version-chain` | any role of any tenant | no ownership or status check |
| `GET /…?manufacturer_tenant_id=&status=&update_type=` | any role of any tenant | all statuses, all publishers; no pagination |

## 2. Reproduced exposures (strict tripwires in `tests/test_p472_03_batch5_genesis_gd6.py`)
Each fails today on its own assertion (verified with `--runxfail`); 6 control tests pass.
| ID | Exposure | Evidence (tenant B viewer/lead vs tenant A content) |
|---|---|---|
| GD6-01 | Read another tenant's **pending** update by id (object-id substitution) | 200, body returned |
| GD6-02 | Feed lists other tenants' unpublished updates | pending id listed |
| GD6-03 | `status=pending_review` filter enumerates other tenants' drafts (filter side channel) | rows of tenant A returned |
| GD6-04 | Publisher filter `manufacturer_tenant_id=` returns unpublished content — **the AW-04 register entry / RB-T01** | pending id listed |
| GD6-05 | Version chain discloses unpublished predecessors | draft id in chain |
| GD6-06 | Another tenant's leadership **publishes** an update | 200 |
| GD6-07 | Another tenant's leadership **rejects** (reverts to draft) an update | 200 |
| GD6-08 | `supersedes_id` links into another tenant's chain; 201/404 is an id-existence oracle | 201 |
| GD6-09 | Submitter / reviewer **user emails** disclosed to every tenant | email present |

Note on RB-T01: the sweep oracle flags the publisher filter because SQL binds a client-named tenant. Under
the proposed default below, filtering *published* content by publisher is legitimate; the finding resolves
only when unpublished content is excluded for non-owners **and** a reviewer confirms the oracle result.

## 3. Proposed least-privilege default (for decision; NOT implemented)
1. Unpublished (`pending_review`, `draft`) updates visible **only to the submitting tenant**; other tenants
   get 404 (indistinguishable from non-existent) on `/{id}`, are filtered out of lists/filters/chains.
2. Published updates visible network-wide; the publisher filter applies to published content only.
3. **Moderation**: the submitting tenant cannot self-publish; publication/rejection only by a separately
   authorized platform curator role (not any tenant's `spd_manager`), with a hash-chained audit event per
   decision (actor, decision, before/after status).
4. `supersedes_id` must reference the submitter's own update (else 404 — no existence oracle).
5. Other tenants see an anonymized publisher label and no `submitted_by` / `reviewed_by` identities
   (consistent with "hospital identities in cross-hospital intelligence must be anonymized").
6. Pagination with tenant-scoped totals.

## 4. Questions for GD-6
1. Is the feed curated by a platform role, by manufacturers, or by each tenant? Who may publish/reject?
2. May any tenant (incl. hospitals) submit, or only verified manufacturer organizations (link to AW-07 /
   GD-9 manufacturer identity)?
3. Is publisher identity public for published content, or pseudonymous?
4. Retention/visibility of rejected content.
5. What happens to the content already published by non-curators under the current open model (no
   production data examined here)?

## 5. Implementation readiness
Once GD-6 is signed: implement §3 behind the decision, convert the GD6-xx tripwires **only** where the
assertion is unchanged, re-run both sweeps, and route RB-T01/RB-T15…RB-T23 to a non-author reviewer.
