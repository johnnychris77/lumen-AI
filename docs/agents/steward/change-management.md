# Change Management & Phased Rollout

## Naming note: "rollout," never "pilot"

`pilot` is a heavily-loaded, pre-existing namespace in this codebase
(`app/models/pilot.py`, `pilot_config.py`, `pilot_error_log.py`,
`app/routes/pilot*.py`) meaning a *customer/product deployment pilot* -- an
entirely different concept from this brief's "pilot rollout" of one governed
action. To avoid a permanent, confusing collision, Steward uses
**`GovernedActionRollout`** / `rollout_scope` throughout instead of any
`pilot_*` symbol. The brief's own vocabulary ("single-instrument pilot",
"facility pilot", etc.) survives only as data values in `ROLLOUT_SCOPES`,
never as a Python or table identifier.

## Rollout scopes

`single_instrument`, `single_workflow`, `shift`, `department`, `facility`,
`market`, `enterprise` -- narrowest to broadest.

## Tracking (`steward_rollout_service`)

Each `GovernedActionRollout` row records scope, start date, baseline metrics,
expected result, actual result, adverse effects, user feedback, and a
go/no-go decision.

**No rollout automatically advances to a broader scope.**
`record_go_no_go` only ever records the decision on that rollout row; a
caller must separately create the next, broader-scope rollout via
`create_rollout` -- there is no code path that escalates scope on its own.

## Change readiness

`ready`, `partially_ready`, `not_ready`, `blocked`, `unknown` -- tracked per
action and surfaced on every workspace/board view and the Change Readiness
Report.
