# LCID Persistence

## Contract

Every image registered into the clinical dataset infrastructure receives
a permanent LCID (`LCID-YYYY-NNNNNNNNN`). LCIDs are:

* **assigned once** at registration by `app.services.ml.lcid_service`
  using `LcidSequenceCounter` (a per-year atomic counter row);
* **unique** — `DatasetRegistryEntry.lcid` carries a UNIQUE constraint
  (enforced by the database, verified on PostgreSQL this sprint);
* **never reused and never reassigned** — archiving or superseding an
  entry does not free its LCID; the counter only moves forward.

## Root identity chain

The LCID is the join key that makes the evidence chain traceable
end-to-end:

```
LCID image
  → AnnotationVersion rows (append-only)
  → Ground Truth versions
  → BaselineImageLink (Atlas; ACTIVE baselines cite the LCID image)
  → DatasetVersion membership (frozen, immutable)
  → training runs / ModelRegistryEntry (dataset_version_id)
  → live inference records (lcid_image_id in the result contract)
  → Digital Twin history
  → audit_logs (hash-chained, immutable)
```

The Sprint-2 result contract exposes `image.lcid_image_id` +
`image.sha256` on every live inference result, so a result can always be
traced back to the exact image identity it scored.

## Status of this objective

Already built by the LCID sprint and Project Canvas; **verified, not
rebuilt, this sprint**. The uniqueness constraint and counter semantics
now also carry executed PostgreSQL evidence (the constraint is enforced
by PostgreSQL 16 in the migrated schema, not just by SQLite).

Evidence: LCID/dataset-registry test suites; migration `4b336d3ed612`
onward applied to PostgreSQL (see `POSTGRESQL_MIGRATION.md`).
