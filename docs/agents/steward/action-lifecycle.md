# Action Lifecycle

## Statuses

`DRAFT -> PENDING_APPROVAL -> APPROVED -> READY_TO_START -> IN_PROGRESS`, with
`BLOCKED`, `AT_RISK`, `AWAITING_EVIDENCE`, and `AWAITING_VERIFICATION` as
side-states, resolving to `COMPLETED_PENDING_REVIEW -> SUSTAIN / REVISE /
ESCALATE -> CLOSED`, or `CANCELLED` at any point. `CLOSED` and `CANCELLED` are
terminal -- `steward_action_service.transition_status` refuses any further
transition on a terminal action (mirroring Council's "reconvening a resolved
case" invariant).

## No action begins without an approved source decision

`steward_action_service.create_action` requires a non-empty `source_decision`,
a non-empty `approved_by`, and a non-null `approval_timestamp` -- an
unapproved recommendation cannot activate an action; the call raises
`ValueError` instead.

## Role-authorized transitions

Every transition is audited (`GovernedActionAuditEvent`), but only `APPROVED`,
`CLOSED`, and `CANCELLED` are *gated* by authority tier -- the rest (moving to
`IN_PROGRESS`, `BLOCKED`, `AT_RISK`, etc.) are operational tracking, not
re-authorization, and only require a valid tenant role.

Authority tiers reuse Council's exact `ROLE_AUTHORITY_TIER` mapping
(`council_leadership.ROLE_AUTHORITY_TIER`), since the underlying RBAC is still
only four real roles (`viewer`/`operator` = tier 0, `spd_manager` = tier 2,
`admin` = tier 4):

| Operation | Standard-risk tier | High/critical-risk tier |
|---|---|---|
| Approve | 1 | 2 |
| Close | 1 | 2 |

A non-admin-tier approver is additionally scope-limited to their own
facility: approving or closing an action outside their configured facility
requires director/executive-tier (`admin`) authority.

## Owner and accountable leader required to start

`READY_TO_START` cannot be reached until both `owner` and
`accountable_leader` are set (`steward_action_service.assign_owner`).

## Scope cannot expand without new authorization

Editing `action_description`, `category`, or `action_type` after creation
(`steward_action_service.update_scope`) requires manager-tier-or-above
authority -- the same threshold as approving a standard-risk action.
