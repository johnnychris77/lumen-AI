# Closed Learning Loop

Codename: Project Guardian · LumenAI Quality v2.9

## Route

`/quality-command-center` (`frontend/src/pages/QualityCommandCenterPage.tsx`,
rendering `QualityCommandCenterDashboard.tsx`). Five tabs: Quality Events,
RCA & CAPA, Competency, First Pass Yield, Executive Dashboard.

## What "every confirmed event should update X" actually means here

Section 10 of the sprint lists six systems a confirmed event should update:
Digital Twin, Clinical Memory, Knowledge Graph, Reasoning Engine, Education
Library, Trend Analytics. `quality_command_center_service.apply_learning_loop`
is honest about which of these have real, separate mutable state to write
to versus which are computed live from underlying data and simply reflect
new information the next time they're read:

| System | What actually happens |
|---|---|
| Clinical Memory (`ClinicalCase`) | **A real write.** If the event correlates to an inspection and qualifies as significant (`clinical_case_library_service.is_significant`), `save_or_update_case` is called with the event's narrative as clinical reasoning and `outcome="or_confirmed_quality_event"`. |
| Digital Twin (instrument condition) | No separate write needed — `instrument_condition_service.instrument_condition_history` derives condition trend live from `Inspection`/`InspectionFinding` rows, which the correlated inspection is already part of. |
| Knowledge Graph | Computed live from structured data (`knowledge_graph_service.py`) — reflects the event's classification/correlation on next read. |
| Reasoning Engine / Trend Analytics | Computed live (`finding_trend_service.py`, `anatomy_risk_service.py`, etc.) — same reasoning as above. |
| Education Library | A fixed, code-generated reference (`education_library.py`), not a database table — "updating" it would be a code change, not a runtime write; out of scope here. |

`POST /api/quality-guardian/events/{id}/confirm` marks the event confirmed
(and by whom); `POST /api/quality-guardian/events/{id}/learning-loop` then
applies the above and reports exactly what was and wasn't updated — never
silently claiming a write that didn't happen.

## Executive Quality Dashboard

`GET /api/quality-guardian/command-center` aggregates, without re-deriving
any of their logic:

- Quality events (30-day window) by severity, recurring findings
- CAPA lifecycle counts (`capa_lifecycle_service.lifecycle_summary`)
- Root cause trends (`root_cause_service.root_cause_trends`)
- First Pass Yield, all scopes (`first_pass_yield_service.compute_all_scopes`)
- Education impact — average effectiveness score across addressed
  competency opportunities
- Technician trends (`competency_service.technician_quality_dashboard`)
- Vendor trends (from OR Connect's `VendorTray` records)
- Manufacturer trends (baseline approval rates from `BaselineLibraryEntry`)

Restricted to `admin`/`spd_manager`. Every response carries
`human_review_required: true` and the fixed Guardian disclaimer.
