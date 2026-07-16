# LumenAI — Pilot Implementation Plan

Objective 5 review. **Distinct from `docs/demo-program/PILOT_IMPLEMENTATION_GUIDE.md`** (Phase 5's index of existing pilot documentation) — this Phase 6 document is the governance framework itself: objectives, metrics, acceptance criteria, timeline, stakeholders, governance meetings, feedback collection, risk register, and go/no-go and expansion criteria, per this program's Objective 5 scope.

## Pilot objectives

Reference `docs/pilot/LUMENAI_v1_4_ENTERPRISE_PILOT_EXECUTION_PLAN_v1.md`'s phased structure directly (Phase 0 Internal Readiness → kickoff → workflow validation → evidence capture → executive review → commercial conversion) and its explicit pilot-scope exclusions (no PHI ingestion, no EHR integration) — these exclusions should be restated to every pilot customer up front, not discovered mid-pilot.

## Success metrics and acceptance criteria

`docs/pilot/pilot-success-metrics.md` already defines this in full: Adoption/Data Quality/Operational Value/User Satisfaction metric tables with numeric targets, computed from real, persisted data (`pilot_analytics.py`'s contamination-trends/inspection-efficiency/CAPA-effectiveness/baseline-adoption/ROI endpoints). Use directly; do not re-derive.

## Timeline and stakeholders

`docs/pilot/pilot-launch-runbook.md`'s T-14-day pre-launch checklist and launch-day checklist (with documented abort criteria) is the real, operable timeline. Stakeholder roles map onto the personas documented in `docs/ux-review/USER_PERSONAS.md` — cite that document's honest role-mapping gaps (Supervisor/Director/Market Director have no independently-enforced RBAC role) when defining who signs off at each pilot milestone, so the pilot agreement's named approvers match what the platform can actually enforce.

## Governance meetings

`docs/customer/customer-success-playbook.md`'s QBR cadence model (tier-linked frequency) is the real governance-meeting structure. For pilot-specific interim governance, `docs/pilot/pilot-launch-runbook.md`'s daily/weekly monitoring templates are the operable cadence during the pilot window itself, before the customer converts to a standard subscription tier's QBR cadence.

## Feedback collection

Real and working, not aspirational: `backend/app/routes/pilot_analytics.py`'s `/survey/submit` and `/survey/summary` endpoints back the pulse survey referenced in `pilot-success-metrics.md` §5.1, and `PilotAnalyticsDashboard.tsx`'s "Weekly Pulse Survey" widget is the live UI. `PilotErrorLog` (`backend/app/models/pilot_error_log.py`) provides real, structured operational-failure feedback (upload/AI-analysis/baseline-lookup/role-permission/report-generation failure categories) as a second, technical feedback channel.

## Risk register

No pilot-specific risk register currently exists as a standalone artifact. Construct it from three real, existing sources rather than starting blank:
1. The three named Critical Gaps in `docs/production-readiness/PRODUCTION_READINESS_SCORECARD.md` (dev-auth bypass configuration risk, possible mock-data-serving executive dashboard, near-absent database referential integrity).
2. The Supervisor-approval UX gap documented in `docs/ux-review/USER_JOURNEYS.md` and reconfirmed in `docs/demo-program/ROLE_BASED_DEMOS.md` — a genuine operational risk for any pilot that expects a working supervisor review-and-approve action in the UI.
3. `docs/security/security-risk-register.md`'s existing SEC-001 through SEC-006 findings (Bandit/pip-audit/npm audit/Gitleaks-derived), most marked "Pending"/"Open" as of this review.

## Go/No-Go criteria

`docs/pilot/pilot-success-metrics.md`'s existing Pilot Go/No-Go Scorecard (weighted Pass/Fail across 4 categories, "Pass ≥ 3 of 4 categories" to proceed) is the real, usable mechanism — cite directly. `pilot_service.py`'s `conversion_ready` gate (`days_remaining <= 15 and met_count >= 4` against `PilotStatus.agreed_kpis`) is the code-enforced complement to the scorecard's qualitative assessment.

## Expansion criteria

`docs/customer/customer-success-playbook.md`'s tier-linked expansion plays and `docs/global/global-commercialization-plan.md`'s implementation-revenue-model framing describe expansion mechanics — but see `docs/commercial-readiness/PRICING_MODEL.md` for the honest disclosure that expansion-relevant pricing figures currently conflict across three different internal documents and must be reconciled before being presented to a real pilot customer as a fixed expansion price.
