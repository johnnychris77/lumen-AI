# Tenant Isolation Test Matrix

Cross-tenant access expectations and where they are enforced/tested. Isolation
must hold with the **corrected** membership loader.

## Matrix

`A`, `B` are distinct tenants. Actor is a member of `A` only (unless noted).

| Actor | Action | Target | Expected | Enforced by / test |
|-------|--------|--------|----------|--------------------|
| Member of A | read | A | allow | `resolve_verified_tenant` (Case B) · `test_history_inspection_results` |
| Member of A | write | A | allow per role | inspection role gate · `test_inspection_role_permissions` |
| Member of A | read | B | **deny 403** | `verified_tenant_ids` mismatch (Case E) · `test_cross_hospital_tenant_isolation_security` |
| Member of A | write | B | **deny 403** | same |
| Member of A | export | B | **deny 403** | `_scoped_rows` fail-closed · `test_history_inspection_results` |
| Member of A | read B via `X-Tenant-Id: B` header | B | **deny 403** | `require_enabled_tenant_membership` / Case G · `test_header_role_privilege_escalation`, `test_tenant_api_boundaries` |
| Member of A | read B via body/query tenant | B | **deny 403** | Case G · `test_tenant_resolution_contract::test_case_G` |
| Multi-tenant (A,B) | read, no selection | — | **deny 403** (explicit selection required) | Case C · `test_tenant_resolution_contract::test_case_C` |
| Zero-tenant user | any tenant-scoped read | — | **deny 403** | Case D · `test_tenant_resolution_contract::test_case_D` |
| Disabled membership in A | read | A | **deny 403** | Case F (`is_enabled` filter) · `test_tenant_resolution_contract::test_case_F`, `test_analytics_kpi_hardening` |
| Platform admin (`role==admin`) | read | any/all | allow | Case A · `test_directive_002_tenant_context` |
| OIDC token, tenant claim = A | read | B | **deny** | `test_oidc_tenant_membership_enforcement`, `test_oidc_tenant_claim_enforcement` |

## Roles covered

`operator`, `spd_manager`, `viewer`, `tenant_admin` (per-tenant), `vendor_user`,
platform `admin`. Vendor/manufacturer baseline scoping is covered by the enterprise
path membership check and `test_alerts_tenant_isolation` / baseline suites.

## Verification status

All rows above are backed by passing tests in the full SQLite suite (3760 passed,
0 failed on a fresh DB).
The corrected loader was run against the entire suite and the isolation/privilege
suites specifically (`test_cross_hospital_tenant_isolation_security`,
`test_header_role_privilege_escalation`, `test_oidc_tenant_membership_enforcement`,
`test_directive_002_tenant_context`, `test_tenant_api_boundaries`) — all green.

## Forgery regression coverage

Explicit forged-tenant tests live in `test_tenant_resolution_contract.py` (Case G:
header/query/body substitution) and `test_header_role_privilege_escalation.py`
(role/tenant header spoofing). A client value never confers authority.
