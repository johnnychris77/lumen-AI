# Project Vanguard — Executive Intelligence Center & Scorecards

LumenAI OS v4.6 — Sections 1 & 2

## Naming disambiguation (read this first)

Before writing any Vanguard code, every existing "executive" surface in
this codebase was read in full:

* **`/api/executive/dashboard/{role}`** (`app/routes/executive.py`) —
  its own response labels most fields `"data_source": "mock"`: every
  role except `cfo` returns seeded `random.Random` values, and `cfo`'s
  "real" branch is a rough marketing-style ROI formula
  (`inspection_count * 0.9 / 60 * 30` for labor savings, hard-coded
  `$16,000`/`$78,000` constants) rather than genuine per-unit cost data.
  **Vanguard does not read from, extend, or model itself on this
  endpoint** — every figure in Vanguard's Executive Intelligence Center
  and Scorecards traces back to a real computation.
* **`/api/enterprise/governance-intelligence/summary`** returns four
  **literal hard-coded integers** (92, 88, 86, 90) — a genuinely
  fabricated pre-existing surface, unrelated to Vanguard's real
  Governance Dashboard (see `board-reporting.md`).

Vanguard's backend is mounted at **`/api/vanguard`**, never
`/api/executive`. Frontend routes `/executive` and `/strategy` were both
confirmed free before use.

## Executive Intelligence Center (Section 1)

`vanguard_executive_intelligence_service.executive_intelligence_center`
composes the eight named dimensions from services that already compute
each one for real:

| Dimension | Computed by |
|---|---|
| Enterprise Readiness / Risk | `pulse_command_center_service.pulse_command_center` |
| Surgical Readiness | `orbit_executive_service.executive_surgical_operations` |
| SPD Quality | `atlas_dashboard_service.enterprise_dashboard` (falls back to live Pulse KPIs if no enterprise-hierarchy facility exists — never a fabricated quality score) |
| Financial Impact | `vanguard_financial_service.financial_intelligence` |
| Capacity | Digital Twin utilization + today's scheduled case volume — genuinely new but built entirely from real rows (no "facility capacity" model existed anywhere before this) |
| AI Health / Knowledge Growth | `pulse_command_center_service.pulse_command_center` |

No dimension is computed twice — this module is a pure composition
layer.

## Executive Scorecards (Section 2)

Eight audience labels (`SCORECARD_AUDIENCES`: CEO, COO, CNO, CMO, VP
Surgical Services, Quality, Supply Chain, SPD Director) are **display
shapes** over the same real data above — exactly the pattern
`atlas_report_service.generate_executive_report`'s `audience` parameter
already established. RBAC continues to be enforced by the route's
existing `require_roles` tiers; the audience label only selects which
KPI subset is returned, never a new permission dimension. Every
generated scorecard is persisted as an `ExecutiveScorecardSnapshot` for
trend history.

```
GET /api/vanguard/executive-intelligence
GET /api/vanguard/scorecards/{audience}
GET /api/vanguard/scorecards/{audience}/history
```
