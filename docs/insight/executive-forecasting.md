# Project Insight — Enterprise Forecast Dashboard & Executive Reports

LumenAI v3.3 — Sections 7 & 9

## Section 7 — Enterprise Forecast Dashboard (`/forecast`)

### Endpoint

```
GET /api/insight/dashboard?horizon=30_day
```

### Architecture

```
backend/app/services/insight_engine_service.py::build_forecast_dashboard
frontend/src/components/InsightDashboard.tsx
frontend/src/pages/ForecastPage.tsx                — route: /forecast
```

`build_forecast_dashboard` takes the full Section 1 intelligence payload
and maps it onto the six named displays the sprint asks for, each with
its own confidence indicator — it does not hand the dashboard the raw,
undifferentiated payload:

| Display | Source |
|---|---|
| Enterprise Quality Forecast | `quality_trend_forecasts` (all 9 metrics) |
| Risk Forecast | `instrument_lifecycle_forecasts`, filtered to elevated tiers |
| Repair Forecast | Instrument-level repair likelihoods + the `repair_backlog` operational forecast |
| Instrument Health Forecast | Health score trajectories per instrument type |
| Inspection Volume Forecast | `inspection_workload` + `peak_inspection_periods` operational forecasts |
| Education Forecast | The full Section 4 predictive-education response |

Every display's `confidence` field is the mean confidence across its
underlying forecast rows — never a single fabricated headline number.

## Section 9 — Executive Forecast Reports

### Endpoints

```
POST /api/insight/reports/generate
GET  /api/insight/reports
GET  /api/insight/reports/{id}
GET  /api/insight/reports/{id}.csv
GET  /api/insight/reports/{id}.xlsx
GET  /api/insight/reports/{id}.pdf
```

### Architecture

`backend/app/services/insight_report_service.py` reuses the exact export
pattern `atlas_report_service.py` (Atlas v3.1) established — CSV
(`csv.DictWriter`/`StringIO`), XLSX (`openpyxl.Workbook`/`BytesIO`), PDF
(`reportlab.pdfgen.canvas.Canvas`/`BytesIO`), all in-memory, no new
export library added.

### Cadence maps to horizon

Each report cadence resolves to one of Insight's own horizons, so a
"Weekly Forecast Summary" genuinely uses the 7-day forecast, not a
monthly one truncated:

| Cadence | Horizon |
|---|---|
| Weekly Forecast Summary | `7_day` |
| Monthly Quality Outlook | `30_day` |
| Quarterly Risk Forecast | `90_day` |
| Annual Strategic Planning Report | `rolling_annual` |

Generating a report regenerates the underlying quality-trend,
operational, and instrument-lifecycle forecasts at that horizon (via the
same generation functions the standalone endpoints use) and the
recommendation engine — so a report is never stale data assembled from
whatever happened to be in the database, it's a fresh forecast run.

### Route ordering note

The `.csv`/`.xlsx`/`.pdf` export routes are registered in
`predictive_insight.py` **before** the plain `GET /reports/{id}` detail
route — the same fix applied in `atlas_enterprise.py`: FastAPI/Starlette
match routes in registration order, and a request for `.../{id}.csv`
would otherwise match the generic `{report_id}` path first (then fail
int-conversion of `"1.csv"` with a 422) instead of falling through to the
more specific export route.
