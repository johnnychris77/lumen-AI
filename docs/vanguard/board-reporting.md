# Project Vanguard — Board Reporting & Governance Dashboard

LumenAI OS v4.6 — Sections 7 & 9

## Board Reporting (Section 7)

Three other board-report generators already exist in this codebase —
checked in full before writing `vanguard_board_reporting_service.py`:

| Existing generator | Why Vanguard doesn't extend it |
|---|---|
| `routes/board_reporting.py` | A single, fixed-shape weekly report (CSV/XLSX/ZIP) over raw `Inspection` rows — no audience or cadence typing at all. |
| `benchmark_engine.generate_board_report` | A second, older, `CVInferenceRecord`-based enterprise-rollup lineage (with a mock-data-when-`db=None` fallback), parallel to Atlas's real-only lineage. Composing it would mean Vanguard depends on two incompatible enterprise rollups. |
| `portfolio_briefings.py` | LumenAI's own SaaS customer-portfolio board briefing (tenant churn/renewal risk) — a completely different audience (LumenAI's leadership, not the hospital's). |

Instead, `vanguard_board_reporting_service.generate_board_packet`
extends **`atlas_report_service.generate_executive_report`**, which
already has the right shape (`REPORT_AUDIENCES`, `REPORT_CADENCES`,
persisted `ExecutiveReport` rows) — it was only missing a PowerPoint
export and a named-packet-type wrapper, both added here.

Four named packet types map onto Atlas's existing audience/cadence enum
rather than inventing a new one:

| Packet type | Atlas audience | Atlas cadence |
|---|---|---|
| Monthly Board Packet | `ceo` | `monthly` |
| Quarterly Executive Review | `coo` | `quarterly` |
| Annual Strategic Report | `ceo` | `annual` |
| Quality Committee Report | `spd_director` | `monthly` (+ `finding_trend_service.finding_trends` appended) |

A tenant with no resolvable enterprise-hierarchy facility gets the live
Vanguard Executive Intelligence Center snapshot instead of a fabricated
Atlas-shaped report — the same honest-fallback pattern established
throughout this codebase (e.g. Catalyst's `reporting_skill`).

### Exports

* **PDF** — the same `reportlab` low-level canvas pattern
  `atlas_report_service.build_report_pdf_bytes` already uses.
* **Excel** — the same `openpyxl` two-sheet pattern.
* **PowerPoint** — genuinely new for a *hospital-facing* report, but
  built with the exact `python-pptx` `Presentation()` pattern already
  used internally by `leadership_packet_exports.py`/
  `governance_packet_exports.py`/`portfolio_briefing_exports.py` (all
  three scoped to LumenAI's own internal reporting) — this is the first
  hospital-facing consumer of that established pattern, not a new export
  library.

```
GET  /api/vanguard/board-reports
POST /api/vanguard/board-reports/generate   {packet_type}
GET  /api/vanguard/board-reports/{id}
GET  /api/vanguard/board-reports/{id}.pdf
GET  /api/vanguard/board-reports/{id}.xlsx
GET  /api/vanguard/board-reports/{id}.pptx
```

## Governance Dashboard (Section 9)

At least five pre-existing governance-adjacent surfaces were checked
before scoping this section:

* Horizon's `/api/horizon/governance/*` and Beacon's
  `/api/beacon/governance/*` — both scoped narrowly to their own
  sprint's knowledge-sharing participation workflow, not general org
  governance.
* `governance_console.py` — retention-policy compliance (reused
  directly for "policy compliance" below).
* `governance_command_center.py` — SLA events + packet-release
  exceptions (real, reused directly for "workflow compliance").
* `accreditation_engine.py` — real audit-readiness scoring (reused
  directly for "audit readiness").
* **`/api/enterprise/governance-intelligence/summary`** — every score
  in its response (92, 88, 86, 90) is a **literal hard-coded integer**,
  not computed from any table. This is a genuinely fabricated
  pre-existing surface; `vanguard_governance_service.py` does not read
  from or extend it.

| Dimension | Computed by |
|---|---|
| Policy compliance | Real count of enabled `RetentionPolicy` rows |
| Knowledge adoption | `knowledge_graph_service.learning_confidence` |
| Workflow compliance | `governance_command_center.command_center_summary` |
| Audit readiness | `accreditation_engine.compute_regulatory_dashboard` |
| Training completion | New: org-wide average of `competency_service.technician_quality_dashboard`'s real per-technician `training_progress_pct` — no "% required training completed" rollup existed anywhere before this |

```
GET /api/vanguard/governance
```
