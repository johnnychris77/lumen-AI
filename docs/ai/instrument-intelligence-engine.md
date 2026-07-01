# Instrument Intelligence Engine (Phase 15)

**Status:** Draft for review
**Purpose:** Make LumenAI understand surgical instruments the way SPD professionals
inspect them — by anatomy, high-risk zone, retention area, required image coverage,
and clinical consequence — rather than reporting only "blood detected."

> ⚠️ Advisory pilot. Zone assignment and coverage are deterministic heuristics
> (instrument type + technician-tagged zones), not pixel-level CV. No FDA/
> diagnostic claims; `human_review_required` stays true.

## Components
- **Instrument Anatomy Library** (`app/services/instrument_anatomy.py`) — per-family
  anatomy zones, high-risk zones, required images, recommended angles, min images,
  manual steps. Extensible; no manufacturer hardcoded.
- **Zone risk model** (`app/services/instrument_zones.py`) — per-zone risk level,
  retention risk, contamination/condition risks, high-retention set.
- **Zone-aware output schema** — every finding carries `instrument_zone`,
  `zone_risk`, `zone_reason`, `recommended_manual_check`, `recommended_action`.
- **Zone-aware escalation** — contamination in a high-retention zone escalates more
  aggressively than the same signal on a flat surface (see
  `docs/ai/instrument-zone-taxonomy.md`).
- **Inspection Coverage Engine** (`app/services/inspection_coverage.py`) — coverage
  score, quality band, missing required zones, missing-image guidance, risk map.
- **AI Inspection Mentor** — zone-specific reasoning (what / where / why the zone is
  high risk / what to verify manually / what next).
- **Instrument Knowledge Library** (`instrument_knowledge` table) — manufacturer/
  model/family, IFU reference, anatomy + high-risk zones, failure modes, maintenance
  interval, repair/replacement criteria.
- **Executive analytics** — `GET /api/analytics/zone-intelligence` (real override-by-
  zone; zone-rate metrics surfaced empty until per-zone history exists — not faked).

## Future
SVG anatomy maps, clickable zones, image overlays, heatmaps, and segmentation masks
are a future CV release. The engine never fabricates visual evidence today.
