# P472-03 Batch 7 — GuardianX GD7-05 Write-Side Source Authorization (v1)

**Issue #189 · PR #181 (DRAFT) · reproduced at `4667ab8`.** Author evidence; **not** independently reviewed.
**RB-T28 is not accepted and GuardianX write authorization is not "remediated"**: the fix below is a
fail-closed floor for the cases existing policy settles. The rest stays open pending GD-7 (unsigned).

## 1. Why RB-T28 was not enough

`test_another_tenant_cannot_contaminate_a_source` (RB-T28, converted in B6.2) asserts only that tenant A's
**listing** does not show tenant B's entry. It passed because the B6.2 read gate hides entries whose audit
owner is not the caller. The foreign **write** was never refused, so it was never tested. RB-T28 is
preserved; its set-up now seeds the contaminated state through the service layer, because the HTTP write is
now refused. Its assertion is unchanged, and a comment in the test states its read-side-only coverage.

## 2. Reproduction at `4667ab8` (before), SQLite and PostgreSQL 16.15 — identical

Script: `backend/scripts/p472_03_gx_source_write_repro.py` (local DB only; refuses production). Raw output:
`evidence/p472-03-batch7/gd7-05-write-side/gx_repro_before_{sqlite,pg16}.json`.

| Step (tenant B = attacker, A = victim) | Before | After (Batch 7) |
|---|---|---|
| B writes ledger evidence under **A's inspection** | **201**; row persisted, audit owner B | **404** |
| B writes ledger evidence under **A's `capa_suggestion` key** (ownerless) | **201**; persisted | **403** |
| B writes ledger evidence under a **non-existent** inspection | **201** | **404** |
| B writes an **explanation** under A's inspection | **201** | **404** |
| B sets `tenant_id_for_digital_twin` = A on `POST /explainability` | **201**; A's digital-twin health computed and returned to B | **403** |
| A's ledger list / inspection replay shows B's **evidence** | no (B6.2 read gate) | no |
| A's inspection replay and recommendation replay show B's **explanation** | **yes** (integrity of A's audit replay) | no |
| B reads A's private **explanation** (list, recommendation replay, audit-evidence package) | **yes** | **yes — still open (RB-T32)** |
| Dry-run classifier `classify_entries` on B's injected row | `attributable` to **B** under A's source key | (no new injected rows) |

**Persisted state before the fix:** the injected rows carry B's reviewer email and a valid hash-chained audit
event under B. Integrity verification passes for them; nothing marks them as contamination.

**Downstream consumers** (the complete inventory below): the B6.2 read gate already hides foreign *ledger* rows
from A. The real impact was through explanations, which have no owner and no read filter, and through the GD-7
migration path: the dry-run classifier would attribute the injected row to B, permanently binding B's
evidence to A's object. **Rows injected before Batch 7 may already exist in any deployed database.** None was
examined; that is part of HIST and must also be handled in the GD-7 migration design (§6).

## 3. Inventory

| Item | Fact (code at `4667ab8`) |
|---|---|
| Writers | exactly two, both HTTP: `POST /api/guardianx/evidence` → `record_evidence`; `POST /api/guardianx/explainability` → `create_explanation`. No scheduler, job or service writes ledger or explanation rows. |
| `source_type` | free-form client string; no enum, no validation (empty strings accepted before). |
| Source types with a tenant-owned table | `inspection` → `inspections.tenant_id` (reads scoped since AW-08c); `workflow_execution` → `forge_workflow_executions.tenant_id` (replay scoped since B6.2b). |
| Source types without an owner table | `capa_suggestion`, `rca_suggestion` (generated on the fly by `capa_suggestion_service`, never persisted with an id); anything else a client invents. |
| Unknown-source behaviour (before) | accepted, persisted, signed, audited under the writer's tenant. |
| Ledger readers | `GET /evidence/{id}`, `/evidence/{id}/verify`, `GET /evidence` (B6.2 gate); replay of inspection, workflow execution and recommendation (gate via `list_entries_for_source`); `GET /reports/audit-evidence-package` calls the replay **with no tenant** (ledger part therefore empty for everyone — fail closed). |
| Explanation readers | `GET /explainability/{id}`, `GET /explainability`, all replays, audit-evidence package: **no tenant filter at all** (RB-T32). |
| `audit_chain` in recommendation replay | `verify_audit_chain(resource_type=source_type, resource_id=source_id)` without an owner tenant: reports chain status for any resource named by the caller (metadata only; recorded under RB-T32 scope). |

## 4. Design — fail-closed source-ownership layer (`app/services/guardianx_source_ownership.py`)

1. **Validation:** `source_type`/`source_id` must be non-empty strings of at most 200 characters (422).
2. **Owned source types** (`OWNED_SOURCE_TYPES`: inspection, workflow_execution): the row must exist **and**
   belong to the caller's verified tenant. Missing and foreign are indistinguishable (404, no existence
   oracle). This is established policy: the same objects' reads are already tenant-scoped.
3. **Ownerless source types, ledger writes:** refused (403) when the key already holds any entry whose
   audit-trail owner is not the caller. That covers another tenant's entries and legacy entries with no
   provable single owner. This blocks the operation that is unsafe under every GD-7 option. A key no one
   has used stays writable, as before.
4. **Explanation writes:** owned source types checked as in (2). Ownerless explanation writes are unchanged,
   because explanation rows have no owner and no audit trail, so no check can be grounded (RB-T32 / GD-7).
5. **Digital-twin claim:** `tenant_id_for_digital_twin` is a tenant claim; any value other than the caller's
   verified tenant is refused with `refuse_other_tenants` (403). This is the established AW-04 rule.
6. Adding a source type to `OWNED_SOURCE_TYPES` is a reviewed code change, not configuration.

**Not implemented — governance-dependent (GD-7, unsigned):**
* whether ownerless keys may be written at all, namespaced per tenant, or registered first (today a fresh key
  is writable, so the first writer effectively "holds" it: squatting is possible, but it affects availability,
  not confidentiality);
* explanation ownership (owner column, audit event, read gate) — RB-T32 stays a **failing** strict tripwire;
* the audit-evidence package's missing tenant parameter, and replay `audit_chain` without an owner;
* treatment of contaminated rows already stored before Batch 7 (classifier/migration must also check source
  ownership, not only the audit trail).

## 5. Tests

`backend/tests/test_p472_03_batch7_guardianx_source_ownership.py`:

| ID | Test(s) | Before (`4667ab8`, `--runxfail`) | After |
|---|---|---|---|
| RB-T29 (GD7-06) | foreign inspection, foreign workflow execution, missing inspection | 3 × fail (`201 == 404`) | pass |
| RB-T30 (GD7-07) | ownerless key in use by another tenant | fail (`201 == 403`) | pass |
| RB-T31 (GX-08) | explanation under foreign inspection | fail (`201 == 404`) | pass |
| RB-T32 (GX-09) | explanations not disclosed cross-tenant | fail (private text returned) | **still fails — strict xfail kept (OPEN)** |
| RB-T33 (GX-10) | digital-twin claim of another tenant | fail (`201 == 403`) | pass |
| Controls (7) | owner writes for own inspection / execution; repeated own ownerless key; fresh ownerless key; own explanation; own digital-twin claim; unauthenticated refused | pass | pass |

The conversions of RB-T29/30/31/33 are **author conversions** (markers removed, assertions unchanged) and
release blockers until a non-author disposition.

**Existing tests changed (set-up only, assertions unchanged):**
* `test_p472_03_batch5_guardianx_gd7.py::…::test_another_tenant_cannot_contaminate_a_source` (RB-T28): the
  contaminated state is seeded via the service layer, and the comment documents read-side-only coverage.
* `test_p472_03_batch4_remediation.py::test_guardianx_evidence_audit_event_is_attributed_to_the_verified_tenant`:
  it wrote under a non-existent inspection id; it now creates the inspection in the caller's tenant.
* `test_p472_03_batch2_remediation.py::test_the_route_table_is_the_mounted_application`: census 715 → 716
  (`POST /explainability` now uses `refuse_other_tenants`).

**Results (author, LOCAL):** SQLite: new file + GuardianX suites 64 passed + 1 xfailed (RB-T32); Batch 4 +
route-wide Batch 2 harness in full: 2,041 passed, 2 failed (the two tests above), then those 2 re-run after the
set-up/census changes: 2 passed (the full files are re-run in the final suites). PostgreSQL 16.15: 66 passed +
1 xfailed. Full-suite results are in the Batch 7 release-gate index.

## 6. Contract changes (for the API owner)

| Request | Before | After |
|---|---|---|
| `POST /evidence` or `/explainability` with `source_type` inspection/workflow_execution not owned by the caller's tenant, or non-existent | 201 | 404 |
| `POST /evidence` into an ownerless key already holding another (or unprovable) owner's entries | 201 | 403 |
| Empty / over-long `source_type` or `source_id` | 201 | 422 |
| `tenant_id_for_digital_twin` naming another tenant | 201 (other tenant's health computed) | 403 |

## 7. Residual risks (open)

| ID | Risk | Status |
|---|---|---|
| R-GX-EXPLAIN-READ | Explanations readable cross-tenant (RB-T32) | **OPEN — failing tripwire; GD-7** |
| R-GX-OWNERLESS-KEYS | First writer of a fresh ownerless key blocks others (squatting); no namespace | OPEN — GD-7 |
| R-GX-WRITE-RACE | Two tenants writing a never-used ownerless key concurrently can both pass the check (no lock) | OPEN — low; GD-7 design should namespace keys |
| R-GX-LEGACY-CONTAMINATION | Rows injected before Batch 7 remain and verify as valid; the dry-run classifier would attribute them to the injector | OPEN — HIST + GD-7 migration must check source ownership |
| R-GX-PKG-TENANTLESS | `/reports/audit-evidence-package` takes no tenant (ledger part empty for all; explanations leak) | OPEN — part of RB-T32 |
