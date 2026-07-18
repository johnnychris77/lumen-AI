# Tenant Migration Inventory (LPZ-DIR-002, Phase 4)

Routes whose tenant scope must migrate to the verified resolver
(`app.security.tenant_context.resolve_verified_tenant`).

## MIGRATED (this increment)

| Route | Method | Prior tenant source | Auth dep | Data store | R/W | Migration | Test |
|---|---|---|---|---|---|---|---|
| /api/history | GET | `getattr(user,tenant_id)`→None→**unfiltered** | require_roles | inspections | R | **DONE** (fail-closed resolver) | test_directive_002_tenant_context |
| /api/history/summary | GET | same | require_roles | inspections | R | **DONE** | same |
| /api/history/export.json/.csv/.xlsx/.bundle.zip | GET | same | require_roles | inspections | R (export) | **DONE** | same |

## MIGRATION PENDING (41 routes, shared pattern) — DEFERRED to increment 2+

All of the following read tenant as
`getattr(current_user, "tenant_id", None) or get_request_tenant_id(request)`.
**Risk profile (shared):** with this increment the left operand is now a
*verified* `active_tenant_id` for any JWT user with a membership, so the
header is no longer the sole source for those users; but a principal with
**no** verified membership (e.g. a dev/admin token, or a JWT user with no
membership row) still falls through to the header default
`default-tenant`. Each route must be individually converted to
`resolve_verified_tenant` and given cross-tenant negative tests. Owner:
Platform Security (Pilot Zero WS1).

Routes (method varies R/W per handler; classify during migration):
advisory_pilot, ai_clinical_review, anatomy_intelligence,
annotation_database, apollo_quality, atlas_enterprise,
baseline_image_library, capture, catalyst_copilot, clinical_readiness,
dataset_eligibility, dataset_ingestion, dataset_registry, dataset_release,
federated_horizon, guided_capture, industry_collaboration, inspections,
instrument_intelligence, instrument_intelligence_admin, knowledge,
model_pipeline, nexus_api_gateway, nexus_integration, or_connect,
orbit_readiness, pilot_deployment, pilot_validation, platform,
predictive_insight, pulse_operations, quality_dashboard, quality_guardian,
review_workspace, reviewer_queues, scenario_analysis,
sentinel_orchestration, shadow_validation, spd_mentor, vanguard_intelligence,
workflow, workflow_forge.

**Priority within the backlog for Pilot Zero:** the dataset / annotation /
Ground-Truth / capture / inspection routes (they touch governed image
data) migrate before the analytics/dashboard routes.

Note: many of these also call `require_enterprise_auth`/`require_enterprise_role`
elsewhere, which *does* verify membership against the header tenant. The
migration's job is to make the tenant used for the **query** identical to
the verified one, and to add explicit cross-tenant tests — not to assume
the enterprise-auth check already covers every handler.
