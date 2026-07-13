# LumenAI — Enterprise Dashboards

Objectives 7 (Enterprise Reporting) and 8 (Enterprise Dashboard at `/enterprise`) review.

## Enterprise Reporting — 2 of 6 required report types are real

`vanguard_board_reporting_service.py::generate_board_packet()` supports exactly 4 packet types, real and genuinely exported to PDF/Excel/PPTX (`reportlab`/`openpyxl`/`python-pptx`, all confirmed working code, not stubs):

| Required report type | Status |
|---|---|
| Monthly executive reports | **Real** — `PACKET_MONTHLY_BOARD` |
| Quality summaries | **Real** — `PACKET_QUALITY_COMMITTEE`, appends `finding_trend_service.finding_trends` |
| Operational summaries | **Partial** — `PACKET_QUARTERLY_REVIEW` loosely covers this but isn't distinctly named "operational" |
| Regional comparisons | **Missing** — no packet type produces per-region/per-market rollups; a real market-benchmark rollup exists elsewhere (`enterprise_dashboards.py`'s `/market/{market_id}` route) but board reporting doesn't use it |
| Benchmark reports | **Missing** — the module's own docstring explicitly notes it deliberately does not reuse `benchmark_engine.generate_board_report`, and no packet type covers this |
| Improvement reports | **Missing** — no packet type maps to this at all |

A fifth real packet type exists (`PACKET_ANNUAL_STRATEGIC`) but isn't one of this brief's 6 named categories. `docs/vanguard/board-reporting.md` already documents all 4 real packet types, the export formats, and the deliberate non-reuse of `benchmark_engine`'s board report — cite that document rather than duplicating it.

## `/enterprise` Dashboard — a confirmed runtime bug means it likely never shows real data today

`frontend/src/pages/EnterpriseDashboard.tsx` is real, nav-wired (`AppShell.tsx`'s "Quality & Compliance" group, gated `ELEVATED_ROLES`), and renders 3 sections: Executive Scorecard, Facility Readiness, System Quality.

**Confirmed bug**: this page's three data-fetch calls hit `/api/enterprise/dashboards/executive-scorecard`, `/system-quality`, and `/readiness` — with **no `{system_id}` path segment**. The only matching backend router (`backend/app/routes/enterprise_dashboards.py`) requires `system_id` as a mandatory path parameter on all three routes (`/executive-scorecard/{system_id}`, `/system-quality/{system_id}`, `/readiness/{system_id}`) — there is no route registered without it. **Every one of these three fetches will 404 as the page is currently wired**, and each failure is silently caught (`.catch(() => null)`), so the page always renders its "No data available" empty states in practice. The underlying backend logic (real KPIs, readiness scoring, a benchmarking endpoint at `/benchmarking/{system_id}`) is genuinely computed from live `EnterpriseFacility`/`Inspection` data — it is simply unreachable from this page as written today.

Against Objective 8's 8 required panel types:

| Required panel | Status |
|---|---|
| Facilities | Present (Facility Readiness section) — though currently unreachable due to the bug above |
| KPIs | Present (Executive Scorecard section) — same caveat |
| Heatmaps | **Missing** — no heatmap component anywhere on this page |
| Risk | **Missing** — no risk panel |
| Digital Twins | **Missing** — the page never calls any digital-twin endpoint |
| Quality | Present (System Quality section) — same fetch-bug caveat |
| Capacity | **Missing** — capacity planning lives only on the separate `/strategy` route, never surfaced here |
| Benchmarking | **Missing** — the page never calls the real `/api/enterprise/dashboards/benchmarking/{system_id}` endpoint, even though it exists and works |

**This `/enterprise` route is an unrelated, older ("P16-era") surface, not part of Project Vanguard** — `docs/vanguard/strategic-planning.md` correctly documents Vanguard's own frontend as living at `/strategy`, a separate page entirely. No existing Vanguard documentation covers `/enterprise` at all; this document is the first to do so.

## Recommendation

1. **Fix the `/enterprise` page's missing `system_id` path parameter first** — this is a simple, isolated frontend bug (add the tenant's resolved `system_id` to the three fetch URLs) that currently makes the entire page non-functional in practice despite working backend logic underneath it.
2. Only after that fix, consider whether to add the 5 missing panels (Heatmaps, Risk, Digital Twins, Capacity, Benchmarking) — several of these already have real backend endpoints (benchmarking, digital twin health via Atlas) that just need a frontend panel wired to them, not new backend work.
3. Add "Regional comparisons," "Benchmark reports," and "Improvement reports" as new Vanguard board-packet types if enterprise reporting is a genuine Version 1.3 priority — these require new packet-generation logic, not just wiring existing data.
4. Cite `docs/vanguard/board-reporting.md` and `docs/vanguard/strategic-planning.md` directly for what's already documented; this document's contribution is the gap analysis against the brief's specific required lists, plus the newly-found `/enterprise` runtime bug.
