# Policy Simulation

Implemented in `app/services/policy_simulation_service.py::simulate_policy()`.

## What it does

Before a threshold change becomes the active policy, replays a candidate
set of thresholds against every historical `LumenDecisionRecord` in scope
(optionally filtered by instrument family, anatomy zone, or facility) and
reports:

- `inspections_evaluated` / `inspections_affected`
- `previously_continued_now_requires_review`
- `previously_reviewed_now_technician_managed`
- `probable_contamination_cases` (always recomputed as still requiring
  recleaning under the candidate thresholds — Section 4 is never
  simulated away)
- `false_escalation_estimate` (only where the underlying data supports it)
- `supervisor_workload_delta`
- `instrument_family_impact` / `anatomy_zone_impact` / `facility_impact`

## What it never does

`modifies_historical_records` is always `false` in the response — the
function only reads `LumenDecisionRecord` rows and never writes to them or
to `Inspection`. Regression-tested in
`test_lumen_decision_engine.py::TestPolicySimulation::test_simulation_is_read_only`,
which asserts the record count is identical before and after a simulation
call.

## Publication remains separate

`requires_authorized_publication` is always `true` — a simulation result,
however favorable, does not itself activate anything. Publishing a new
threshold still requires the full governance lifecycle in
`baseline_decision_policy_service.py` (draft → submit → approve →
activate), each step role-gated to `admin`/`spd_manager`.

## Route

`POST /api/decision-policies/simulate` (`admin`/`spd_manager` only).
