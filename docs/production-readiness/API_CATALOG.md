# LumenAI — API Catalog

**1859 endpoint decorators across 193 route files, mounted at 91 distinct `/api/*` prefixes** (plus a handful of non-prefixed root paths: `/health`, `/login`, device-key routes). Exhaustively documenting every one of the 1859 endpoints individually is not the useful level of detail for a production-readiness review of a codebase this size — this catalog instead documents every *router* (the real unit of ownership in this codebase, matching one specialist/module each), with representative request/response/auth pattern per group, and calls out every genuine exception (undocumented auth, unregistered routers, versioning gaps) by name.

## Methodology

For each router: purpose (from the module's docstring or its owning specialist), auth pattern (does it use `require_tenant_roles` — the tenant-scoped RBAC dependency — or the simpler `get_current_user`, or neither), and endpoint count. "Consumers" = the frontend workspace that calls it, from `main.tsx`'s route list.

## Authentication/authorization pattern (applies to nearly all routes)

The overwhelming majority of routes (635 call sites) use `Depends(require_tenant_roles(*roles))`, which:
1. Resolves caller identity from a JWT or recognized dev-token in the `Authorization` header (never from a client-supplied header).
2. Resolves `tenant_id`/`tenant_name` from `x-tenant-id`/`x-tenant-name` headers.
3. Requires a matching, enabled `TenantMembership` row for that `(user, tenant)` pair — 403 otherwise.
4. Requires the resolved role to be in the route's allowed-roles list — 403 otherwise.

**18 route files use the simpler `get_current_user` dependency instead**, which resolves identity the same way but does **not** independently verify tenant membership or auto-scope queries — the route author must do that manually. This is not necessarily wrong (some of these are legitimately tenant-agnostic, e.g. platform admin), but it is a manual, unenforced discipline rather than a structural guarantee — see Technical Debt Register TD-11 for the specific files.

**No global API versioning scheme exists.** No route file uses a `/v1/`, `/v2/` style prefix except Nexus's `/api/v1/*` gateway routes (a deliberate exception, documented as the external-facing integration surface). Everything else is unversioned — a breaking change to any endpoint's request/response shape has no migration path today (Technical Debt Register TD-12). **No endpoint is marked deprecated** via any convention (no `deprecated=True` on any route decorator found) — deprecation status in this codebase currently lives only in comments/docstrings, not in the OpenAPI schema.

## Top 25 routers by endpoint count

| Prefix | File | Endpoints | Auth | Consumer (frontend) |
|---|---|---|---|---|
| `/api/enterprise` | `enterprise_intake.py` | 77 | `require_tenant_roles` | `/enterprise` |
| `/api/guardianx` | `guardianx_assurance.py` | 44 | `require_tenant_roles` | `/ai-assurance` |
| `/api/beacon` | `industry_collaboration.py` | 44 | `require_tenant_roles` | (Beacon has no dedicated nav entry — orphan, see Architecture Inventory §1) |
| `/api/infinity` | `infinity_platform.py` | 40 | `require_tenant_roles` | `/developers`, `/marketplace` |
| `/api/steward` | `governed_action.py` | 36 | `require_tenant_roles` | `/steward` |
| `/api/network-intelligence` | `p20_network_intelligence.py` | 34 | `require_tenant_roles` | `/network-intelligence` |
| `/api/olympus` | `olympus_network.py` | 33 | `require_tenant_roles` | `/network` |
| `/api/apollo` | `apollo_quality.py` | 32 | `require_tenant_roles` | `/quality` |
| `/api/quality-guardian` | `quality_guardian.py` | 30 | `require_tenant_roles` | `/quality-dashboard` |
| `/api/oracle` | `oracle_discovery.py` | 30 | `require_tenant_roles` | `/oracle` |
| `/api/horizon` | `federated_horizon.py` | 30 | `require_tenant_roles` | (no dedicated nav entry — orphan) |
| `/api/forge` | `workflow_forge.py` | 30 | `require_tenant_roles` | `/workflow-builder` |
| `/api/sage` | `sage_education.py` | 29 | `require_tenant_roles` | `/sage`, `/my-learning` |
| `/api/platform` | `platform.py` | 28 | `require_tenant_roles` | `/launcher`, `/platform-admin` |
| `/api/athena` | `athena_knowledge.py` | 28 | `require_tenant_roles` | `/knowledge-memory` |
| `/api/accreditation` | `accreditation.py` | 28 | `require_tenant_roles` | `/accreditation` |
| `/api/mobile` | `mobile.py` | 27 | `require_tenant_roles` | (mobile app, not the web frontend) |
| `/api/orbit` | `orbit_readiness.py` | 26 | `require_tenant_roles` | `/surgical-readiness` |
| `/api/nexus` | `nexus_integration.py` | 26 | `require_tenant_roles` | `/integrations` |
| `/api/atlas` | `atlas_enterprise.py` | 26 | `require_tenant_roles` | `/atlas` |
| `/api/phoenix` | `phoenix_intelligence.py` | 25 | `require_tenant_roles` | `/phoenix` |
| `/api/pulse` | `pulse_operations.py` | 23 | `require_tenant_roles` | `/pulse` |
| `/api/council` | `council_leadership.py` | 23 | `require_tenant_roles` | `/council` |
| `/api/sentinel` | `sentinel_orchestration.py` | 21 | `require_tenant_roles` | `/sentinel` |
| `/api/operations` | `p22_operations.py` | 21 | `require_tenant_roles` | `/operations` |

All 25 use the tenant-scoped RBAC dependency consistently — no auth gap found in the highest-traffic routers.

## Router groups by specialist (full list, counts approximate)

| Group | Routers | Total endpoints (approx.) |
|---|---|---|
| Core inspection/quality/CAPA | `enterprise_intake`, `quality_guardian`, `capa*`, `findings*`, `inspection*` | 200+ |
| AI Specialists (25, see AI_SPECIALIST_CATALOG) | `council`, `maestro`, `oracle`, `governed_action` (Steward), `vulcan_reliability`, `sage_education`, `veritas_evidence`, `sentinelx_risk`, `apollo_quality`, `athena_knowledge`, `phoenix_intelligence`, `guardianx_assurance`, `genesis_ai_intelligence_cloud`, `nova_agent_platform`, `olympus_network`, `infinity_platform`, `industry_collaboration`, `workflow_forge`, `pulse_operations`, `catalyst_copilot`, `orbit_readiness`, `vanguard_intelligence` | ~550 |
| Legacy P-number platform sprints | `p20_network_intelligence`, `quality_intelligence` (P21), `p22_operations`, `global_intelligence` (P23), `p24_standards`, `p25_infrastructure` | ~120 |
| Tenant/billing/commercial | `tenant*`, `billing*`, `commercial*`, `growth*` | ~80 |
| Governance/reporting | `governance_approvals`, `governance_reconciliation`, `leadership_packet*`, `account_review*`, `saved_report*` | ~90 |
| Nexus/integrations | `nexus_integration`, `nexus_api_gateway`, `integrations`, `mobile` | ~90 |
| **Unregistered (dead) routers** | 16 files, see Dependency Map §6 | ~69 (unreachable) |

## Request/response conventions (representative, not per-endpoint)

Every specialist route file follows the same shape (established once by Council and repeated ~20 times since): `POST` endpoints take a plain `dict` body parsed manually (not a Pydantic request model in most specialist routes — see Technical Debt Register TD-13), raise `HTTPException(422, ...)` on a service-layer `ValueError`, and return the service's own `to_dict()` shape. `GET` list endpoints take query-string filters and return `{"items_key": [...]}`. This consistency is a real strength — a developer who has read one specialist's route file can predict the shape of any other's.

## Consumers not reachable from any nav item

Per the frontend inventory, ~40 of 105 authenticated routes have no `AppShell` nav entry — including several specialist workspaces mentioned above (Beacon, Horizon). These endpoints are real and registered (unlike the dead routers in §6 of the Dependency Map) but are only reachable by a user who knows the direct URL. See Architecture Inventory §1 and Technical Debt Register TD-04.
