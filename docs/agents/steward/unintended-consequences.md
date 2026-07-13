# Unintended Consequence Monitoring

`steward_unintended_consequence_service.flag_consequence` records one
consequence per row (`GovernedActionUnintendedConsequence`) and, if the
action is not already in a terminal state, moves its status to `AT_RISK` so
it surfaces on every workspace and board view until reviewed.

## Monitored consequence types

`new_workflow_bottleneck`, `increased_inspection_time`,
`increased_supervisor_workload`, `new_image_quality_problem`,
`increased_evidence_overrides`, `reduced_throughput`,
`increased_repair_referrals`, `user_confusion`, `risk_displacement`.

## Flagging never rewrites history

Flagging a consequence only ever *adds* a new row -- it never edits or
deletes the action's existing implementation history (audit trail,
verifications, rollout results). `review_consequence` marks a row reviewed
and records notes, but the original flag and its supporting evidence remain
exactly as recorded.

## Closure gate

`steward_closure_service.close_action` refuses to close any action (any risk
level) that has an unreviewed unintended consequence.
