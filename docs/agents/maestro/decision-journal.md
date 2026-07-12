# Project Maestro — Operational Health Index, Decision Journal & Leadership Workspace

Sections 7, 8, 9 of the sprint brief.

## Operational Health Index (Section 7)

`maestro_health_index_service.compute_operational_health(db, tenant_id)`
reuses five of Phoenix's already-computed platform maturity dimensions
(`phoenix_maturity_index_service.compute_platform_maturity_index`)
directly — Quality, Workflow, Education, Digital Twins (renamed
`digital_twin_score`), Knowledge — plus Phoenix's executive-intelligence
(audit-readiness) dimension, renamed `enterprise_score`. **Equipment** is
the one genuinely new dimension: the average Vulcan Instrument Reliability
Score across the tenant's most recent 200 `VulcanReliabilityAssessment`
rows (`None` if no rows exist yet — never fabricated).

`overall_score` is the average of whichever of the 7 dimension scores are
actually present; a `MaestroOperationalHealthSnapshot` persists all 7 plus
`breakdown_json`, which traces back to the source Phoenix maturity
snapshot's `id` for full auditability. `human_review_required` is always
`True`.

## Decision Journal (Section 8)

`maestro_decision_journal_service.record_decision(db, tenant_id,
recommendation_id, *, leader_decision, decided_by, ...)` is the leadership
knowledge base: for every recommendation a leader acts on, it records the
evidence and specialists consulted (copied from the recommendation at
decision time), Maestro's confidence, what the leader actually decided,
the outcome, and lessons learned.

`leader_decision` is required and non-empty — a `ValueError` is raised
otherwise, since an empty journal entry would defeat its purpose as an
audit record. Recording a decision is also the *only* place a
recommendation's `status` moves out of `pending` (via the optional
`new_status` parameter) — Maestro itself never silently advances a
recommendation's status.

## Leadership Workspace (Section 9, `/maestro`)

`maestro_orchestration_service.leadership_workspace_summary(db,
tenant_id)` composes the single `/maestro` payload:

- **Top Priorities** — `maestro_priority_engine_service.latest_priorities`
- **Operational Health** — the latest `MaestroOperationalHealthSnapshot`
- **Open Risks** — Sentinel-X's `risk_dashboard_summary` (enterprise,
  facility, anatomy risk)
- **Today's Recommendations** — pending `MaestroRecommendation`s with
  `timeline_horizon="today"`
- **Pending Executive Decisions** — all pending recommendations
- **Shift Readiness** — Sentinel-X's `supervisor_workspace_summary`
  pending-review count, open patient safety alert count, and escalating
  trends
- **Enterprise Status** — overall operational health plus enterprise-wide
  average/high-or-critical risk percentage

Every field is a direct read of an already-computed specialist output;
nothing here is computed fresh outside of the Priority Engine, Health
Index, and Recommendation Engine themselves. `human_review_required` is
always `True`, and the response carries Maestro's `DISCLAIMER`: it never
replaces human leadership.
