# GD-3 — Vendor & manufacturer baseline ownership: architecture decision record

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Branch | `engineering/render-local-inference-p47` |
| Status of this document | **Proposal for review.** It records a design and the reasons for it. It is **not** an approval of that design, and it does not constitute governance sign-off on the ownership or sharing policy. |
| What is already implemented | Only the **tenant-private default floor** (commit `78426ce`, tightened in a follow-up): an owning-tenant tag, fail-closed quarantine of untagged rows, and tenant-scoping of every read/approval/match/scoring/audit path. **No** sharing grants, **no** manufacturer-managed category, **no** revocation machinery. Those are designed below and deliberately **not built**. |
| Release disposition | **HOLD / NO-GO.** Unchanged. P472-03 stays open. |

> **Execution control honoured.** The GD-3 brief says: *"Stop after the
> architecture, schema, and migration design review if governance approval is
> required before implementation,"* *"Do not introduce schema changes until the
> architecture decision and migration contract have been reviewed,"* and *"Do
> not assume that this prompt constitutes formal approval of GD-3's ownership or
> sharing policy."* Governance approval **is** required. Therefore this document
> is where the work stops for the ownership-model and sharing mechanism. The one
> schema change already on the branch — a nullable `tenant_id` owning-tenant tag
> — is the minimal fail-closed floor (a pure access reduction, no sharing
> surface); it is flagged below as itself pending this review, and it can be
> reverted if the reviewers prefer the whole change to wait.

---

## 1. Component inventory (Phase 1)

Every component that creates, reads, updates, approves, compares, exports or
infers over vendor/manufacturer baselines, with its current tenant posture.

### 1.1 Data models

| Model | Table | Tenant column (before GD-3) | Role |
|---|---|---|---|
| `EnterpriseVendorBaselineSubscription` | `enterprise_vendor_baseline_subscriptions` | **none** | The vendor/manufacturer baseline library record (identifiers, reference image URL, approval status, source). |
| `VendorBaselineAuditEvent` | `vendor_baseline_audit_events` | **none** | Submit/approve/reject/scoring-use audit trail for a baseline. |
| `BaselineLibraryEntry` | `baseline_library` | network-shared by design | The *network* baseline library (manufacturer/model/anatomy), distinct from the vendor-subscription table; intentionally cross-tenant and **out of GD-3 scope**. |
| `VeritasBaselineResolution` | `veritas_baseline_resolutions` | `tenant_id` (already) | Per-resolution audit row written by the governed resolver. |
| `VeritasBaselineGovernanceAction` | — | `tenant_id` (already) | Governance actions over a resolved baseline. |
| `ManufacturerRegistration` | `manufacturer_registrations` | n/a (manufacturer identity) | The manufacturer registry (see §5, AW-07). |

### 1.2 Routes (`app/routes/enterprise_intake.py`)

| Method · path | Handler | Operation |
|---|---|---|
| POST `/api/enterprise/vendor-baseline-subscription/baselines` | `create_enterprise_vendor_baseline_record` | Create |
| POST `…/baselines/upload-image` | `upload_vendor_baseline_image` | Upload reference image (not baseline data) |
| GET `…/baselines` | `list_enterprise_vendor_baseline_records` | List / search |
| POST `…/baselines/{id}/approve` | `approve_enterprise_vendor_baseline_record` | Approve |
| POST `…/match` | `match_enterprise_vendor_baseline_record` | Match for scoring |
| GET `…/baselines/{id}/audit` | `get_enterprise_vendor_baseline_audit_trail` | Read audit trail |
| GET `…/intake/{id}/governance-packet(.pdf)` | packet builders | Export (embeds baseline audit trail) |
| GET `…/intake/{id}/governance-export-package` | export package | Export (counts baseline audit events) |
| GET `…/findings/kpi-summary` | kpi summary | Analytics (counts baselines) |

### 1.3 Services

| Module | Function | Baseline operation |
|---|---|---|
| `baseline_comparison_scoring_service` | `resolve_baseline` → `_resolve_from_uploaded` | Clinical scoring: pick an approved baseline for an instrument |
| `veritas_baseline_resolution_service` | `resolve_governed_baseline` → `_resolve_from_uploaded` / `_enrich_from_uploaded` | Governed resolution + enrichment |
| `veritas_baseline_governance_service` | governance actions | Governance over a resolved baseline (keyed by `baseline_source_type` + id) |
| `veritas_baseline_matching_service` | matching | Matching (no direct Sub query) |
| `vendor_baseline_audit_service` | `log_vendor_baseline_audit_event` | Writes an audit event |
| `seed_demo` | demo inserts | Seeds two demo baselines |

### 1.4 Downstream inference / analytics

Baseline resolution feeds the ranking engine and the inspection/borescope
comparison pipeline through `resolve_baseline`/`resolve_governed_baseline`; the
CV inference provenance (P4.7.2) is a separate trust chain and is **not**
modified by GD-3. `kpi-summary`, the governance packet and the export package
read baseline counts/trails for analytics and evidence.

### 1.5 Client-supplied identifiers (where a caller can name an owner)

| Input | Source | Current trust |
|---|---|---|
| Baseline id (`{baseline_id}` path) | client | Now resolved only within the caller's tenant (floor). A foreign id → not-found/404. |
| Tenant id / name (`X-Tenant-Id`, `X-Tenant-Name`, body) | client | Ignored for ownership; the verified membership tenant is used (Batch 2 rule). |
| **Manufacturer id (`X-Manufacturer-ID`)** | client | **Unverified** — `require_manufacturer_auth` returns the header value as-is. This is open finding **AW-07**. |
| Vendor name / manufacturer name (body) | client | Descriptive only; never used for authorization. |

## 2. Current ownership assumptions and cross-tenant flows (pre-GD-3)

- The vendor-subscription library was **one library for all tenants**: any
  authenticated hospital/vendor caller listed it, one hospital administrator's
  approval made a baseline "approved" for everyone, and
  `baseline_comparison_scoring_service` could score one tenant's inspection
  against a baseline another tenant approved. This is the GD-3 finding and
  batch-1 item R2.
- Manufacturer identity is **asserted by a header** with no verification
  (AW-07). "Supplied by a manufacturer" is therefore not currently a
  trustworthy fact.
- The network `BaselineLibraryEntry` table is a separate, intentionally shared
  library and is out of scope here.

## 3. Proposed ownership model (Phase 1) — **for governance approval**

Three categories. **Treat as proposed until the product owner, clinical quality
lead and data-governance owner approve them.**

**A. Tenant-private baseline.** Owned by one verified tenant; visible and usable
only by authorized members of that tenant; not discoverable by other tenants.
**Default** for newly created tenant baselines. *This is the only category the
floor implements today.*

**B. Manufacturer-managed baseline.** Associated with a **verified** manufacturer
identity; subject to manufacturer authorization/licensing; **not** public;
reachable by a tenant only through an approved access grant. **Blocked on
AW-07** — until manufacturer identity is verified (not a header), this category
cannot be built safely.

**C. Platform-governed shared baseline.** Explicitly approved for sharing, with
documented ownership, licensing and distribution permissions, access controlled
by a dedicated sharing policy. **No** unrestricted access merely because a row
is flagged "shared."

A baseline supplied by a vendor/manufacturer is **not public by default**; it is
category A (private to the submitting tenant) unless a grant or a platform
decision moves it to B or C.

## 4. Proposed schema (Phase 2) — **design only, not applied**

Beyond the owning-tenant tag already on the branch, the full model needs:

**`enterprise_vendor_baseline_subscriptions` (extend)**
- `ownership_type` enum: `tenant_private` | `manufacturer_managed` | `platform_shared` (default `tenant_private`, NOT NULL once backfilled).
- `owner_tenant_id` (nullable; set for category A) — the existing `tenant_id` tag is this column's seed.
- `owner_manufacturer_id` (nullable; set for category B, FK to the manufacturer registry) — usable only once AW-07 is fixed.
- `sharing_classification`, `license_restrictions`, `provenance_source`, `revoked_at` (nullable), `revocation_reason`.
- `version` / `revision_of` to preserve history; approved versions immutable.
- A CHECK/trigger that forbids ambiguous ownership (exactly one of owner_tenant_id / owner_manufacturer_id for A/B; neither for C with a platform approval row).

**`vendor_baseline_baseline_access_grants` (new — not a CSV field)**
- `baseline_id` (FK), `grantee_tenant_id`, `permitted_operations` (read/compare/…),
  `authorizing_actor`, `approval_evidence_ref`, `effective_at`, `expires_at` (nullable),
  `revoked_at` (nullable), `created_at`. Unique on (baseline_id, grantee_tenant_id, active).

**`vendor_baseline_audit_events` (extend)**
- Keep the owning-tenant tag; add grant/revocation event types so every grant,
  revocation and cross-tenant read is audited.

Schema requirements 1–7 from the brief (valid ownership, no ambiguous states,
preserved identifiers/references, immutable approved versions, revocation
without destroying evidence, preserved provenance/audit chain, DB constraints
supporting app-level authz) are satisfied by the above; the access-grant table
replaces any comma-separated tenant list.

**Migration contract (design):** additive columns + the new grant table; existing
rows keep their ids; `ownership_type` backfilled to `tenant_private` only where
an owner is *verified* (see §6), else left in quarantine; reversible down-migration
drops the additions. To be verified up/down on PostgreSQL 16 **after** approval.

## 5. Manufacturer identity (AW-07) is a blocker for category B

`require_manufacturer_auth` (`app/enterprise_auth.py:463`) returns the
`X-Manufacturer-ID` header unverified. Category B ("manufacturer-managed") and
the brief's test *"unauthorized manufacturer identity claims are rejected"*
cannot be satisfied until manufacturer identity is verified against the
`ManufacturerRegistration` registry with a real credential, not a header. This
is recorded as finding AW-07 and must be remediated **before** category B is
implemented.

## 6. Legacy reconciliation and quarantine (Phase 3)

**Inventory (read-only).** The current database carries only the two demo
baselines, now attributed to `demo-tenant`. There are **no** real legacy
production rows in this repository to reconcile; a production reconciliation is
an operations task, not a code change.

**Classification (proposed), per record:** ownership-verified ·
ownership-ambiguous · sharing-authorization-verified · sharing-authorization-missing ·
legacy/orphaned.

**Rule:** never assign an owner by guessing from names, headers, instrument
associations or historical usage. Ambiguous records are preserved and placed in
restricted quarantine (`tenant_id IS NULL` today → visible to no tenant, usable
by no tenant's scoring), with provenance and references intact, released only on
documented ownership verification (the submission audit event, the approving
administrator's membership at the time, or a signed statement from the data
owner). This mirrors GD-4 (ownerless CAPAs). The fail-closed consequence —
existing baselines become unreachable until attributed, changing clinical-quality
output — is a **deployment precondition** and must not ship before the workflow
owner agrees the attribution procedure.

## 7. Centralized authorization-policy design (Phase 4) — **not implemented**

A single `baseline_access` policy would resolve the authenticated actor and
verified tenant/manufacturer identity and decide create/read/list/update/approve/
share/revoke/compare/export/retire **before** any baseline content is loaded or
any downstream inference runs. Access would be by verified ownership or an active
grant; a revoked baseline must not remain reachable through caches, queued jobs
or stored client references; historical evidence is preserved while future
operational use is blocked. The floor already routes every current operation
through `_tq`/`_tget` (verified-tenant scoping); the centralized policy would
generalize that to grants and manufacturer identity — pending approval.

## 8. What is implemented now vs. designed-only

| Capability | State |
|---|---|
| Owning-tenant tag + quarantine of untagged rows | **Implemented** (floor), pending this review |
| Tenant-scoped list/approve/match/audit/scoring/packets/counts | **Implemented** (floor) |
| Adversarial tests (cross-tenant list/approve/audit/scoring refused; quarantine) | **Implemented** (floor) |
| `ownership_type`, manufacturer-managed, platform-shared categories | **Designed only** |
| Access-grant table + grant/revocation/expiry enforcement | **Designed only** |
| Manufacturer identity verification (AW-07 fix) | **Not done** — blocker for category B |
| Centralized `baseline_access` policy | **Designed only** |
| Revocation + cache/queue invalidation | **Designed only** |

## 9. Open risks carried forward

- AW-07: manufacturer identity asserted by header (blocks category B).
- The sharing policy (who may share, to whom, on what license) is **undecided**;
  no grant mechanism should be built before it is.
- The quarantine of pre-GD-3 rows is a clinical-workflow change requiring owner
  sign-off before deployment.
- PA-1: the platform administrator reaches any tenant by header (unchanged,
  documented, open).

## 10. Decision requested

Approve, change or reject: (a) the three ownership categories (§3); (b) the
schema and the separate access-grant table (§4); (c) the legacy reconciliation
and quarantine rule (§6); (d) whether the already-landed tenant-private floor
should remain on the branch or wait with the rest. Only after (a)–(c) are
approved, and AW-07 is remediated for category B, should Phases 4–7 of the brief
be implemented. Until then: **HOLD / NO-GO, PR #181 draft, P472-03 open.**
