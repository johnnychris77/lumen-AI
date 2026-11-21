# P472-03 — Remediation Batch 1: AW-09, AW-10, AW-11

| | |
|---|---|
| Repository / PR | `johnnychris77/lumen-AI`, PR #181 (draft) |
| Branch | `engineering/render-local-inference-p47` |
| Baseline | `90fb1a6` |
| Release status | **HOLD / NO-GO** |
| P472-03 status | **Open.** This batch fixes three findings; ten remain (section 9). |
| Independent review | **Not performed.** The tests here were written by the author of the fix. |

Batch 1 remediates the three findings from the application-wide review
(`p472-03-application-wide-authorization-matrix.md`) that allowed
unauthenticated access to tenant data or had no tenant ownership at all:

| Finding | What it was | Routes |
|---|---|---|
| AW-09 | Enterprise quality routes with no authentication, reading and exporting every tenant's findings, evidence, CAPAs and audit log | 41 |
| AW-10 | Vendor governance events in one in-memory list with no tenant field, read without authentication | 4 (+1 public probe) |
| AW-11 | CAPA register with no tenant ownership: any manager listed, read and modified every tenant's CAPAs | 8 (+1 public probe, +7 other readers and writers of the register) |

It does **not** claim tenant isolation for the application, and it does not
close P472-03.

---

## 1. Scope actually changed, and why it is wider than the 53 routes

The three findings name 53 routes. The change covers **94 routes in three
modules** plus the services behind them, because fixing only the named routes
would have left the same records reachable through their neighbours:

- **Enterprise quality (`app/routes/enterprise_intake.py`, 77 routes).** 41
  routes had no authentication. Code review for this batch found that 21 of the
  36 *already authenticated* routes of the same module read the same records
  with no tenant predicate either (for example `GET /intake/history` listed
  every tenant's findings to any signed-in user, and the PDF form of a
  governance packet served any tenant's finding by id to any hospital
  administrator), and 5 more accepted a client-supplied `tenant_id` (the intake
  body, which defaulted to the literal tenant `bonsecours`, and four audit
  queries). The sweep had not seen these because its identities lack the
  hospital-administrator role. Authenticating the 41 routes while leaving their
  siblings would have fixed nothing an authenticated user could not undo with a
  different URL, so the whole module follows one rule.
- **Vendor governance (`app/routes/vendor_governance.py`, 8 routes).** The four
  read routes, the three write routes (which created and linked events in a
  store shared by all tenants) and the health probe, which returned every
  tenant's event counts and vendor names.
- **CAPA register (`app/routes/capa.py`, 9 routes) and every other caller of
  `capa_service`.** The register is written by seven other code paths
  (workflow engines, CAPA suggestions, vendor governance) and read by two
  analytics routes and a second service, `capa_lifecycle_service`, which treated
  ownerless rows as visible to every tenant. All now pass a tenant.

Three AW-09 routes are **not** changed: `GET /api/network/participants/count`,
`GET /api/global-intelligence/network-stats` and
`GET /api/infrastructure/platform-stats`. Their own code documents them as
public and they return only network-wide totals. They stay in the findings
register, unremediated, until an owner confirms that policy (section 9).

---

## 2. Contracts before the change

Captured at `90fb1a6` from the application-wide sweep and from the source. The
per-endpoint detail is in section 7 ("Auth before", "Findings before").

| Module | Authentication before | Tenant source before | Object-level check before |
|---|---|---|---|
| Enterprise quality | None on 43 routes (41 with tenant data, one object route that answered 404, one health probe). `require_enterprise_auth(request)` or a hospital/enterprise-administrator guard on the other 34. | None. Queries had no tenant predicate. `POST /intake` stored `payload.tenant_id` (default `"bonsecours"`). Four audit routes filtered by an optional `tenant_id` query parameter; with none, all tenants. Exports wrote audit rows with `tenant_id=""`. | None. `db.get(Model, id)` on any id. |
| Vendor governance | None on the 4 reads and the health probe; `require_enterprise_auth` on the 3 writes. | None. One list for all tenants. | None. Any event id. |
| CAPA register | Global role only (`require_roles`); the health probe in `main.py` was public and returned register totals and the database file path. | None. No tenant column was written or read by `capa_service`. | None. Any CAPA id. |

---

## 3. The rule now enforced

One rule, the same as the earlier four-module remediation (`6c3072c`), applied
inline in every handler so the endpoint-governance scanner sees the auth call:

```python
tenant_id = authorized_tenant(require_enterprise_auth(request, db=db))
```

- The caller must present a valid token **and** be an enabled member of the
  tenant they act in. For a signed user token that tenant is the explicit
  `X-Tenant-Id` when one is sent and membership verifies, otherwise the user's
  sole membership. A user with no membership is refused; a user with several
  must select one.
- The tenant is never taken from a header on its own, a query parameter, a path
  or a body. Where a request can still name a tenant (`POST /intake` body, the
  `tenant_id` filter of four audit routes) the value is a **claim**: naming any
  other tenant is refused with 403. It is never rewritten to the caller's
  tenant.
- Existing role and permission guards are unchanged and still apply on top.
- No privileged cross-tenant path was added.

How each store enforces it:

| Store | Enforcement |
|---|---|
| Enterprise quality tables (11 tenant-owned tables and `audit_logs`) | Every query in the module goes through two helpers: `_tq(db, Model, tenant_id)` adds the tenant predicate, `_tget(db, tenant_id, Model, id)` returns `None` for another tenant's row. No handler queries a tenant-owned model directly. Audit rows are stamped with the verified tenant. |
| Audit queries and exports | `query_audit_events` and the two export builders take `owner_tenant_id`, applied to the `audit_logs.tenant_id` column. The audit writer now fills that column from the caller's auth context when no tenant is passed (it used to leave the default, `default-tenant`). The event hash is unaffected: it is computed from `details`, not columns. |
| Vendor governance events | Each event records `tenant_id`. Every service function requires the caller's tenant and sees only that tenant's events. The three illustrative events seeded at start-up belong to the `demo` tenant. |
| CAPA register | A `tenant_id` column (added in place if missing). Every function of `capa_service` and `capa_lifecycle_service` requires a tenant and raises without one; there is no all-tenants mode. Every SQL statement carries the tenant. |

Another tenant's object is reported exactly like one that does not exist
(404). A refused request stores nothing.

---

## 4. API contract changes

| Request | Before | Now | Kind |
|---|---|---|---|
| Any of the 41 enterprise quality routes, the 4 vendor-governance reads, without credentials | 200 with data | 401 | **Change (the fix)** |
| Any protected route of the three modules, authenticated user with no tenant membership | 200 on routes that had no auth or only a global role | 403 | **Change** |
| Object route with another tenant's id (finding, evidence, CAPA, instrument, baseline, vendor event, register CAPA) | 200 with that tenant's record, or the write applied | 404, nothing changed | **Change (the fix)** |
| Lists, dashboards, exports, KPI and audit views | all tenants | caller's tenant only | **Change (the fix)** |
| `POST /api/enterprise/intake` with no `tenant_id` | finding created in `bonsecours` | created in the caller's tenant | **Change** |
| `POST /api/enterprise/intake` naming another tenant | created in that tenant | 403 | **Change (the fix)** |
| `GET /api/enterprise/audit/events`, `…/export.csv`, `…/evidence-bundle`, `…/download.json` with `tenant_id` of another tenant | that tenant's events | 403 | **Change (the fix)** |
| …the same with no `tenant_id` | all tenants | caller's tenant | **Change** |
| `X-Tenant-Id` naming a tenant the user is not a member of | already 403 on routes using `require_enterprise_auth`; 200 elsewhere | 403 everywhere in the three modules | **Change** on 53 routes |
| `POST …/vendor-governance/events` or `…/link-capa` with a `capa_id` that is not a CAPA of the caller's tenant | accepted (any string) | 404 | **Change** |
| `GET /api/capa/health`, `GET /api/enterprise/vendor-governance/health` (public probes) | `summary` held all-tenant figures (and the CAPA database path) | `summary: {}` | **Change** |
| Vendor governance for a real tenant | three illustrative events shown to everyone | none; they belong to the `demo` tenant | **Change** |
| `GET /api/pilot-analytics/capa-effectiveness` for a caller with no single verified tenant (including the platform admin's all-tenant view) | CAPA figures over all tenants | CAPA figures empty; inspection figures unchanged | **Change** |
| CAPAs stored before this change (no owner) | visible to every tenant | visible to no tenant | **Change; data decision needed** |
| Any same-tenant request | 200 | 200, same response shape | Compatible |

Response schemas are unchanged except that vendor governance events now
include their `tenant_id`.

---

## 5. Client changes made with the fix

| Change | Files |
|---|---|
| Removed the hard-coded `X-Tenant-Id: bonsecours` and `X-Tenant-Name: Bon Secours` headers (12 places). The server resolves the tenant from membership; a user who is not a member of `bonsecours` was refused by any route that verified the header. | `EnterpriseAuditTrailPanel`, `EnterpriseIntakePanel`, `EnterpriseGovernanceCommandCenter`, `ManufacturerBaselinePanel`, `EnterpriseCapaPanel`, `EnterpriseCapaSummaryPanel`, `VendorIntake`, `DashboardApp` |
| Exports that are now authenticated were opened with plain links or `window.open`, which cannot send the bearer token. They now download through a new helper, `openProtectedFile` / `onProtectedLinkClick` in `lib/api.ts`. Three of these links pointed at routes that were already protected and were therefore already failing. | `PacketActionButtonsPanel` (5), `ExecutiveQualityReviewPanel`, `InfectionPreventionReviewPanel`, `VendorBaselineSubscriptionPortal` (3), `ExecutiveGovernanceDashboard`, `CapaWorkflowPanel`, `VendorGovernancePanel` |

External consumers could not be surveyed from the repository. Anything that
read the Power BI CSV, toolkit or dashboard exports without credentials, or
that named another organisation's tenant, will now be refused.

**Existing tests whose set-up changed.** Seven existing tests exercised the
remediated routes in a way the new rule refuses. Their set-up was brought in
line with the rule; no assertion about behaviour was altered or removed.

| Tests | What they did | Change |
|---|---|---|
| `test_audit_csv_export`, `test_audit_export_hash`, `test_audit_export_manifest`, `test_audit_query_filters`, `test_compliance_evidence_bundle`, `test_compliance_evidence_bundle_download` (one test each) | Authenticated with the development token and named the tenant only as a `tenant_id` query filter, which is now a claim that must agree with the caller's tenant. | The request also states that tenant in `X-Tenant-Id` (through the existing `TenantHeaderClient` test wrapper, now also applied to `/api/enterprise/audit`). |
| `test_inspection_intelligence_workflow::test_baseline_comparison_returns_structured_response` | Seeded a finding and instrument in `test-tenant` and a baseline with no tenant, then called the route with no tenant. | The request states `test-tenant`, and the seeded baseline carries its instrument's tenant, as the application always writes it. |
| `test_p472_03_application_wide_findings` | 17 strict expected failures for AW-09, AW-10 and AW-11. | Markers removed; the assertions are unchanged and now pass as ordinary tests. |
| `test_p472_03_application_wide_isolation` | Counted the routes covered by a dedicated remediation test file (`13 + 39`). | Count extended to `13 + 39 + 77 + 8 + 9` for the three modules of this batch. |

---

## 6. Adversarial results, before and after

**Application-wide sweep** (every mounted route; two SQLite runs and one
PostgreSQL 16 run agree, before and after):

| | Before (`90fb1a6`) | After |
|---|---|---|
| Routes with a sweep finding | 682 | 641 |
| AW-09, unauthenticated access to tenant tables | 44 | 3 (the public aggregate counters, unchanged) |
| AW-06M / AW-06N on these modules | 8 / 8 | 0 / 0 |
| Routes answering an anonymous request with 2xx | 93 | 48 |
| New findings anywhere | — | 0 |
| Unauthenticated or invalid-token request reaching tenant-bound SQL | 0 | 0 |

**Exploit tests** in `backend/tests/test_p472_03_application_wide_findings.py`.
Each states the secure behaviour; before the fix each failed for the stated
reason and was held as a strict `xfail`.

| Finding | Tests | Before | After |
|---|---|---|---|
| AW-09 | 8 | xfail: anonymous 200 with every tenant's audit log and quality data | pass |
| AW-10 | 5 | xfail: anonymous 200 with tenant B's event; tenant A saw B's event | pass |
| AW-11 | 4 | xfail: tenant A listed, read by id and modified tenant B's CAPA | pass |

Only the `xfail` markers were removed; no assertion changed. The 14 tests for
the other findings are still strict `xfail`.

**Dedicated tests** in `backend/tests/test_p472_03_batch1_remediation.py`: 1,491
tests over all 94 routes, with two tenants that each own real records.

| Area | Tests | What is asserted |
|---|---|---|
| Route table and request table | 2 | the tables are exactly the mounted routes of the three modules; every write has a valid body |
| Callers with no verified identity | 819 | 9 identities × 91 protected routes: anonymous, anonymous naming tenant B, malformed token, expired token, tampered signature, role headers without a token, no membership (with and without naming B), disabled membership. Refused; nothing of B revealed; B's records and all row counts unchanged |
| Public probes | 3 | still public; carry no per-tenant figures |
| Object-id substitution | 26 | A's valid credentials with B's finding, evidence, CAPA, instrument, baseline, event and register ids: refused or not found, nothing revealed, nothing changed |
| Tenant named in the verified header | 91 | 403 on every route |
| Disagreeing tenant headers | 91 | 403 on every route |
| Unverified tenant header alone | 91 | does not move the caller; no SQL binds tenant B |
| Body, query and link claims | 7 | intake naming B or a literal tenant creates nothing; audit queries naming B are refused; an event cannot be linked to B's CAPA |
| Lists, aggregates, exports | 54 | nothing of B in any listing, including inside PDFs and ZIP members |
| SQL structure | 66 | for every read route: no statement binds B; every statement on a tenant-owned table is tenant-filtered or a primary-key lookup |
| Aggregates and other register readers | 2 | counts equal the caller's own records |
| Verification routes | 3 | return verification metadata only (see open item R1) |
| Owner workflow | 91 + 14 + 3 | the owner succeeds on every route and sees their own records; records created without naming a tenant belong to the caller; audit rows carry the caller's tenant |
| User with two memberships | 26 + 1 + 91 | acts only in the selected tenant; no selection or a third tenant is refused |
| Stores | 10 | every service function requires a tenant; an ownerless CAPA is visible to nobody and cannot be advanced; seeded demo events are not served to real tenants |

A mutation check: removing the tenant predicate from the two query helpers
makes 107 of these tests fail.

---

## 7. Endpoint-by-endpoint matrix

Generated from the sweep before and after the change and from the source.
"Findings before" lists sweep classes and, where the sweep could not reach the
route, what code review found. Every row is **not independently reviewed**.

<!-- BEGIN BATCH1 MATRIX -->
| Method | Route | Module | Auth before | Findings before | Auth after | Tenant source after | Tenant and object scope after | Findings after | Contract change |
|---|---|---|---|---|---|---|---|---|---|
| GET | `/api/capa/health` | capa | — | — | — | unreachable duplicate (shadowed by the public probe in `main.py`) | — | — | — |
| GET | `/api/capa` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager, viewer) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| POST | `/api/capa` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| POST | `/api/capa/from-audit-signal` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| GET | `/api/capa/escalation-summary` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| GET | `/api/capa/powerbi-csv` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| GET | `/api/capa/governance-scorecard` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant | none | limited to caller's tenant; no membership → 403 |
| GET | `/api/capa/{capa_id}` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager, viewer) | verified context | CAPA register scoped to tenant; other tenant's id = 404 | none | other tenant's object → 404; no membership → 403 |
| PATCH | `/api/capa/{capa_id}` | capa | bearer + global role | AW-11 | verified member + global role (admin, spd_manager) | verified context | CAPA register scoped to tenant; other tenant's id = 404 | none | other tenant's object → 404; no membership → 403 |
| POST | `/api/enterprise/intake` | enterprise_intake | in handler: require_hospital_or_enterprise_admin | client tenant_id trusted (code review) | verified member + hospital/enterprise admin | verified context; body tenant_id is a claim (403 if different) | fixed content; audit row recorded in caller's tenant | none | foreign tenant claim → 403 |
| GET | `/api/enterprise/intake/history` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | every query tenant-filtered | none | limited to caller's tenant |
| GET | `/api/enterprise/intake/{finding_id}/governance-packet` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/governance-packet.pdf` | enterprise_intake | in handler: _require_governance_packet_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/intake/{finding_id}/governance-packet/verify-hash` | enterprise_intake | in handler: _require_governance_packet_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | rows for the id read in tenant only | none | none |
| GET | `/api/enterprise/intake/{finding_id}/governance-export-history` | enterprise_intake | in handler: _require_governance_packet_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | rows for the id read in tenant only | none | none |
| GET | `/api/enterprise/audit-trail` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | every query tenant-filtered | none | limited to caller's tenant |
| POST | `/api/enterprise/intake/{finding_id}/review` | enterprise_intake | in handler: require_hospital_or_enterprise_admin | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| POST | `/api/enterprise/intake/{finding_id}/capa` | enterprise_intake | in handler: require_hospital_or_enterprise_admin | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/capas` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | every query tenant-filtered | none | limited to caller's tenant |
| PATCH | `/api/enterprise/capas/{capa_id}/status` | enterprise_intake | in handler: require_hospital_or_enterprise_admin | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/capas/summary` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | every query tenant-filtered | none | limited to caller's tenant |
| POST | `/api/enterprise/intake/{finding_id}/evidence` | enterprise_intake | in handler: require_hospital_or_enterprise_admin | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/intake/{finding_id}/evidence` | enterprise_intake | none (public) | AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/evidence/{evidence_id}/download` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| POST | `/api/enterprise/instruments/{instrument_id}/baseline` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/instruments/{instrument_id}/baseline` | enterprise_intake | undetermined (anonymous 404) | no tenant predicate (code review; sweep role-gated) | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 404 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/vendor-baselines` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| POST | `/api/enterprise/intake/{finding_id}/baseline-comparison` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| POST | `/api/enterprise/baselines/{baseline_id}/review` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | other tenant's object → 404; limited to caller's tenant |
| GET | `/api/enterprise/storage/health` | enterprise_intake | none (public) | none | public probe | — | no tenant data returned | none | none |
| GET | `/api/enterprise/intake/{finding_id}/governance-export-package` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/governance-zip-bundle` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/vendor-escalation-packet` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/vendor-escalation-packet.pdf` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/infection-prevention-review-packet` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/infection-prevention-review-packet.pdf` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/executive-quality-review-dashboard` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/executive-quality-review-dashboard.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/intake/{finding_id}/export-readiness-status` | enterprise_intake | none (public) | AW-06M; AW-06N; AW-09 | verified member | verified context | object fetched in tenant only (other tenant's id = 404); child rows tenant-filtered | none | anonymous 200 → 401; other tenant's object → 404; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.csv` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi.csv` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi.data-dictionary` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi.data-dictionary.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi.dashboard-spec` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi.dashboard-spec.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.zip` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.readme.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.metadata` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.health` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.executive-summary.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.final-validation` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.production-lock` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.release-notes.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.completion-certificate.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.v1-archive.zip` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/export-readiness-history.powerbi-toolkit.v1-closeout` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/audit-command-center` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.csv` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.powerbi.csv` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.powerbi.data-dictionary` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.powerbi.data-dictionary.pdf` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.toolkit.zip` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/audit-command-center.health` | enterprise_intake | none (public) | AW-09 | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | anonymous 200 → 401; no membership → 403 |
| POST | `/api/enterprise/baseline-aware-score` | enterprise_intake | in handler: require_enterprise_auth | audit row written with no tenant | verified member | verified context | fixed content; audit row recorded in caller's tenant | none | none |
| GET | `/api/enterprise/baseline-review-queue` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines` | enterprise_intake | in handler: require_enterprise_auth | audit row written with no tenant | verified member | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines/upload-image` | enterprise_intake | in handler: require_enterprise_auth | none | verified member | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| GET | `/api/enterprise/vendor-baseline-subscription/baselines` | enterprise_intake | in handler: _require_vendor_baseline_library_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| POST | `/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/approve` | enterprise_intake | in handler: _require_vendor_baseline_approval_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| POST | `/api/enterprise/vendor-baseline-subscription/match` | enterprise_intake | in handler: require_enterprise_auth | no tenant predicate (code review; sweep role-gated) | verified member | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| GET | `/api/enterprise/vendor-baseline-subscription/baselines/{baseline_id}/audit` | enterprise_intake | in handler: _require_vendor_baseline_audit_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | shared vendor baseline library (not tenant-owned) | none | none |
| GET | `/api/enterprise/audit/verify-chain` | enterprise_intake | in handler: _require_governance_packet_access | none | verified member + hospital/enterprise admin | verified context | verification metadata by hash or resource id (not tenant-partitioned; open item R1) | none | none |
| GET | `/api/enterprise/intake/{finding_id}/governance-packet/certificate` | enterprise_intake | in handler: _require_governance_packet_access | no tenant predicate (code review; sweep role-gated) | verified member + hospital/enterprise admin | verified context | rows for the id read in tenant only | none | none |
| GET | `/api/enterprise/audit/events` | enterprise_intake | in handler: require_audit_chain_verify | client tenant_id trusted (code review) | verified member + audit:verify_chain | verified context; query tenant_id is a claim (403 if different) | every query tenant-filtered | none | limited to caller's tenant; foreign tenant claim → 403 |
| GET | `/api/enterprise/audit/events/export.csv` | enterprise_intake | in handler: require_audit_chain_verify | client tenant_id trusted (code review) | verified member + audit:verify_chain | verified context; query tenant_id is a claim (403 if different) | every query tenant-filtered | none | limited to caller's tenant; foreign tenant claim → 403 |
| GET | `/api/enterprise/audit/events/export/verify` | enterprise_intake | in handler: require_audit_chain_verify | none | verified member + audit:verify_chain | verified context | verification metadata by hash or resource id (not tenant-partitioned; open item R1) | none | none |
| GET | `/api/enterprise/audit/events/export/manifest/verify` | enterprise_intake | in handler: require_audit_chain_verify | none | verified member + audit:verify_chain | verified context | verification metadata by hash or resource id (not tenant-partitioned; open item R1) | none | none |
| GET | `/api/enterprise/audit/evidence-bundle` | enterprise_intake | in handler: require_audit_chain_verify | client tenant_id trusted (code review) | verified member + audit:verify_chain | verified context; query tenant_id is a claim (403 if different) | every query tenant-filtered | none | limited to caller's tenant; foreign tenant claim → 403 |
| GET | `/api/enterprise/audit/evidence-bundle/verify` | enterprise_intake | in handler: require_audit_chain_verify | none | verified member + audit:verify_chain | verified context | verification metadata by hash or resource id (not tenant-partitioned; open item R1) | none | none |
| GET | `/api/enterprise/audit/evidence-bundle/download.json` | enterprise_intake | in handler: require_audit_chain_verify | client tenant_id trusted (code review) | verified member + audit:verify_chain | verified context; query tenant_id is a claim (403 if different) | every query tenant-filtered | none | limited to caller's tenant; foreign tenant claim → 403 |
| GET | `/api/enterprise/audit/evidence-bundle/verification-summary` | enterprise_intake | in handler: require_audit_chain_verify | none | verified member + audit:verify_chain | verified context | verification metadata by hash or resource id (not tenant-partitioned; open item R1) | none | none |
| POST | `/api/enterprise/audit/events` | enterprise_intake | in handler: require_audit_chain_verify | none | verified member + audit:verify_chain | verified context | fixed content; audit row recorded in caller's tenant | none | none |
| GET | `/api/enterprise/findings/kpi-summary` | enterprise_intake | none (public) | AW-09 | verified member | verified context | every query tenant-filtered | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/vendor-governance/health` | vendor_governance | none (public) | AW-10 (all-tenant summary in a public probe) | public probe | — | no tenant data returned | none | none |
| POST | `/api/enterprise/vendor-governance/events` | vendor_governance | in handler: require_enterprise_auth | none | verified member | verified context | events scoped to tenant | none | limited to caller's tenant |
| GET | `/api/enterprise/vendor-governance/events` | vendor_governance | none (public) | AW-10 | verified member | verified context | events scoped to tenant | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/vendor-governance/summary` | vendor_governance | none (public) | AW-10 | verified member | verified context | events scoped to tenant | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| GET | `/api/enterprise/vendor-governance/capa-linkage-summary` | vendor_governance | none (public) | AW-10 | verified member | verified context | events scoped to tenant | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
| POST | `/api/enterprise/vendor-governance/events/{event_id}/link-capa` | vendor_governance | in handler: require_enterprise_auth | none | verified member | verified context | events scoped to tenant; other tenant's id = 404 | none | other tenant's object → 404 |
| POST | `/api/enterprise/vendor-governance/events/{event_id}/create-capa` | vendor_governance | in handler: require_enterprise_auth | none | verified member | verified context | events scoped to tenant; other tenant's id = 404 | none | other tenant's object → 404 |
| GET | `/api/enterprise/vendor-governance/powerbi-csv` | vendor_governance | none (public) | AW-10 | verified member | verified context | events scoped to tenant | none | anonymous 200 → 401; limited to caller's tenant; no membership → 403 |
<!-- END BATCH1 MATRIX -->

---

## 8. Unrelated defects corrected while testing

Building real fixtures exposed four pre-existing defects in the enterprise
quality module. They are not tenancy defects; they are listed because they are
changes to application code in this commit, and because without them the
legitimate workflow could not be tested end to end.

| Route | Defect | Correction |
|---|---|---|
| `POST /api/enterprise/intake/{id}/review` | Built its response with `inspection_id`; the model's field is `finding_id`. Every successful review was committed and then answered HTTP 500. | Field name corrected. |
| `POST /api/enterprise/intake/{id}/capa` (two return paths) | Same field-name mistake: CAPA created, then HTTP 500. | Field name corrected. |
| `GET /api/enterprise/capas` | The schema file defined `EnterpriseCapaListItem` twice, so the list response rejected its own items: HTTP 500 whenever a CAPA existed. | Duplicate class removed. |

---

## 9. Remaining open findings

**From the application-wide review, unchanged by this batch**

| ID | Risk | Routes | Status |
|---|---|---|---|
| AW-09 (aggregate counters) | Owner decision | 3 | Documented in code as public; no recorded policy decision. Two of them also return invented fallback totals when the tables are empty, which is an integrity question outside tenancy. |
| AW-01 | High | 19 | Open |
| AW-02 | High | 60 observed, 176 by pattern | Open |
| AW-03 | High | 132 | Open |
| AW-04 | High | 38 | Open |
| AW-05 | High | 373 | Open |
| AW-06M | High | 141 | Open |
| AW-06N | Medium | 420 | Open |
| AW-07 | High | 20 by pattern | Open |
| AW-08 | High | 3 confirmed, leads unconfirmed | Open |

**Residual items inside the three remediated modules**

| ID | Item | Risk |
|---|---|---|
| R1 | Five verification routes are not partitioned by tenant: `GET /audit/verify-chain` (by resource id) and four hash-verification routes. They require a verified hospital or enterprise administrator and return verification metadata only, but chain verification discloses whether another tenant's resource has audit events and how many. Partitioning it needs a decision on the hash chain, which is per resource, not per tenant. | Low |
| R2 | The vendor baseline library (`enterprise_vendor_baseline_subscriptions`, 6 routes) has no tenant ownership: it is one shared library, and one hospital administrator's approval applies to everyone. Authenticated, not partitioned. Needs a product decision. | Design question |
| R3 | Vendor governance events are still held in process memory: lost on restart, different on each replica. | Durability, not isolation |
| R4 | CAPAs written before this change have no owner and are now visible to nobody. Assigning them is a data decision. The register is still a separate SQLite file; on a PostgreSQL deployment it lives on the application container's disk. | Data decision |
| R5 | Audit rows written by other modules without a tenant take the column default `default-tenant` and are visible to members of that tenant. Same root as AW-06. | Medium |
| R6 | CAPAs created by workflow engines (Apollo, Maestro, Forge, Catalyst, quality dashboard) are stamped with the tenant their calling route resolved. Those routes are still open under AW-05, so a user with no single membership can still mis-attribute one. | Open under AW-05 |
| R7 | Actor and role labels on some audit events (`X-LumenAI-Actor`, `X-LumenAI-Role`, `tenant_name`) are still taken from the client. Attribution integrity, not tenancy. | Low |
| R8 | The shared development token (rejected in production) trusts the tenant header. Unchanged. | Known |
| R9 | Three POST routes validate the body before authenticating, so an anonymous caller gets 422 rather than 401. No data is involved. | Info |
| R10 | Refused requests are not audited. | Low |

---

## 10. Verification

Recorded in the PR description for the commit that contains this document,
because a document cannot name its own commit.

---

## 11. Independent review recommendation

Ready for a non-author security review and a contract sign-off. Not ready to
close AW-09, AW-10 or AW-11 until that review has happened.

Suggested checks for the reviewer:

1. Confirm that no handler in `enterprise_intake.py` queries a tenant-owned
   model except through `_tq` / `_tget`, and that the list of tenant-owned
   models is complete.
2. Reproduce one case from each finding against a deployed non-production
   instance, with identities the reviewer creates.
3. Decide the open policy questions: the three public counters, R1 (chain
   verification), R2 (shared baseline library), R4 (ownerless CAPAs).
4. Sign off, or amend, the contract changes in section 4, in particular the
   removal of the `bonsecours` default, the empty probe summaries and the demo
   events.
5. Check production for evidence that the previously anonymous routes were
   accessed. This review did not examine production.
