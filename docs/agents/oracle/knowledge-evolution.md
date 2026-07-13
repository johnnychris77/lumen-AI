# Knowledge Evolution

## Governance-gated, never a direct write

A promoted `OracleKnowledgeSuggestion` never writes `KnowledgeArticle`
directly. `oracle_knowledge_evolution_service.create_suggestion` creates the
suggestion row *and* a `GovernanceApproval` row (`request_type=
"oracle_knowledge_evolution"`, `target_resource=
"oracle_knowledge_suggestion"`) -- the same generic governance-approval
table Steward and the pre-existing `app/routes/governance_approvals.py`
use.

## Approval requires leadership authority

`approve_suggestion` requires
`ROLE_AUTHORITY_TIER[reviewer_role] >= TIER_APPROVE_KNOWLEDGE_SUGGESTION`
(tier 2, manager-or-above -- the same convention Steward and Council use for
their own high-authority gates), enforced both at the route
(`require_tenant_roles("admin", "spd_manager")`) and inside the service.

On approval, the linked `GovernanceApproval` is marked `approved` and a real
`KnowledgeArticle` is created via `knowledge_repository_service.create_article`
-- but with `approval_status="pending_review"`, not `"approved"`. The
article still needs a knowledge editor's separate editorial review through
the existing `knowledge_governance_service` workflow; Oracle's governance
approval authorizes the article's *existence*, not its final editorial
sign-off. `mark_published` observes that the linked article reached
`approval_status="approved"` and moves the suggestion to `published` --
Oracle never sets `approval_status` itself.

## Rejection

`reject_suggestion` requires the same leadership tier, marks the linked
`GovernanceApproval` `rejected` with `review_notes`, and moves the
suggestion to `rejected`. Only a `pending` suggestion can be approved or
rejected.

## Legacy-role anomaly, not repeated here

One pre-existing route (`governance_approvals.py`) gates on legacy
`"tenant_admin"`/`"site_admin"` roles that don't exist in the modern 4-role
RBAC. Oracle's knowledge-evolution routes always use the modern roles
(`admin`, `spd_manager`) and never the legacy ones.
