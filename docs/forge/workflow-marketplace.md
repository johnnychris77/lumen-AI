# Project Forge — Forge Marketplace

LumenAI OS v4.1 — Section 10

## One more field on the existing model, not a second workflow-library table

`WorkflowDefinition.marketplace_status` (`private` / `pending_review` /
`published`) is the entire marketplace data model — Sections 1, 4, 9,
and 10 all share the one `WorkflowDefinition` table. This mirrors the
draft → review → published idiom Beacon's `StandardsPublication` and
P24's `AdvisoryConsortiumMember` already established in this codebase
for governance-gated shared content, rather than inventing a new one.

## Operations

| Sprint's requirement | Function | Governance |
|---|---|---|
| Import templates | `forge_marketplace_service.import_template` | Clones one of the nine seeded global templates into the caller's own tenant as a fresh draft |
| Clone workflows | `clone_workflow` | Deep-copies any workflow (own, template, or published marketplace listing) the caller can see into a new, independent draft (`workflow_ref` is new — it is not a version of the source) |
| Share approved workflows | `share_workflow` | Only a **published** workflow may be shared; sets `marketplace_status = pending_review` — never publishes to the marketplace directly |
| **"Community templates require governance approval"** | `approve_share` | Gated to the `admin` role at the route layer (`POST /api/forge/workflows/{id}/approve-share`); only this call moves `pending_review` → `published`, making the workflow visible to every tenant via `GET /api/forge/marketplace` |
| Export workflows | `export_workflow` | Returns a portable JSON blob (`workflow_ref`, `name`, `nodes`, `edges`, `version`) for external download/backup |

## Endpoints

```
GET  /api/forge/marketplace                          — every published community listing
POST /api/forge/workflows/{id}/clone
POST /api/forge/workflows/{id}/share
POST /api/forge/workflows/{id}/approve-share           — admin only
GET  /api/forge/workflows/{id}/export
POST /api/forge/workflow-templates/{category}/import
```

Every `approve-share` call is recorded in the platform's shared
`AuditLog` (`forge.marketplace_approved`) — the same single audit table
every other sprint in this codebase already writes to.
