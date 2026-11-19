# P472-03 — Residual-risk register (v1)

| | |
|---|---|
| Reviewed commit | `1ff863d` |
| Reconciled against | the Batch 2 findings register, the application-wide sweep (re-run post-GD-3), and the strict-xfail inventory on this tree |
| Status | Prepared by the author; **no finding is closed** |

Every item is classified into exactly one of: **Remediated & independently
verified** · **Implemented, awaiting independent review** · **Design-only** ·
**Governance approval pending** · **Open security finding** · **Known test-oracle
artifact** · **Not yet assessed**.

## 1. Remediated & independently verified
**None.** No independent non-author review has occurred, so nothing qualifies.

## 2. Implemented, awaiting independent review
AW-01, AW-02, AW-05, AW-09, AW-10, AW-11, AW-12, AW-13 (Batch 1 + Batch 2); GD-1
(counters auth); GD-2 fail-closed half (own-tenant verification); GD-4 (CAPA
quarantine); **GD-3 tenant-private floor** (`78426ce`, `38d1222`) + its migration.
Author-tested; sweep observes AW-01/02/05/09 = 0 and foreign-writes = 0; not
independently reviewed.

## 3. Design-only (not built)
GD-3 ownership model, the three-category scheme, the access-grant table,
manufacturer-managed category, versioning, revocation; the GD-2 authorized
cross-tenant verification path. Pending governance approval (and AW-07 for the
manufacturer category).

## 4. Governance approval pending
GD-1, GD-2, GD-3, GD-4 policy sign-offs; the GD-3 legacy-attribution procedure;
the clinical-workflow quarantine acceptance. All **PENDING** owner decisions.

## 5. Open security findings (not closed)
| ID | Finding | Evidence |
|---|---|---|
| AW-03 | Handler re-reads tenant from an unverified header — 118 routes | strict xfail ×2 |
| AW-04 | Tenant taken from query/path/body — 38 routes | strict xfail ×5 |
| AW-06M | Verified members without a header pooled in `default-tenant` — 122 routes | strict xfail ×2 |
| AW-06N | Users with no membership pooled in `default-tenant` — 28 routes | strict xfail ×2 |
| **AW-07** | `require_manufacturer_auth` accepts any `X-Manufacturer-ID` (no verified manufacturer identity) — **GD-3 category-B blocker** | strict xfail ×1 |
| AW-08 (genuine) | Tenant table read with no tenant predicate: accreditation list-all; vendor scorecard `db.query(Inspection).all()`; GuardianX replay by id | strict xfail ×3 |
| PA-1 | Platform administrator reaches any tenant by header, no purpose/access log | pinned, documented |
| — | Actor/role labels on 11 enterprise audit writes still header-derived | Batch 2 register |
| — | `require_tenant_roles` treats "no header" as `default-tenant` on 176 routes | Batch 2 register |
| — | Refused requests are not audited | Batch 2 register |
| — | Two counters return invented figures when empty | Batch 2 register |
| — | Client-supplied name fields on operations records | Batch 2 register |

## 6. Known test-oracle artifact (NOT a finding)
The adversarial sweep lists `enterprise_vendor_baseline_subscriptions` /
`vendor_baseline_audit_events` as "unscoped SQL leads" on
`POST …/vendor-baseline-subscription/baselines`, `POST …/match`, and
`GET …/findings/kpi-summary`. **These queries are tenant-scoped** (`_tq` emits
`WHERE …tenant_id = ?`); the detector's spaced `" WHERE "` string-match misses the
newline SQLAlchemy renders before `WHERE`, and create's residual flag is
`db.refresh()`'s primary-key read of the caller's own just-created row. Proven not
a leak by the 403 A→B results, foreign-writes = 0, and the tenant-private tests.
**This artifact is separate from the three genuine AW-08 findings in §5 and must
not be conflated with them, nor used to dismiss them.**

## 7. Not yet assessed
- 731 routes only partly exercised by the sweep; 164 role-gated beyond its
  identities.
- Response-content leaks on correctly-scoped 2xx routes (the AW-13 pattern) beyond
  those already found.
- Tenant-triggered background jobs beyond the SLA scan (the AW-12 pattern).
- GD-3 background/async/cache paths by dedicated adversarial test (assessed by code
  inspection only — no such reader found).
- Production environment, production migration readiness, and whether the earlier
  unauthenticated exposure was used (historical access investigation: plan only).

## 8. Strict expected-failures on this tree (15) — none converted
| Test | Finding |
|---|---|
| `…findings::test_aw03_a_member_of_a_cannot_opt_tenant_b_into_the_intelligence_network` | AW-03 (POST /api/network/opt-in, X-LumenAI-Tenant-Id) |
| `…findings::test_aw04_…_create_an_accreditation_program_in_tenant_b` | AW-04 (POST /api/accreditation/programs body tenant) |
| `…findings::test_aw04_…_list_tenant_b_accreditation_programs` | AW-04 (GET /api/accreditation/programs?tenant_id=) |
| `…findings::test_aw04_…_grant_data_sharing_consent_for_tenant_b` | AW-04 (POST /api/intelligence/consent body tenant) |
| `…findings::test_aw04_…_read_tenant_b_network_registry_entry` | AW-04 (GET /api/network-intelligence/registry?tenant_id=) |
| `…findings::test_aw06m_members_of_different_tenants_do_not_share_a_default_tenant` | AW-06M |
| `…findings::test_aw06n_users_with_no_membership_are_still_pooled_where_the_default_is_a_literal` | AW-06N |
| `…findings::test_aw07_a_hospital_user_cannot_assume_an_arbitrary_manufacturer_identity` | AW-07 |
| `…findings::test_aw08_listing_accreditation_programs_does_not_return_other_tenants` | AW-08 (genuine) |
| `…findings::test_aw08_vendor_scorecard_does_not_aggregate_another_tenants_inspections` | AW-08 (genuine) |
| `…findings::test_aw08_guardianx_replay_does_not_serve_another_tenants_inspection` | AW-08 (genuine) |
| `…isolation::test_no_route_exhibits[AW-03]` | AW-03 (118 routes) |
| `…isolation::test_no_route_exhibits[AW-04]` | AW-04 (38 routes) |
| `…isolation::test_no_route_exhibits[AW-06M]` | AW-06M (122 routes) |
| `…isolation::test_no_route_exhibits[AW-06N]` | AW-06N (28 routes) |

No expected failure was converted to a pass; each remains strict and pins an open
finding.

## 9. Review-routing matrix (Phase 6) — all UNASSIGNED
| Review area | Required reviewer | Status |
|---|---|---|
| Batch 2 authorization | Non-author application-security reviewer | UNASSIGNED — APPROVAL REQUIRED |
| GD-3 tenant isolation | Non-author security reviewer | UNASSIGNED — APPROVAL REQUIRED |
| Database migration | Database / platform-engineering reviewer | UNASSIGNED — APPROVAL REQUIRED |
| Clinical-workflow impact | Clinical operations / inspection workflow owner | UNASSIGNED — APPROVAL REQUIRED |
| Manufacturer identity / AW-07 | IAM owner | UNASSIGNED — APPROVAL REQUIRED |
| GD-1…GD-4 policies | Governance decision owners | UNASSIGNED — APPROVAL REQUIRED |
| Enterprise release gate | Release / security-governance authority | UNASSIGNED — APPROVAL REQUIRED |

HOLD / NO-GO · P472-03 OPEN · PR #181 DRAFT.
