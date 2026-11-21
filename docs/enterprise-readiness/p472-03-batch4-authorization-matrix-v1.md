# P472-03 — Batch 4 Authorization Matrix (v1)

Controls in force on the route groups changed by Batch 4 (Issue #186). The full per-endpoint matrix is
generated from the sweep: `p472-03-application-wide-authorization-matrix.md` / `.csv` (1,912 routes).
Status of every row: **remediated, pending independent review** (not closed).

## Tenant resolution rule (all groups)
| Request | Result |
|---|---|
| Names its own tenant in `X-Tenant-Id` **or** `X-LumenAI-Tenant-Id` | served in that tenant |
| Names a tenant it is not an enabled member of | **403** |
| Sends two tenant headers that disagree | **403** |
| Names no tenant, exactly one membership | served in that tenant |
| Names no tenant, several memberships | **403** (must select) |
| No membership | **403** |
| `tenant_id` in query / path / body naming another tenant | **403** (claim, never a selector) |
| Development token (non-production only) / platform administrator (PA-1) | unchanged documented exception, logged when cross-tenant |

## Route groups
| Group | Modules (routes pinned) | Auth | Tenant source after Batch 4 | Commit |
|---|---|---|---|---|
| AW-03/06M header re-read | mobile, integrations, standards, infrastructure, global/quality intelligence, quality twin, patient safety, network benchmark, baseline library, instrument registry, industry dashboard, recall signals (142) + OR-Connect vendor portal | `require_enterprise_auth` | `request_tenant(ctx, request)` | `5adde8d` |
| AW-04 claims (AuthContext) | billing, intelligence, intelligence consent, ranking | `require_enterprise_auth` | `request_tenant(ctx, request, claim)`; ranking finding lookups tenant-predicated | `76d7fc3` |
| AW-04 claims (principal) | commercial, growth, accreditation (writes + reads), p20 network intelligence | `require_roles` | `principal_claim_tenant` / `verified_request_tenant(…, claim)`; platform-wide views PA-1 only | `76d7fc3` |
| AW-04 claims (membership) | olympus, genesis research opt-in, infinity partner licences | `require_tenant_roles` | `refuse_other_tenants(membership tenant, claim)` | `76d7fc3` |
| Shared dependency | `require_tenant_roles` (562 call sites, 58 modules) | bearer + tenant role | either header verified; disagreeing → 403; none → sole membership | `24ec88d` |
| AW-06N | pre-sterilization command centre, CIOS, knowledge graph, agents, decision engine, analytics (46) | `require_roles` | `principal_tenant(current_user, request)`; analytics also requires membership for a named tenant | `cea6d7f` |
| Audit attribution | GuardianX evidence | `require_tenant_roles` | audit event under the verified tenant | `4308443` |
| AW-08 object level | accreditation programs, vendor analytics, GuardianX replay | various | tenant-predicated lookups (Day 3); re-verified | `c826fcc` |

Pinned-remediated coverage (a finding reappearing on any of these routes fails the suite): **567 routes**.

## Not covered by this matrix
`GET /api/genesis-ai/manufacturer-updates` (AW-04 publisher filter, open) and the GD-6/GD-7 leads — see
`p472-03-batch4-remediation-review-v1.md` §5.
