# Project Forge — Workflow Simulator

LumenAI OS v4.1 — Section 8

## Real replay, not a mock

`forge_simulation_service.simulate_workflow` calls the exact same
`forge_execution_service.execute_workflow` engine a live trigger would
use, against a real, already-recorded `Inspection` row (and its
`InspectionFinding`s) — `is_simulation=True` is the only difference,
recorded on the resulting `WorkflowExecution` row so simulated runs are
clearly distinguishable from real ones in `/workflow-history` and never
mistaken for an actual automated action having been taken.

Because a simulation runs the real engine, its automation actions (CAPA
creation, knowledge draft creation, watchlist entries, etc.) are also
real — simulating a decision path without also exercising its actions
would defeat the purpose of validating a workflow before publishing it.
Organizations should generally simulate against non-production tenants
or already-resolved historical inspections for this reason (documented
directly in the service module's docstring).

## What's displayed

| Sprint's requirement | Source |
|---|---|
| Expected outcome | Caller-supplied `expected_outcome` string, recorded on the execution row |
| Actual outcome | `WorkflowExecution.actual_outcome` — the execution's real final status |
| Decision path | `WorkflowExecution.decision_path_json` — the ordered list of node keys actually visited, including which branch a Conditional Branch/Coverage Check node took |
| Execution time | `WorkflowExecution.execution_time_ms` — real wall-clock time measured with `time.monotonic()` around the walk, never a fabricated estimate |

`simulate_workflow`'s response also includes `outcome_matched` — `true`/
`false` if an `expected_outcome` was supplied, `null` if the caller chose
not to supply one (never guessed).

## Endpoint

```
POST /api/forge/workflow-execution/simulate
  {"workflow_id": <id>, "inspection_id": <id>, "expected_outcome": "..."}
```

## "Replay approvals / routing"

If the simulated workflow reaches an Approval node, a real
`WorkflowApprovalInstance` is started (see
`docs/forge/workflow-builder.md`'s Approval node section) — the
simulation exercises the same approval-chain machinery Section 7 defines,
it does not stub it out.
