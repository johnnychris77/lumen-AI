# P472-03 Batch 8 — GuardianX Explanation Ownership (RB-T32 and GX-11…GX-14) (v1)

**Issues #190 / #189 · PR #181 (DRAFT)** · Baseline `83dbf70` · Tripwires-first commit `eec3bc8` · Fix: see §6.

Status: **author-remediated; not independently reviewed; GD-7 unsigned.** "Remediated" means the reproduction now
passes. It does not mean accepted or closed. Release stays **HOLD / NO-GO**.

## 1. What was wrong (reproduced, not inferred)

`scripts/p472_03_gx_explanation_repro.py` was run against fresh SQLite and fresh PostgreSQL 16.15 databases at
`83dbf70`. Outputs are in `evidence/p472-03-batch8/explanations-before/`.

| # | Tenant B action against tenant A's explanation | `83dbf70` | Persisted / effect |
|---|---|---|---|
| 1 | `GET /explainability?source_type&source_id` (A's ownerless key) | **200, A's private text** | — |
| 2 | `GET /explainability/{id}` (A's ownerless-key and inspection explanations) | **200, A's private text** | — |
| 3 | `GET /audit-replay/recommendations` | **200, A's private text** | — |
| 4 | `GET /reports/audit-evidence-package` (took no tenant at all) | **200, A's private text** | — |
| 5 | `POST /explainability/{id}/human-override` (a **write**) | **200** | **B's override persisted in A's record** |
| 6 | `POST /explainability` under A's ownerless key | **201** | B's row appears in **A's** list and replay |
| 7 | `GET /audit-replay/recommendations?source_type=<any resource>` | chain verified **without the GD-2 tenant scope** | event count of another tenant's chain disclosed |
| — | Audit attribution of explanation writes | **none**: no audit event existed for any explanation | ownership unprovable |

All seven were identical on both databases. Same-tenant use (list, read, override, inspection replay) worked.

## 2. Inventory

| Item | Finding |
|---|---|
| Explanation writers | `POST /explainability` → `create_explanation`; `POST /explainability/{id}/human-override` → `record_human_override`. No job, scheduler, bulk or internal path writes explanation rows (`grep` of `AIExplainabilityRecord` / `guardianx_explainability_service` in `backend/app`). Nova collaboration only references an explanation id |
| Explanation readers | `GET /explainability/{id}`, `GET /explainability`, `replay_inspection`, `replay_recommendation`, `audit_evidence_package` |
| `source_type` classes | **owned**: `inspection` (`Inspection.tenant_id`), `workflow_execution` (`WorkflowExecution.tenant_id`). **ownerless**: every other value (`capa_suggestion`, `rca_suggestion`, any free-form string) — no table records the source. **global / unsupported**: none defined. An unregistered type is ownerless |
| Owner of an explanation row | none stored (no column, no audit event) before Batch 8 |
| Ledger counterpart | B6.2: a ledger entry's owner is the single real tenant on its hash-chained audit trail (`audit_owner_tenant`); entries without one are readable by no tenant |

## 3. Design — centralized, fail-closed, no GD-7 option chosen

GD-7 asks whether GuardianX records are tenant-owned (**Option T**: add `tenant_id`) or platform-wide (**Option P**).
Adding an owner column would choose T. So this batch adds **no schema change** and reuses the ownership rule
already in force for the ledger since B6.2. That rule is listed as "current behaviour" in the GD-7 packet.

`app/services/guardianx_source_ownership.py` is the single policy point:

1. **Attribution.** Every explanation creation and every human override writes a hash-chained audit event
   (`guardianx.explanation_recorded` / `guardianx.explanation_overridden`, resource type
   `guardianx_explainability_record`) under the writer's **verified** tenant. The row and its event commit in
   one transaction.
2. **Ownership.** `explanation_owner(record)` is the single real tenant on that trail. It is `None` for no event,
   only `default-tenant` / no tenant, or several tenants.
3. **Reads and amendments.** These are allowed only when the caller's verified tenant equals the owner. This covers
   list, by-id, override, both replays and the audit-evidence package. A missing explanation and a foreign one are
   indistinguishable (404). With no verified tenant, nothing is returned.
4. **Legacy rows** (written before Batch 8, so no trail) are served to **no tenant**. They are not deleted and not
   re-attributed. Their release is GD-7 / CLIN-1 (issue #190: "quarantined GuardianX legacy rows remain unavailable
   pending GD-7/CLIN-1").
5. **Writes.**
   - Owned types: the source must exist in the caller's tenant (Batch 7; 404 otherwise, with no existence oracle).
   - Ownerless keys are one namespace across the ledger and explanations. A ledger or explanation write into a key
     that already holds a ledger entry or an explanation **not provably the caller's** is refused (403).
   - A key no one has used remains writable. Whether that should continue is GD-7 (R-GX-OWNERLESS-KEYS).
6. **Replays.** Every replayed audit chain is verified under the GD-2 tenant scope (`owner_tenant_id`, already
   enforced on the enterprise-quality routes).
   - Another tenant's chain reads as "no events".
   - A mixed chain raises `AuditChainScopeError`, which maps to 403.
   - Without a verified tenant nothing is verified. An empty tenant must not match events stored with no tenant.
7. **Not trusted from the caller:** `tenant_id`, `source_id` ownership, `created_by`. The tenant always comes from
   `require_tenant_roles` (verified membership).

## 4. Tests

| Test | At `83dbf70` (`eec3bc8`) | After fix |
|---|---|---|
| RB-T32 GX-09 explanations not disclosed (list, replay, package, by id) | strict xfail (fails) | pass — **converted, assertion unchanged** |
| RB-T34 GX-11 no foreign human override (404, row unchanged) | strict xfail (fails) | pass — converted |
| RB-T35 GX-12 no explanation into a key in use (403, not in owner's list) | strict xfail (fails) | pass — converted |
| RB-T36 GX-13 legacy (unattributable) explanation served to no tenant | strict xfail (fails) | pass — converted |
| RB-T37 GX-14 replay does not report another tenant's audit chain | strict xfail (fails) | pass — converted |
| Negative (new, not tripwires): multi-member selecting C cannot read A's; concurrent first writers never see each other; ledger write into a key holding A's explanation refused; refused writes persist no row and no audit event | 3 of the 4 **failed** (the fourth was added with the fix) | pass |
| Controls: owner list / read / override; several own explanations; inspection replay + package show own; owner sees own audit chain; least-privileged (viewer) member reads; deleted source refused (404); unauthenticated refused | pass | pass |

The no-persistence test was flaky in its first version: it counted all of tenant B's rows, including one the
concurrent-write test may legitimately create. It now compares counts before and after (8/8 stable runs).

## 5. Contract changes (visible to API clients)

| Request | Before | After |
|---|---|---|
| Read or override another tenant's explanation by id | 200 | 404 |
| List / replay / package of a source | every tenant's explanations | the caller's own only |
| Explanation written before Batch 8 | visible to everyone | visible to **no one** (quarantined) — availability impact |
| Explanation or ledger write into an ownerless key used by another tenant | explanation 201 (ledger already 403) | 403 |
| Replay of a resource whose audit chain belongs to another tenant | chain verified and reported | "no events"; mixed chain → 403 |
| `/reports/audit-evidence-package` | tenantless | caller's tenant view |

## 6. Remaining (not remediated; separate open risks)

* **GD-7 unsigned.** This is an interim floor compatible with Option T and Option P. Under P, tenant users would
  lose these reads entirely. The owner must decide.
* **R-GX-OWNERLESS-KEYS / R-GX-WRITE-RACE:** a fresh key belongs to its first writer. Two concurrent first writes
  can both succeed; each then sees only its own rows (test-pinned), so there is no disclosure, only key sharing.
* **R-GX-EXPLAIN-LEGACY (new):** pre-Batch-8 explanations are unavailable to every tenant until GD-7 / CLIN-1.
  The number of such rows in deployed databases is unknown (production not examined).
* **Explanation content is not sealed.** The audit event records source and override count, not a content digest.
  A database writer could edit an explanation undetected. Sealing like the ledger (B5.4) is a follow-up.
* **R-HIST:** whether cross-tenant explanation reads or overrides happened before Batch 8 is not investigated.
* Author tests only. **No independent review** of RB-T32 or RB-T34…T37.
