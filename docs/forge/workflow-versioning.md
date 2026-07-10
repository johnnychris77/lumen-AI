# Project Forge — Workflow Version Control

LumenAI OS v4.1 — Section 9

## Copies Beacon's exact versioning pattern

Rather than a second versioned-content model or a separate history
table, `WorkflowDefinition` (and `WorkflowRule`, the same way) uses the
identical pattern `beacon_standards_service.py` already established for
`StandardsPublication`: one nullable `supersedes_id` self-referencing
column plus a `status` field (`draft`/`published`/`archived`), and a
`version_history()` walker that follows the chain to its root and back.

## Lifecycle

```
draft --publish--> published --revise--> draft (new version, supersedes_id set)
                       |
                       +--archive--> archived
```

- **Draft** (`forge_workflow_service.create_workflow`) — version 1,
  freely editable in place via `revise_workflow` as long as it stays a
  draft.
- **Published** (`publish_workflow`) — sets `approved_by`/`approved_at`/
  `effective_date`. A further `revise_workflow` call on a published
  workflow never mutates it: it creates a **new row** at `version + 1`,
  linked via `supersedes_id`, and moves `is_current` to the new row. The
  previously-current row's `is_current` is cleared but the row itself is
  never deleted or edited.
- **Archived** (`archive_workflow`) — retired; `is_current` is cleared.

## Rollback

`rollback_to_version(workflow_id, target_version_id)` re-validates that
the target is actually part of that workflow's own version chain (via
`version_history`), archives whatever is currently current, and
republishes the target version as current. The archived version keeps
its own row and history — rollback is itself just another recorded state
transition, not a destructive rewrite.

## Endpoints

```
GET  /api/forge/workflows/{id}/versions   — full chain, root to tip
POST /api/forge/workflows/{id}/rollback   — {"target_version_id": <id>}
GET  /api/forge/workflow-history/{id}     — versions + real + simulated executions, composed
```

Every version carries its own `author`, `reviewer`, `approved_by`, and
`effective_date` fields — "change history" is the version chain itself,
not a separate audit log (though every publish/rollback/revise action is
*also* recorded in the platform's shared `AuditLog` via `forge.*`
action types, for cross-module audit search).
