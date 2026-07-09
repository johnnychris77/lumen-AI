# Project Nexus — Data Governance

LumenAI v3.2 — Section 9

## Source System

Every synchronized record traces back to exactly one connector and its
underlying vendor system:

- `NexusSyncedAsset.source_system` — the connector_key (e.g. `censitrac`,
  `epic`) that supplied this instrument/tray record.
- `NexusSyncRun.connector_id` — every sync execution is tied to the
  connector that ran it, never anonymous.
- `NexusWorkQueueLink.connector_id` + `external_ref_id` — every linked
  work-queue item records both which connector created the link and what
  the external system calls that item.

## Ownership

Every Nexus table is `tenant_id`-scoped (per-hospital, matching this
codebase's tenant==hospital convention — see `docs/atlas/enterprise-model.md`
for the same convention in Atlas). A connector, its credentials, its
synced assets, its work-queue links, and its identity mappings all belong
to exactly one tenant and are never queried across tenant boundaries —
every service function in `app/services/nexus_*.py` takes `tenant_id` as
an explicit, required filter, never inferred.

## Synchronization Rules

- **Import vs. export** — `NexusWorkQueueLink.sync_direction` defaults to
  `import_only`. A caller must explicitly pass `sync_direction=
  "export_enabled"` for a link to be eligible for pushing LumenAI data
  back out to the external system — this directly implements the
  sprint's instruction: "Do not overwrite external systems without
  explicit configuration."
- **Validated references only** — `nexus_work_queue_sync_service.
  _validate_internal_ref` checks that `internal_ref_id` actually exists
  in the relevant internal table (`Inspection`, `RepairRequest`,
  `VendorTray`, `SurgicalCase`) *before* creating a link. A queue item
  that doesn't exist is never linked, let alone fabricated.
- **Upsert, not duplicate** — `nexus_asset_sync_service.sync_assets` keys
  on `(tenant_id, connector_id, external_id)`; re-running a sync updates
  the existing `NexusSyncedAsset` row rather than creating a duplicate.

## Conflict Resolution

When a second sync reports different attributes (manufacturer, model,
repair_status, location, service_status) for an asset already on file,
`NexusSyncedAsset.conflict_resolution` is set to `"external_wins"` and
`last_conflict_at` is stamped — the new external value replaces the old
one, but the fact that a conflict occurred (and when) is preserved rather
than silently overwritten. `GET /api/nexus/connectors/{id}/synced-assets`
surfaces this so an operator can review conflicting syncs.

## Retention

Nexus does not introduce a new retention policy — synced records
(`NexusSyncedAsset`, `NexusSyncRun`, `NexusEvent`) follow this platform's
existing retention/audit-trail conventions (`app/services/
retention_scheduler_service.py` and the standard audit log lifecycle) with
no Nexus-specific override, so a single retention policy governs the
whole platform rather than a second, connector-specific one.

## Audit Trail

Every governance-relevant Nexus action is logged via `app/audit.py::
log_audit_event` at the route layer:

- `nexus.connector_registered` — connector registration
- `nexus.credential_issued` / `nexus.credential_revoked` — credential
  lifecycle
- `nexus.assets_synced` — every asset sync run, with processed/failed/
  conflict counts

Every synchronized record's provenance fields (`source_system`,
`synced_at`, `conflict_resolution`) mean an operator never has to
reconstruct "where did this instrument record come from" from the audit
log alone — it's on the record itself.

## Provenance is mandatory, not optional

Every synchronized record must include provenance — this is enforced at
the schema level: `NexusSyncedAsset.source_system` and `synced_at` are
non-nullable columns, not optional metadata a connector can omit.
