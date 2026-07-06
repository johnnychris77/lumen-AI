# Inspection Zones

The zone taxonomy underlying anatomy resolution and zone-aware scoring: SPD
contamination and damage hide in specific instrument zones (serrations, box
locks, lumens, drill-bit flutes, o-ring areas, hinges …), not uniformly across
the whole instrument.

## Source of truth

`backend/app/services/instrument_zones.py`

- `ZONE_TAXONOMY` — zone category → representative zone names (e.g.
  `cutting_working_surface`, `rotary_orthopedic`, `lumen_scope`, `mechanical`,
  `handle_external`, `unknown`).
- `HIGH_RETENTION_ZONES` — zones where residual soil is hard to remove;
  contamination findings here are escalated.
- `ZONE_INFO` — per-zone `risk`, `reason` (why this zone matters), and
  `manual_check` (the recommended manual inspection step).
- `resolve_zones(instrument_type)` / `zone_for_finding(instrument_type,
  finding_type)` / `zone_fields(...)` — deterministic zone assignment for a
  finding, labeled `assignment_method: "pilot_zone_assignment"` with a capped
  confidence (never claimed as computer-vision certainty).

This is structured knowledge and deterministic pilot logic — **not**
pixel-level localization. A future CV release can localize the actual region
and drop into the same schema.

## API

`GET /api/instrument-zones` (v1.1 addition) — the full taxonomy,
high-retention zone list, and per-zone info, for the Inspection Zones library
page and for anyone integrating without reading the Python source.

## Frontend

`/inspection-zones` (`frontend/src/pages/InspectionZonesPage.tsx`) — zone
categories, the high-retention zone list, and a per-zone reference table
(risk / reason / recommended manual check).

## Relationship to the Coverage Engine

A zone only becomes part of an instrument's *required* image views if it's
listed in that family's `required_images` (see `anatomy-library.md`). The
Coverage Engine (`coverage-engine.md`) checks captured zones against that
required list — the zone taxonomy here is the shared vocabulary both use.
