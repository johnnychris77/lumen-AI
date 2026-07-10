# Project Orbit — Case Intelligence

LumenAI OS v4.5 — Section 3

## One call, every real signal for a case

`GET /api/orbit/cases/{case_id}/intelligence` (`orbit_case_intelligence_
service.case_intelligence`) composes:

* **Procedure, Required Trays, Inspection Status, Supervisor Holds** —
  directly from `or_connect_service.case_detail` (Project Symphony) —
  never recomputed.
* **Required Instruments** — via `case_detail`'s `inspection_ids`/
  `digital_twins`.
* **Implants** — this sprint's new `ImplantRecord` rows for the case.
* **Loaner Equipment** — this sprint's new `LoanerEquipment` rows.
* **Digital Twin Status** — `digital_twin_engine.compute_twin_dashboard`,
  fetched only when the case has at least one linked digital twin (never
  called speculatively for a case with no instruments logged yet).
* **Risk Alerts** — open `CaseRiskAlert` rows for the case (see
  `readiness-engine.md` for how new alert types are detected).
* **Knowledge Notes** — real, approved `KnowledgeArticle` rows tagged to
  the case's `procedure` field via `knowledge_repository_service.
  list_articles(procedure=...)`.
* **Case Cart / Environmental Readiness** — this sprint's newest tables,
  the latest row per case.

Nothing in this response is fabricated when a dimension has no data yet
— an empty list (no implants required, no risk alerts open) is a real
answer, not a placeholder.

## Endpoint

```
GET /api/orbit/cases/{case_id}/intelligence?facility_id=<optional>
```
