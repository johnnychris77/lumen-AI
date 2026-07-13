# Governed Action Schema

The `GovernedAction` model (`app/models/governed_action.py`, table
`governed_actions`) is the durable record tracking an approved decision from
implementation plan through closure.

## Fields

| Field | Notes |
|---|---|
| `id` | Primary key; doubles as the brief's `action_id` (no separate column, matching every other specialist's convention). |
| `tenant_id` | LumenAI's real multi-tenancy key; maps to the brief's `organization_id`. |
| `facility_id` | Optional facility scope. |
| `source_type` / `source_id` | Points back to the record that was actually approved (see `SOURCE_TYPES`). Never re-derived or overridden by Steward. |
| `source_decision`, `approved_by`, `approval_timestamp` | The approval-of-record. All three are required at creation -- see `action-lifecycle.md`. |
| `action_title`, `action_description`, `category`, `action_type` | What the action is (see `action-types.md` categories below). |
| `owner`, `accountable_leader`, `stakeholders` | Required before an action can reach `READY_TO_START`. |
| `priority`, `risk_level` | `low` / `medium` / `high` / `critical`. High/critical drives every elevated-authority and evidence-sufficiency gate in this module. |
| `dependencies`, `milestones` | JSON lists; dependency *analysis* is computed live (see `implementation-planning.md`), never separately persisted. |
| `due_date`, `status` | Drives due-soon/overdue escalation. |
| `evidence_requirements`, `expected_outcomes`, `success_metrics` | Inputs to the plan generator and benefits-realization engine. |
| `actual_outcomes`, `benefits_realization` | Rolled up from the most recent `GovernedActionOutcomeReview`. |
| `unintended_consequences` | JSON summary; the authoritative rows live in `GovernedActionUnintendedConsequence`. |
| `change_readiness` | `ready` / `partially_ready` / `not_ready` / `blocked` / `unknown`. |
| `closure_decision`, `closure_approver`, `closed_at` | Set only via `steward_closure_service.close_action`. |

## Source types

`council_case`, `capa`, `sentinelx_risk_alert`, `maestro_recommendation`,
`aegis_process_recommendation`, `vulcan_reliability_recommendation`,
`sage_education_recommendation`, `veritas_evidence_remediation`,
`phoenix_improvement_recommendation`, `audit_finding`, `policy_change`,
`leadership_directive`.

## Why a Governed Action is not a CAPA

The existing `capas` table (`capa_service.py`) and its `open -> assigned ->
in_progress -> verified -> closed` lifecycle (`capa_lifecycle_service.py`) are
not duplicated here. A `GovernedAction` with `source_type="capa"` links to a
CAPA's id via `source_id` -- Steward's own 15-status lifecycle tracks the
*implementation* of that CAPA's corrective/preventive action, a materially
richer, longer-running process (dependencies, phased rollout, benefits
realization) than the CAPA record itself models.

## Child tables

| Table | Section | Purpose |
|---|---|---|
| `GovernedActionAuditEvent` | 3, 24 | Append-only status/audit trail. |
| `GovernedActionRollout` | 8 | Phased-rollout stages (see `change-management.md` for naming). |
| `GovernedActionVerification` | 9 | Completion evidence, gated by Veritas for high-risk actions. |
| `GovernedActionOutcomeReview` | 10 | Benefits-realization measurements. |
| `GovernedActionUnintendedConsequence` | 11 | Flagged consequences. |
| `GovernedActionResidualRiskReview` | 20 | Sentinel-X risk before/during/after. |
