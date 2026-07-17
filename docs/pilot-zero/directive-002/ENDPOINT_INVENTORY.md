# Endpoint Inventory (LPZ-DIR-002, Phase 5)

Classification vocabulary: PUBLIC · AUTHENTICATED · TENANT_SCOPED ·
ADMINISTRATOR · INTERNAL_SERVICE · DEVELOPMENT_ONLY · DISABLED ·
UNCLASSIFIED.

## Status

**IN PROGRESS.** A complete, per-endpoint classification of every mounted
route is required before Directive 002 can be marked closed (no endpoint
may remain UNCLASSIFIED at closure). That full enumeration is a dedicated
deliverable of the next increment; this increment classifies the route
family it touched and records the method for the rest.

## Classified this increment

| Method | Path | Router | Handler | Auth | Authz | Tenant dep | Write | Sensitivity | Production mounted | Classification |
|---|---|---|---|---|---|---|---|---|---|---|
| GET | /api/history | history | get_history | require_roles | 4 roles | resolve_verified_tenant | no | inspection records | yes | TENANT_SCOPED |
| GET | /api/history/summary | history | get_history_summary | require_roles | 4 roles | resolve_verified_tenant | no | aggregates | yes | TENANT_SCOPED |
| GET | /api/history/export.json | history | export_history_json | require_roles | 3 roles | resolve_verified_tenant | no | bulk export | yes | TENANT_SCOPED |
| GET | /api/history/export.csv | history | export_history_csv | require_roles | 3 roles | resolve_verified_tenant | no | bulk export | yes | TENANT_SCOPED |
| GET | /api/history/export.xlsx | history | export_history_xlsx | require_roles | 3 roles | resolve_verified_tenant | no | bulk export | yes | TENANT_SCOPED |
| GET | /api/history/export.bundle.zip | history | export_history_bundle | require_roles | 3 roles | resolve_verified_tenant | no | bulk export | yes | TENANT_SCOPED |
| GET | /health, /ready, /metrics | app.main | probes | none/token | — | none | no | ops | yes | PUBLIC / INTERNAL_SERVICE |
| GET | /api/gpae/health/deep, POST /api/gpae/monitoring/sweep | gpae_monitoring | — | require_roles(admin,spd_manager) | 2 roles | none | no | ops | yes | ADMINISTRATOR |

## Enumeration method (for the completing increment)

Iterate `app.main.app.routes`, and for each `APIRoute` record method,
path, endpoint module, and its `Depends(...)` chain (auth dependency,
role gate, tenant helper), whether the handler performs a write, and
whether it is mounted in production. Prioritize identifying **unauthenticated
write** endpoints (Finding F4). This is a mechanical pass over the mounted
router table; no unauthenticated writer has been confirmed yet, and none
may be assumed absent until the pass is complete.
