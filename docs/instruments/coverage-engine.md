# Inspection Coverage Engine

Computes how completely an inspection's tagged image views cover an
instrument's required anatomy zones, and what's still missing before a
confident clinical decision.

## Source of truth

`backend/app/services/inspection_coverage.py`

- `compute_coverage(instrument_type, inspected_zones)` — coverage against the
  instrument's `required_images`. When `inspected_zones` is `None` (zones
  were never tagged), returns `assessed: False` / `quality: "not_assessed"`
  rather than an alarming 0% — an explicit (possibly empty) list is assessed
  normally.
- `missing_image_guidance(instrument_type, inspected_zones)` — "Close-up image
  of {zone}" guidance list for each missing required zone.
- `build_risk_map(instrument_type, findings_by_zone, inspected_zones)` —
  per-zone table: required? / inspected? / findings? / zone risk /
  recommended manual check.
- `coverage_dashboard_summary(db, tenant_id)` (v1.1 addition) — real
  aggregate stats across stored inspections: average coverage, status
  breakdown, average coverage by instrument family, most commonly missing
  zones, recent inspections. Inspections that never had zones tagged are
  excluded from the average (not counted as 0%) — nothing fabricated.

## Coverage status vocabulary

| Status | Meaning |
|---|---|
| `complete` | 0 missing required zones and ≥95% coverage |
| `acceptable` | 0 missing required zones, or ≥80% coverage |
| `incomplete` | ≥50% coverage |
| `insufficient` | <50% coverage |
| `not_assessed` | zones were never tagged for this inspection |

## Wiring

- `app/services/baseline_comparison_scoring_service.py` calls
  `compute_coverage` / `missing_image_guidance` / `build_risk_map` and attaches
  `instrument_anatomy`, `inspection_coverage`, `missing_image_guidance`,
  `risk_map` onto every completed AI analysis (see `ai-context.md`
  cross-reference in `guided-capture.md`).
- `app/agents/coverage_agent.py` (`InspectionCoverageAgent`, Phase 22 §3) wraps
  the same service for the multi-agent/CIOS pipeline — no separate coverage
  logic.

## API

- `GET /api/coverage-dashboard/summary` (v1.1 addition) — fleet-wide
  aggregate, backing the Coverage Dashboard page.
- Per-inspection coverage is embedded in the `POST /api/inspections` analysis
  response (`inspection_coverage`, `missing_image_guidance`, `risk_map`), not
  a separate endpoint.

## Frontend

- `/coverage-dashboard` (`frontend/src/pages/CoverageDashboardPage.tsx`) —
  fleet-wide aggregate view.
- Per-inspection: `frontend/src/components/InstrumentIntelligencePanel.tsx`,
  rendered inline in the New Inspection AI-prediction panel — shows the
  coverage percentage, captured/missing zone chips, and the missing-image
  guidance list described in the v1.1 spec.

## Missing high-risk zones do not block submission

Guidance is advisory ("Inspection coverage incomplete. Upload additional
images for: …"); the current default does not block inspection submission on
incomplete coverage. See `guided-capture.md` for the non-blocking rationale.
