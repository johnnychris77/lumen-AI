# Project Atlas — Enterprise Analytics & Executive Reports

LumenAI v3.1 — Sections 7 & 9

## Enterprise Analytics (Section 7)

### Endpoints

```
GET /api/atlas/analytics/{system_id}/trend
GET /api/atlas/analytics/{system_id}/trend/all
```

### Architecture

`backend/app/services/atlas_analytics_service.py`

Trends the same `FacilityIntelligenceSnapshot` history Section 5 already
persists — never a re-derivation. Each call to `atlas_dashboard_service.
enterprise_dashboard` (or `refresh_all_facility_intelligence`) adds one row
per facility; this module buckets that accumulated history by
monthly/quarterly/yearly `created_at` labels and averages the requested
metric within each bucket. Supported metrics: `quality_score`,
`risk_score`, `health_score`, `digital_twin_health_pct`,
`supervisor_agreement_rate`, `training_index`, `knowledge_index`.

Each series point reports its `sample_size` (how many facility snapshots
fed into that bucket's average) alongside the averaged `value`, so a
one-facility bucket is visibly less confident than a ten-facility one.

## Executive Reports (Section 9)

### Endpoints

```
POST /api/atlas/reports/{system_id}/generate
GET  /api/atlas/reports/{system_id}
GET  /api/atlas/reports/{system_id}/{report_id}
GET  /api/atlas/reports/{system_id}/{report_id}.csv
GET  /api/atlas/reports/{system_id}/{report_id}.xlsx
GET  /api/atlas/reports/{system_id}/{report_id}.pdf
```

### Architecture

```
backend/app/services/atlas_report_service.py
frontend/src/components/AtlasDashboard.tsx  — "Reports" tab
```

### The first formally audience-typed report system in this codebase

Every other report generator here (`board_reporting.py`,
`benchmark_engine.generate_board_report`, `portfolio_briefings.py`) uses a
single fixed shape or a free-text `audience`/`role` string with no
validated set. `ExecutiveReport.audience` is validated against
`REPORT_AUDIENCES`: CEO, COO, SPD Director, Market Director, Hospital
Summary. `cadence` is validated against `REPORT_CADENCES`: monthly,
quarterly, annual.

### Audience-scoped summaries

`_build_summary` composes `atlas_dashboard_service.enterprise_dashboard`,
`atlas_watchlist_service.list_active_watchlist`, and
`atlas_benchmarking_service.cross_facility_benchmark` — never re-deriving
any of their math — and narrows the result by audience:

- **Market Director** reports (with a `market_id`) filter
  `facility_comparison` and the benchmark list down to that market only.
- **Hospital Summary** reports (with a `facility_id`) return only that one
  facility's intelligence and benchmark, not the full enterprise rollup.
- CEO/COO/SPD Director reports return the full enterprise summary.

### Export formats

Reuses the exact export patterns already established elsewhere in this
codebase, rather than adding a new library:

- **CSV** — `csv.DictWriter` over `StringIO`, the same pattern as
  `board_reporting.py`.
- **XLSX** — `openpyxl.Workbook()` with a "Summary" sheet (metric/value
  pairs) and a "Facility Comparison" sheet, the same pattern as
  `board_reporting.py`.
- **PDF** — `reportlab.pdfgen.canvas.Canvas`'s low-level, manual
  y-coordinate text drawing, the same pattern as `app/reports/pdf_report.py`,
  wrapping the Atlas disclaimer text at the bottom of the page.

All three are rendered to an in-memory buffer (`BytesIO`/`StringIO`) and
streamed via `StreamingResponse`, never written to a temp file.

### Route ordering note

The `.csv`/`.xlsx`/`.pdf` export routes are registered in
`atlas_enterprise.py` **before** the plain
`GET /reports/{system_id}/{report_id}` detail route. FastAPI/Starlette
match routes in registration order; without this ordering, a request for
`.../{report_id}.csv` would match the generic `{report_id}` path first (and
then fail int-conversion of `"1.csv"` with a 422) instead of falling
through to the more specific export route.
