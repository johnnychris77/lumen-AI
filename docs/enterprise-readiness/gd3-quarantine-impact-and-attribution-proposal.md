# GD-3 — Legacy-baseline quarantine: clinical-workflow impact and attribution procedure proposal

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft), head `c9a0f73` |
| Status | **Proposal + evidence, for governance approval.** Not a sign-off. No production data was touched; no baseline was attributed. |
| Release disposition | **HOLD / NO-GO.** P472-03 open. |

This document answers two of the GD-3 handoff questions: what breaks for a tenant
whose baselines are quarantined (§2), and the procedure proposed for attributing
those baselines back to their owners (§3). The migration behaviour it relies on
was validated on PostgreSQL 16 against representative legacy records (§1).

---

## 1. Migration validation against representative legacy records (evidence)

Reproduced on PostgreSQL 16, database migrated to the **pre-GD-3** head
`c9d1f7a3e5b2` (where `enterprise_vendor_baseline_subscriptions` has **no**
`tenant_id` column), then three representative legacy baselines and three legacy
audit events were inserted, then `alembic upgrade head` applied the GD-3
migration `d8f3a6b914c7`.

| Check | Result |
|---|---|
| Pre-GD-3: `tenant_id` column absent on both tables | Confirmed (empty `information_schema` result) |
| After upgrade: rows preserved | 3 baselines, 3 audit events — **all preserved** |
| After upgrade: ownership | **100 % `tenant_id IS NULL`** (3 of 3 baselines, 3 of 3 audit events) |
| After upgrade: original data intact | catalog numbers, categories, approval statuses unchanged |
| Tenant-scoped SQL read (`tenant_id = 'tenant-A'` / `'demo-tenant'`) | **0 rows** — NULL never matches an explicit tenant |
| Application scoring `resolve_baseline(legacy-category, tenant)` for `tenant-A`, `demo-tenant`, `default-tenant` | **`baseline_found = False`** for all three |
| Governed resolver `resolve_governed_baseline(tenant-A, legacy-category)` | **`SUPERVISOR_REVIEW_REQUIRED`**, tier `none` |
| `alembic downgrade -1` (remove GD-3) | rows preserved: 3 baselines, 3 audit events still present |
| `alembic upgrade head` again | rows re-quarantined: 3 of 3 `tenant_id IS NULL` |

**Conclusion:** the migration is **non-destructive and reversible**. Existing
baselines are **preserved** but **inaccessible** — invisible to every tenant and
usable by no tenant's scoring — until ownership is verified and set. This is the
intended fail-closed behaviour (the same shape as GD-4 for ownerless CAPAs).

## 2. Clinical-workflow impact when historical baselines are quarantined

When GD-3 ships, every baseline written before GD-3 has `tenant_id IS NULL` and
is quarantined. For a tenant **until its baselines are attributed**, these
operations change. (A tenant that never had vendor baselines is unaffected; the
network `BaselineLibraryEntry` library is a separate, intentionally shared table
and is **not** quarantined.)

| Operation | Route / service | Behaviour while baselines are quarantined |
|---|---|---|
| **List / search** vendor baselines | `GET …/vendor-baseline-subscription/baselines` | Returns an empty library for that tenant; `total_library_count` = 0. No error. |
| **Match** an instrument to a baseline | `POST …/vendor-baseline-subscription/match` | `match_status: no_match`; recommended action "route to baseline review queue or request vendor baseline." |
| **Approve** a baseline | `POST …/baselines/{id}/approve` | The quarantined id resolves as not-found (`{"status":"not_found"}`); nothing to approve until attributed. |
| **Audit trail** of a baseline | `GET …/baselines/{id}/audit` | 404 for a quarantined id. |
| **Clinical scoring / baseline comparison** | `resolve_baseline` → ranking engine, inspection & borescope comparison | `baseline_found = False` → **no manufacturer/vendor baseline**; the comparison falls through to **supervisor review required**; numeric baseline-match metrics are unavailable and confidence is lowered. **This is the clinical-quality–affecting change.** |
| **Governed resolution** | `resolve_governed_baseline` | `SUPERVISOR_REVIEW_REQUIRED`, tier `none`. |
| **Governance packet / export** | `…/governance-packet(.pdf)`, `…/governance-export-package` | The vendor-baseline audit-trail section is empty for that tenant; baseline audit-event counts are 0. |
| **KPI / analytics** | `…/findings/kpi-summary` | `total_baselines`, `approved_baselines`, `pending_baselines`, `vendor_submissions` all 0; `approval_rate` 0. |

**What does NOT change:** the network `BaselineLibraryEntry` resolution path
(manufacturer/model/anatomy) is unchanged, so inspections that resolve from the
network library are unaffected; CV inference provenance (P4.7.2) is untouched;
no inspection is blocked — it is routed to supervisor review rather than scored
against a vendor baseline.

**Severity.** For a site that relied on vendor-subscription baselines for
scoring, every such inspection drops to supervisor review until its baselines are
attributed. That is a **change to clinical-quality workflow output** and is why
this must not ship before the baseline-workflow owner has agreed the attribution
procedure below. It is a safe-direction change (abstain rather than score against
an unowned baseline), not a silent wrong answer.

## 3. Attribution procedure proposal (for owner approval — no production attribution performed)

A quarantined baseline is released to a tenant **only** by an explicit,
evidenced attribution. This is a proposal; **no attribution was performed**, and
none should be until the baseline-workflow owner and the data-governance owner
approve this procedure. Attribution must never be inferred from names, request
headers, instrument associations or historical usage.

**Required evidence per baseline, before `tenant_id` is set:**

1. **Evidence of ownership** — one of: the original submission audit event
   identifying the submitting tenant; the approving administrator's tenant
   membership at the time of approval; or a signed statement from the data owner.
2. **Documented reviewer authorization** — the person performing attribution
   holds an authorized baseline-governance role and is named in the record.
3. **Audit record** — a `vendor_baseline_audit_event` of a new
   `baseline_attributed` type is written for each attribution, carrying the
   assigned `tenant_id`, the evidence reference, the authorizing reviewer, and the
   timestamp. (This event type is part of the GD-3 design, not yet built.)
4. **Post-attribution verification** — after `tenant_id` is set, confirm that the
   baseline is visible to **only** the assigned tenant (a cross-tenant read still
   returns not-found), that the owning tenant's scoring now resolves it, and that
   no other tenant's scoring does.

**Process (proposed):**

- Produce a reconciliation worklist of all `tenant_id IS NULL` baselines
  (read-only; a count/inventory query only).
- For each, classify as ownership-verified / ownership-ambiguous /
  sharing-authorization-verified / sharing-authorization-missing /
  legacy-orphaned (per the architecture decision record).
- Attribute **only** the ownership-verified rows, one at a time, each with its
  evidence and audit event, then run the post-attribution verification.
- Ambiguous / orphaned rows stay quarantined; a manufacturer-published baseline
  intended for many tenants is **not** attributed to one — it waits for the
  platform-shared / access-grant mechanism, which is design-only and gated on
  governance sign-off and the AW-07 manufacturer-identity fix.
- Attribution runs in a controlled change window, not as an automatic migration
  step. **No automatic legacy attribution** is part of the migration.

**Explicitly out of scope of this document:** performing any attribution,
building the `baseline_attributed` event type or the attribution tooling,
building the sharing/manufacturer mechanism, or deploying anything. Those follow
governance approval.

## 4. Sign-off (to be completed by the owners — unsigned)

| Role | Name | Decision on §3 procedure | Date |
|---|---|---|---|
| Baseline-workflow owner | _unassigned_ | _pending_ | — |
| Data-governance owner | _unassigned_ | _pending_ | — |
| Clinical quality lead (impact in §2) | _unassigned_ | _pending_ | — |

Until signed, the quarantine stays, no baseline is attributed, GD-3 stays open,
and the release stays **HOLD / NO-GO**.
