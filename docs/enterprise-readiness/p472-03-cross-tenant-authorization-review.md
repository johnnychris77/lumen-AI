# P472-03 — Cross-Tenant Authorization: Contract Review and Authorization Matrix

**Scope:** every route in `backend/app/routes/regulatory.py`, `predictions.py`, `benchmarking.py` and `vendor_intelligence.py` (39 routes).
**Baseline:** PR #181 at `be88e4a8d899bab8cec378f495cfab25112b3e2c`.
**Disposition:** HOLD / NO-GO. This records an implementation and its author's tests. It is not an approval and does not close P472-03.

## 1. Finding

All 37 tenant-scoped routes in these modules called `require_enterprise_auth(request)`, which authenticates the caller and verifies membership of the caller's *own* tenant. They then discarded the result and used a `tenant_id` taken from the query string or request body. A verified member of tenant A could read tenant B's aggregates and write records into tenant B by naming B in the request, with no tenant header.

Thirteen cases were demonstrated at `be88e4a` (11 reads, 2 writes). The review below found the same defect in all 37 routes, and two further consequences:

- **GET routes wrote into the named tenant.** The benchmark aggregation routes persist snapshot rows (`hospital_benchmarks`, `vendor_benchmarks`, `enterprise_rollups`), so a read request for tenant B also wrote rows under B.
- **The prediction audit trail recorded a client-chosen tenant and role.** Each prediction read wrote an `audit_logs` row with the tenant from the query and the role from the `X-LumenAI-Role` header.

## 2. Contract before the change

| Module | Tenant source | Default when omitted | Auth call |
|---|---|---|---|
| Regulatory (8 tenant-scoped routes) | `tenant_id` query, or `tenant_id` in the body | none; required (HTTP 422) | `require_enterprise_auth(request)`, result unused |
| Predictions (12) | `tenant_id` query, or body on `POST /outcomes` | none; required (HTTP 422) | same |
| Benchmarks (13) | `tenant_id` query, or body on POST | `demo-tenant` (query), `default-tenant` (body) | same |
| Vendor intelligence (4) | `tenant_id` query | none; required (HTTP 422) | same |

`GET /api/regulatory/standards` and `GET /api/regulatory/standards/mapping` serve a static catalogue. They take no tenant and are unchanged.

Callers found in the repository:

| Caller | What it sent |
|---|---|
| `RegulatoryComplianceDashboard.tsx` | `tenant_id` from `localStorage`, falling back to the literal `demo-tenant` |
| `PredictiveAnalyticsDashboard.tsx` | the literal `default-tenant` |
| `EnterpriseBenchmarkDashboard.tsx` | no tenant, relying on the server default `demo-tenant` |
| Four backend test suites (395 tests) | the shared development token, with the tenant only in the query or body |

No frontend caller of the vendor-intelligence routes exists.

## 3. Rule now enforced

Implemented once in `backend/app/auth/tenant_scope.py` (`authorized_tenant`) and called inline in every tenant-scoped handler:

```python
tenant_id = authorized_tenant(require_enterprise_auth(request, db=db), tenant_id)
```

1. **The tenant is the verified auth context's tenant.** For a signed user token this is a tenant the user is an enabled member of: the `X-Tenant-Id` header when one is sent and membership verifies, otherwise the user's only membership. This is the existing infrastructure, unchanged.
2. **A `tenant_id` in the query or body is a claim, not a selector.** If it names any other tenant the request is refused with HTTP 403. It is never rewritten to the caller's tenant.
3. **A request that names no tenant acts in the caller's verified tenant.**
4. **A user with several memberships selects a tenant with `X-Tenant-Id`.** A `tenant_id` claim must then agree. With no header such a user is refused, as before.
5. **Missing or invalid authentication fails closed** (401 or 403) before any tenant data is read.
6. **One refusal message for every denied claim**, so a response does not reveal whether a tenant exists.
7. **No privileged cross-tenant path was added.** Platform administrators get no bypass on these routes.

Authorization happens before the tier check, before any query, and before any write, so refused requests persist nothing — including snapshots and audit rows.

## 4. Compatibility

| Request | Before | Now | Classification |
|---|---|---|---|
| Names the caller's own tenant | 200 | 200, same response | Backward-compatible |
| Names no tenant, regulatory / predictions / vendor intelligence | 422 | 200 for the caller's tenant | Backward-compatible (relaxation) |
| Names no tenant, benchmarks | 200 with `demo-tenant` (or `default-tenant`) data | 200 with the caller's own tenant's data | **Contract change** |
| Names a tenant the caller is not acting in, including `demo-tenant` and `default-tenant` | 200 with that tenant's data | 403 | **Contract change (the fix)** |
| Body omits `tenant_id` on the POST routes | 422, or `default-tenant` | 200 for the caller's tenant | Backward-compatible (relaxation) |
| Prediction audit row | tenant from query, role from header | tenant, actor and role from the verified context | Behaviour change, no API change |

Response schemas are unchanged.

### Required client migration

A client that sends a hardcoded tenant now receives 403. It must either stop sending `tenant_id` or send the caller's real tenant. The three frontend callers were migrated in the same commit to send no tenant. They no longer read `tenant_id` from `localStorage` or hold a literal tenant.

Effect on users: these three dashboards previously showed `demo-tenant` or `default-tenant` data to every signed-in user. They now show the signed-in user's own tenant. A tenant with no records of its own sees whatever the analytics services return for an empty tenant, which for several of them is seeded demo content (a limitation recorded under P4.7.1, not changed here).

External API clients that pass a hardcoded tenant are not known and could not be surveyed from the repository.

### Shared development token

The shared development token is an existing non-production credential (rejected when `ENVIRONMENT=production`). Its tenant is whatever `X-Tenant-Id` says, with no membership check. P472-03 neither removes nor widens it: a tenant named only in the query or body selects nothing. The four backend suites that use it now state their tenant in the header through `backend/tests/tenant_header_client.py`; no assertion in them changed.

## 5. Authorization matrix

"Verified context" means rule 1 above. Every row was tested for: owner access with and without a claim, five tenant-substitution attacks, nine unverified identities, multi-tenant membership, three hardcoded tenants, and non-disclosure of another tenant's records.

### Regulatory — `/api/regulatory`

| Route | Tenant source before | Tenant source now | Reads | Writes |
|---|---|---|---|---|
| `GET /readiness` | query | verified context | `cv_inference_records`, provenance | — |
| `GET /readiness/findings` | query | verified context | `cv_inference_records`, provenance | — |
| `GET /standards` | none | none (authentication only) | static catalogue | — |
| `GET /standards/mapping` | none | none (authentication only) | static catalogue | — |
| `POST /audit-package` | body | verified context | `cv_inference_records` | `regulatory_audit_packages` |
| `POST /audit-package/pdf` | body | verified context | `cv_inference_records` | `regulatory_audit_packages` |
| `GET /audit-packages` | query | verified context | `regulatory_audit_packages` | — |
| `GET /fda-submissions` | query | verified context | `fda_submission_trackers` | — |
| `POST /fda-submissions` | body | verified context | — | `fda_submission_trackers` |
| `GET /dashboard` | query | verified context | `cv_inference_records`, CAPA, `fda_submission_trackers` | — |

### Predictions — `/api/predictions`

Every prediction read also writes one `audit_logs` row.

| Route | Tenant source before | Tenant source now | Reads | Writes |
|---|---|---|---|---|
| `GET /failures` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /failures/{instrument_id}` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /contamination` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /contamination/{instrument_id}` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /repairs` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /repairs/{instrument_id}` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /recall-risk` | query | verified context | recall events, shared defect signals | `audit_logs` |
| `GET /recall-risk/{instrument_category}` | query | verified context | recall events, shared defect signals | `audit_logs` |
| `GET /tray-risk` | query | verified context | `cv_inference_records` | `audit_logs` |
| `GET /dashboard` | query | verified context | `cv_inference_records`, recall events, shared defect signals | `audit_logs` |
| `POST /outcomes` | body | verified context | — | `prediction_outcomes` |
| `GET /accuracy` | query | verified context | `prediction_outcomes` | — |

Recall events and shared defect signals are cross-hospital, anonymised data by design; they are not tenant records and were not changed.

### Benchmarks — `/api/enterprise/benchmarks`

| Route | Tenant source before | Tenant source now | Reads | Writes |
|---|---|---|---|---|
| `POST /hospitals` | body, default `default-tenant` | verified context | `cv_inference_records`, `hospital_benchmarks` | `hospital_benchmarks` |
| `GET /hospitals/{hospital_id}` | query, default `demo-tenant` | verified context | same | `hospital_benchmarks` |
| `GET /hospitals` | query, default `demo-tenant` | verified context | same | `hospital_benchmarks` |
| `POST /vendors` | body, default `default-tenant` | verified context | vendors, findings, CAPA, baselines, `vendor_benchmarks` | `vendor_benchmarks` |
| `GET /vendors` | query, default `demo-tenant` | verified context | same | `vendor_benchmarks` |
| `POST /rollup` | body, default `default-tenant` | verified context | all of the above, `enterprise_rollups` | all three snapshot tables |
| `GET /rollup` | query, default `demo-tenant` | verified context | same | all three snapshot tables |
| `GET /executive-dashboard` | query, default `demo-tenant` | verified context | same, `benchmark_trend_points` | all three snapshot tables |
| `GET /trends/{subject_type}/{subject_id}/{metric_name}` | query, default `demo-tenant` | verified context | `benchmark_trend_points` | — |
| `POST /reports/generate` | body, default `default-tenant` | verified context | rollup inputs, `board_reports` | `board_reports`, snapshots; publish updates `board_reports` |
| `GET /reports/{report_type}` | query, default `demo-tenant` | verified context | `board_reports` | — |
| `GET /reports/{report_type}/{period_label}` | query, default `demo-tenant` | verified context | `board_reports` | `board_reports` when generated on demand |
| `GET /kpi-summary` | query, default `demo-tenant` | verified context | rollup inputs | all three snapshot tables |

### Vendor intelligence — `/api/vendor-intelligence`

| Route | Tenant source before | Tenant source now | Reads | Writes |
|---|---|---|---|---|
| `GET /vendors` | query | verified context | `vendor_benchmarks` | — |
| `GET /vendors/{vendor_id}` | query | verified context | `vendor_benchmarks` | — |
| `GET /vendors/{vendor_id}/scorecard` | query | verified context | `vendor_benchmarks` | — |
| `GET /vendors/{vendor_id}/trends` | query | verified context | derived trend data | — |

## 6. Background and derived processing

None of these four modules starts a background task or scheduled job from a request. What outlives a request is what it persists as a side effect: benchmark snapshots written by GET routes, generated reports and audit packages, and the prediction access audit trail. All of these now use the verified tenant, and a refused request writes none of them. The asynchronous CV inference job is outside these modules and is covered by `backend/tests/test_p472_cross_tenant_api.py`.

## 7. Verification

`backend/tests/test_p472_03_tenant_authorization.py` covers all 39 routes; its endpoint table is checked against the mounted application. The 13 cases in `backend/tests/test_p472_cross_tenant_api.py` that were strict `xfail` at `be88e4a` are ordinary passing tests. Disabling the tenant check in `authorized_tenant` makes 348 of these tests fail.

Test counts, suite results and the commit SHA are recorded in the PR #181 description, which is authoritative for the exact commit.

## 8. Not addressed

- **Other route modules.** A scan found 40 more handlers in 13 files outside these four modules that take a `tenant_id` path or query parameter directly (for example `accreditation.py`, `p20_network_intelligence.py`, `intelligence.py`, `manufacturer_intelligence.py`). Body-borne tenants were not counted. None of them was reviewed here; some may be correctly protected by other guards.
- **The header-trusting `resolve_tenant` dependency** (about 180 route dependencies in 46 files) and the unauthenticated `POST /baseline-ranking/audit-evidence` remain as recorded under P472-03.
- **The shared development token** still accepts any `X-Tenant-Id` outside production.
- **`RegulatoryComplianceDashboard.tsx` still falls back to the literal `dev-token`** when no session token is stored. It predates this change and is rejected in production, but it should be removed.
- **Refused requests are not audited.** A denied cross-tenant attempt returns 403 and leaves no audit event.
- **Client-supplied attribution fields** (`recorded_by`, `generated_by`) are stored as sent.
- **No independent review.** These are the author's tests.
