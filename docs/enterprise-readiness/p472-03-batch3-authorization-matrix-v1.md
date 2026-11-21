# P472-03 — Batch 3 Authorization Matrix (v1)

**Program:** P472-03 Enterprise Tenant Isolation · **PR #181 (DRAFT)**
Scope: the surfaces changed in Batch 3. For the whole-application matrix see
`p472-03-application-wide-authorization-matrix.md` (regenerated per batch by the sweep). This records
the authorization control **now enforced**; it is evidence for independent review, not a sign-off.

## Legend
- **Identity source** — how the acting manufacturer/tenant identity is determined. `require_manufacturer_auth`
  resolves it from a verified, enabled `ManufacturerMembership`; `resolve_tenant` resolves the tenant from a
  verified `TenantMembership` (fail-closed 403).
- **Claim handling** — what happens to an organization/tenant named in a header or query.

### AW-07 — manufacturer / repair-partner portals
Consumers of `require_manufacturer_auth` (routes in `industry_collaboration.py` — 8 manufacturer-portal +
6 repair-partner-portal, `or_connect_vendor_portal.py` — 3, `manufacturer_portal.py` — 3):

| Surface | Identity source (after Batch 3) | Claim handling | Finding | Verified by |
|---|---|---|---|---|
| all `require_manufacturer_auth` routes | verified `ManufacturerMembership` (enabled) | `X-Manufacturer-ID` honoured only for a verified member; any other org → 403; no header → sole membership; disabled/absent → 403 | AW-07 | `test_p472_03_aw07_manufacturer_identity.py` (7) + converted exploit test + 63 portal tests + PG16 migration up/down |

### AW-04 — accreditation module (completes the Day-3 `programs` fix)

| Endpoint | Method | Identity source | Claim handling | Finding | Verified by |
|---|---|---|---|---|---|
| `/api/accreditation/evidence-items` | GET | `resolve_tenant` (verified) | `tenant_id` query inert | AW-04 | probe + accreditation suite |
| `/api/accreditation/readiness` | GET | `resolve_tenant` | `tenant_id` query inert | AW-04 | probe + accreditation suite |
| `/api/accreditation/readiness/trend` | GET | `resolve_tenant` | `tenant_id` query inert | AW-04 | probe + accreditation suite |
| `/api/accreditation/survey-evidence` | GET | `resolve_tenant` | `tenant_id` query inert | AW-04 | probe + accreditation suite |
| `/api/accreditation/certifications` | GET | `resolve_tenant` | `tenant_id` query inert (no list-all) | AW-08a/AW-04 | probe + accreditation suite |
| `/api/accreditation/programs` (GET, PATCH) | — | `resolve_tenant` | inert / object-ownership 404 | AW-08a/AW-04 (Day 3) | Day-3 evidence |

## Not yet remediated (tracked in the Batch 3 remediation review §3)
The remaining AW-04 routes outside accreditation (network-intelligence 10, enterprise 5, intelligence 5,
commercial 4, olympus 3, genesis-ai 2, billing 1, infinity 1, growth 1) and the AW-03 (118) / AW-06M (122) /
AW-06N (28) classes across ~18 modules are **analyzed with a roadmap but not remediated** in Batch 3. Their
register entries and strict-xfail class guards are unchanged and correctly still reproduce.

## What this matrix does NOT assert
It does not close any finding (AW-07 and the accreditation AW-04 routes remain OPEN pending independent
review), nor authorize release. Enterprise release remains **HOLD / NO-GO**.
