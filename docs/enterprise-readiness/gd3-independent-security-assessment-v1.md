# GD-3 — Independent security assessment (v1)

| | |
|---|---|
| Reviewed commits | `78426ce` (floor + migration), `38d1222` (audit dedup scoping), `c9a0f73` (ownership ADR), `1ff863d` (governance handoff) |
| Reviewer | **UNASSIGNED — non-author security reviewer required** |
| Status | Control checks + DB assurance + coverage gaps prepared by the author; **AWAITING NON-AUTHOR REVIEW** |

The **implemented tenant-private floor** (`78426ce`, `38d1222`) is assessed
separately from the **proposed sharing architecture** (`c9a0f73`,
`gd3-vendor-baseline-architecture-decision.md`), which is design-only and **not
built**.

## 1. Security controls — implemented floor

| # | Control | Author-verified state | Class | Reviewer action |
|---|---|---|---|---|
| 1 | Baseline subscriptions & audit events tenant-scoped | `tenant_id` column on both tables; reads via `_tq`/`_tget` | PASS (impl) | Confirm no raw `db.query(Sub)` without a tenant predicate remains |
| 2 | Tenant identity from verified auth context | `authorized_tenant(require_* )`; never header/body | PASS (impl) | Confirm on all 6 routes + 2 services |
| 3 | Foreign baseline id cannot bypass authz | `_tget` → None for foreign/NULL id; approve/audit return not-found/404 | PASS (impl) | Probe foreign id on approve & audit |
| 4 | Cross-tenant approval & matching denied | approve → `not_found`; match uses `_tq` | PASS (impl) | Probe approve/match as tenant A on B's baseline |
| 5 | Scoring & packets cannot expose foreign baselines | `resolve_baseline`/`resolve_governed_baseline` and packet trail scoped | PASS (impl) | Confirm packet PDF/JSON carry only caller's trail |
| 6 | Audit dedup cannot cross tenants | create/approve dedup reads scoped via `_tq` (`38d1222`) | PASS (impl) | Confirm |
| 7 | Legacy NULL-owned records inaccessible | NULL never matches an explicit tenant; scoring `baseline_found False` | PASS (impl, PG16-validated) | Confirm on a production-like dataset |
| 8 | No unapproved sharing pathway | sharing/manufacturer/grant code not built | PASS (absent by design) | Confirm no latent cross-tenant path |

**Adversarial evidence:** every A→B probe naming another tenant → 403 on all six
vendor-baseline routes; **foreign writes to both tables = 0** across all 1,912
routes. Tests: `TestGd3VendorBaselinesAreTenantPrivate` (5) + 38 adversarial
baseline-route cases; assertions two-sided (foreign refused **and** owner served),
none weakened, no xfail/skip.

## 2. Test-coverage assessment — what the 5+38 tests do and do NOT cover

| Path | Covered? | Finding |
|---|---|---|
| API list/approve/match/audit cross-tenant | Yes (API tests) | — |
| Service-layer scoring (`resolve_baseline`, `resolve_governed_baseline`) | Yes (direct service calls in the suite) | — |
| Governed enrichment (`_enrich_from_uploaded`) | Indirectly (via resolver) | Reviewer: add a direct foreign-id enrichment probe |
| Background jobs / schedulers reading baselines | **No dedicated test** | **Assessed by code search: none exists** — no `app/jobs|tasks|workers|schedulers` module reads the vendor-baseline tables or calls the resolver. The inspection scoring path threads the inspection's stored verified `tenant_id`. Reviewer should confirm this remains true. |
| Asynchronous inspection analysis | Indirect | Scoring receives the inspection's `tenant_id`; no async path bypasses it. Reviewer to confirm `inspection_job` passes the stored tenant. |
| Cached baseline references | **No cache exists** | The resolver queries live each call; there is no baseline cache or stored client-side baseline id that is re-read without re-scoping. Reviewer to confirm. |
| Revocation of a previously accessible baseline | **Design only** | Revocation machinery is not built; the floor has no sharing to revoke. Out of scope until the sharing model is approved. |

**Residual risks (document, do not assume secure):**
- The `db.refresh()` primary-key read of a just-created own-tenant row in the
  create route is unscoped by tenant (it reads the caller's own new row); benign
  but a reviewer should confirm it cannot be driven cross-tenant.
- Coverage of background/async/cache is by **code inspection**, not by a dedicated
  adversarial test; a reviewer may want such a test added before sign-off.

## 3. Database assurance — migration `d8f3a6b914c7`

Validated on PostgreSQL 16 (evidence: `gd3-quarantine-impact-and-attribution-proposal.md` §1).

| Check | Result | Class |
|---|---|---|
| Upgrade adds nullable, indexed `tenant_id` to both tables | Confirmed | PASS |
| Downgrade removes columns/indexes | Confirmed | PASS |
| Existing records preserved on upgrade **and** downgrade | 3/3 baselines, 3/3 audit events preserved both ways | PASS |
| NULL-owned records quarantined | 100% `tenant_id IS NULL`; invisible to every tenant | PASS |
| Referential integrity | No FK added/broken; `baseline_id` index intact | PASS (representative) |
| Tenant-scoped DB queries | `WHERE ...tenant_id = ?` on all reads (see AW-08 note) | PASS |
| Safe rollback | Reversible, non-destructive | PASS |
| PostgreSQL 16 compatibility | Transactional DDL, clean up/down/up | PASS |

**Representative vs production readiness:** the validation used synthetic
representative legacy rows. **Production migration readiness is PENDING** —
production row counts, the true distribution of NULL-owned rows, and the agreed
attribution procedure are not part of this evidence.

## 4. AW-08 artifact vs. genuine missing tenant filters — **do not conflate**

The adversarial sweep lists `enterprise_vendor_baseline_subscriptions` /
`vendor_baseline_audit_events` as "unscoped SQL leads" on the create/match/kpi
routes. **This is a detector artifact, not a finding:** those queries *do* filter
on `tenant_id`, but SQLAlchemy renders the predicate after a newline
(`…subscriptions \nWHERE …tenant_id = ?`) and the sweep's `" WHERE "` (spaced)
string-match misses it; create's residual flag is `db.refresh()`'s primary-key
read of the caller's own row. Confirmed by: the 403 A→B results, foreign-writes =
0, and the passing tenant-private tests.

This is **distinct** from the **three genuine AW-08 strict xfails** elsewhere
(accreditation list-all, vendor scorecard `db.query(Inspection).all()`, GuardianX
replay), which are real missing tenant filters and remain **OPEN**. A reviewer
must not treat the GD-3 artifact as resolving those, nor treat the genuine
xfails as artifacts.

## 5. Proposed sharing architecture (not built) — reviewer questions

Assess `gd3-vendor-baseline-architecture-decision.md`: whether the access-grant
table, manufacturer-managed category and revocation design prevent any
cross-tenant reach without verified ownership or an active grant; and confirm the
manufacturer-managed category stays **BLOCKED** until **AW-07** (unverified
`X-Manufacturer-ID`, confirmed by a strict xfail) is remediated.

## Disposition

Floor **implemented and author-tested**; sharing **design-only**; **AWAITING
NON-AUTHOR REVIEW**; production migration readiness **PENDING**; AW-07 **OPEN**.
HOLD / NO-GO.
