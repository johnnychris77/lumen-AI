# P472-03 — Day 3: Authorization Coverage Matrix (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)**
Scope: the endpoints/services touched by Day 3 remediation. For the whole-application matrix see
`p472-03-application-wide-authorization-matrix.md`. This matrix records the tenant-authorization
control **now enforced** on each surface and how it is verified. It is evidence for independent
review, **not** a sign-off.

## Legend
- **Tenant source** — where the acting tenant is determined. `resolve_tenant` / `principal_tenant`
  resolve the tenant from **verified membership** (the `X-Tenant-Id` header is honoured only when the
  caller is an enabled member; fail-closed 403). `require_tenant_roles` asserts membership then
  exposes the verified tenant.
- **Claim handling** — what happens to a tenant named in a query/body/path field.
- **Object check** — per-object ownership enforcement where the route mutates/reads one record.

| Endpoint / service | Method | Role gate | Tenant source (after Day 3) | Claim handling | Object check | Finding | Verified by |
|---|---|---|---|---|---|---|---|
| `/api/analytics/vendors` (+ `export.json/.csv/.xlsx/.bundle.zip`, `{vendor}/scorecard.json/.pdf`) | GET | `require_roles(admin, spd_manager, vendor_user[, viewer])` | `resolve_tenant` (verified) | n/a (no tenant field) | aggregates only `_tenant_inspections(db, verified)` | AW-08b | probe + `test_p472_03_batch2_remediation` owner/refusal params |
| `/api/accreditation/programs` | GET | `require_roles(admin, executive, spd_manager)` | `resolve_tenant` (verified) | `tenant_id` query is **inert** (no widen, no foreign select) | filter `tenant_id == verified` | AW-08a / AW-04 | probe + batch2 params + XPASS tripwires |
| `/api/accreditation/programs/{id}` | PATCH | `require_roles(admin, executive, spd_manager)` | `resolve_tenant` (verified) | n/a | ownership: foreign → non-disclosing **404** | AW-08a | batch2 refusal params + P19 smoke |
| `guardianx_audit_replay_service.replay_inspection` | (service) | via route `require_tenant_roles(*ALL)` | caller's `current_user["tenant_id"]` (membership-verified) | n/a | `Inspection.tenant_id == verified` else 404 | AW-08c (defence-in-depth) | finding test (now secure) + replay smoke |
| `app.auth.tenant_scope.principal_tenant` (admin/dev branch) | (resolver) | — | **unchanged** governance rule | — | privileged cross-tenant now **logged** (`lumenai.security.tenant`) | PA-1 (partial) | `test_privileged_cross_tenant_access_is_logged` + negative test |
| manufacturer surface (`require_manufacturer_auth`, 7 routes in `industry_collaboration.py`) | GET | enterprise auth | **UNRESOLVED** — identity from `X-Manufacturer-ID` header | **no principal↔manufacturer binding** | — | AW-07 | **BLOCKED** (architecture); reproduced, not fixed |

## Census note
Adding `Depends(resolve_tenant)` to the 7 vendor-analytics routes and 2 accreditation routes moved
the verified-resolver dependency census in `test_p472_03_batch2_remediation::
test_the_route_table_is_the_mounted_application` from **181 → 190** (handler count unchanged at 497).
Those 9 routes are now exercised by the full adversarial parametrization (owner-served **and**
refusal) for every synthetic identity class (member, non-member, multi-membership, split/forged
headers).

## What this matrix does NOT assert
- It does not close AW-04, AW-08a, AW-08b or AW-08c (their strict-xfail tripwires remain red by
  design — closure is an independent-review action).
- It does not resolve AW-07 (no manufacturer-membership model exists) or PA-1's access decision
  (governance-owned).
- It is not a release authorization. Enterprise release remains **HOLD / NO-GO**.
