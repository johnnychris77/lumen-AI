# LCID Digital Twin Linkage

## What "Digital Twin ID" means here

This codebase has no single first-class "digital twin" entity carrying an
ID (several unrelated things are named "twin" elsewhere — SPD-workflow
snapshots, quality snapshots, Oracle insights). Rather than invent a new,
disconnected twin concept, `DatasetRegistryEntry.digital_twin_id` reuses
the same barcode/UDI-based physical-instrument identity already computed
by `app.services.pre_sterilization_command_center_service._instrument_identity()`
(re-implemented identically in `app.services.ml.lcid_service.instrument_digital_twin_id()`
to avoid a service-layer import across module boundaries):

- `barcode:{instrument_barcode}` when a barcode was captured,
- `udi:{instrument_udi}` when a UDI was captured (no barcode),
- `untracked:{instrument_type}:{inspection_id}` otherwise — an honest
  admission that no real re-identification occurred, never fabricated.

## History linkage

`lcid_service.digital_twin_history()` returns, for a given
`digital_twin_id`: every other dataset image sharing that identity, the
real `Inspection` rows matching the same barcode/UDI, and a repair-history
count (inspections whose `disposition == "REMOVE FROM SERVICE"`) — reusing
the same real query pattern as
`readiness_engine.has_repair_history()`, not a duplicate implementation.

## Baseline linkage

`DatasetRegistryEntry.baseline_id` references
`app.models.baseline_library.BaselineLibraryEntry.id` — resolved at
registration time via `lcid_service.resolve_baseline_id()`, which returns
`None` (never a guess) when no approved baseline exists for the
instrument's category/manufacturer.

## Orphan detection

`app.services.ml.dataset_validation_service.validate_registry()` flags any
`baseline_id` that no longer resolves to a real `BaselineLibraryEntry` row
as a `missing_baseline_links` finding, and any reviewed entry with no
baseline linked at all — see `DATASET_SPECIFICATION.md`.
