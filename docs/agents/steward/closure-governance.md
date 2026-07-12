# Closure Governance

`steward_closure_service.close_action` enforces every closure criterion
before delegating to `steward_action_service.transition_status` (which
itself enforces the role-authority-tier gate for `CLOSED`):

1. **Owner comments recorded** -- `owner_comments` must be non-empty.
2. **Evidence verified** (high-risk only) -- `steward_verification_service.
   has_sufficient_evidence` must be true. A checkbox alone is never
   sufficient for a high-risk action; sufficiency for those actions can only
   come from a real Veritas evidence assessment.
3. **Residual risk documented** (high-risk only) --
   `steward_residual_risk_service.has_reviewed_residual_risk` must be true.
4. **Unintended consequences reviewed** (any risk level) -- no unreviewed
   `GovernedActionUnintendedConsequence` row may exist.
5. **Appropriate approver signs off** -- enforced by the same authority-tier
   check used for approval (manager-tier for standard risk, and the same
   tier for high/critical risk, scope-limited to the approver's own facility
   unless they hold admin/director-tier authority).

Any criterion failing raises `ValueError`, surfaced to the caller as HTTP 422
-- closure is all-or-nothing, never partially applied.

## Closure outcomes

`close_and_sustain`, `close_with_monitoring`, `revise_and_continue`,
`escalate`, `reopen_source_case`, `rollback`.

`reopen_source_case` is a *recommendation* Steward reports back to Council
(see `specialist-integrations.md`) -- Steward never reopens a Council Case
itself.

## Rollback preserves audit history

A `rollback` closure outcome does not delete or rewrite any prior
`GovernedActionAuditEvent`, `GovernedActionVerification`,
`GovernedActionRollout`, or outcome-review row -- the full history remains
reconstructable exactly as it happened.
