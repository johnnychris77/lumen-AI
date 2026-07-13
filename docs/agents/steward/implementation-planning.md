# Implementation Planning

## Plan generation (`steward_plan_generator_service.generate_draft_plan`)

For each approved decision, Steward generates a draft plan directly from the
Governed Action's own already-validated fields, plus deterministic,
category-level defaults for the parts the action record doesn't carry a
column for (affected roles, communication plan, training requirement,
rollback plan). Nothing here is LLM-generated or per-instance fabricated.

The plan is never persisted as a separate row -- it is a read-time projection
of the action, so it can never drift out of sync with the action's own
fields. **Human approval (moving the action to `APPROVED`) is required before
the plan is activated**; this module never changes an action's status
itself.

## Dependency and impact analysis (`steward_change_management_service.analyze_dependencies`)

Computed live for every action, covering affected workflows, clinical rules,
policies, required education, integration dependencies, staffing impact,
operational risk, possible service disruption, rollback requirements, and
data/reporting impact.

Actions whose `action_type` changes a workflow or clinical rule (e.g.
`recleaning_workflow_revision`, `policy_revision`) are flagged
`requires_dependency_review_before_publication`.
`assert_dependencies_reviewed_for_publication` raises `ValueError` if such an
action is published without that review having happened.

## Change management plan (`steward_change_management_service.generate_change_management_plan`)

Ten configurable steps: stakeholder identification, leadership sponsorship,
communication, readiness assessment, training, pilot, implementation,
reinforcement, effectiveness review, sustainment -- paired with the action's
current `change_readiness` (`ready` / `partially_ready` / `not_ready` /
`blocked` / `unknown`, set via `set_change_readiness`).

Steward recommends a facility-scoped phased rollout, rather than enterprise-
wide deployment, whenever an action's risk level is high or critical
(`recommend_rollout_scope`).
