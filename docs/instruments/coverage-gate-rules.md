# AI Analysis Gate & Coverage Override Rules (v1.2)

Governs whether an inspection with incomplete anatomy-zone coverage can reach
a final AI decision, and how a supervisor/admin can override that gate with a
documented reason.

## Default behavior: non-blocking

By default (`REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION` unset/false), the
AI Analysis Gate never blocks inspection creation or the AI's decision —
matching the v1.1 "advisory, not a gate" default (see
`docs/instruments/coverage-engine.md`). Incomplete coverage only produces a
warning banner and missing-image guidance.

## Org policy: requiring full coverage

Setting the env var `REQUIRE_FULL_COVERAGE_BEFORE_FINAL_DECISION=true`
(`backend/app/config.py`) makes the gate binding: an inspection with
`coverage_status` of `incomplete` or `insufficient` is created with
`coverage_gate_status="blocked_pending_override"` rather than `"ready"`.

## Gate states (`Inspection.coverage_gate_status`)

| State | Meaning |
|---|---|
| `ready` | Coverage is complete/acceptable, org policy doesn't require full coverage, or a supervisor override has been applied. |
| `draft` | Not currently persisted as a distinct gate state — a technician can instead set `save_as_draft=true` at creation (persisted as `Inspection.is_draft`) to explicitly flag the record as provisional regardless of the gate. |
| `blocked_pending_override` | Org policy requires full coverage, coverage is incomplete/insufficient, and no override has been recorded yet. |

## Source of truth

`backend/app/services/guided_capture.py::coverage_readiness()` computes the
gate; `backend/app/routes/inspections.py`'s `create_inspection` calls it at
creation time and persists `coverage_status`, `coverage_score`,
`coverage_gate_status`, and `is_draft` onto the `Inspection` row (a snapshot,
so history/dashboards don't need to recompute it).

## Supervisor Override

`POST /api/inspections/{id}/coverage-override` (`admin`/`spd_manager` only,
`backend/app/routes/guided_capture.py`) — requires a `reason` of at least 10
characters (matching the existing baseline-override pattern). Sets
`coverage_override_reason`/`coverage_override_by`/`coverage_override_at`,
moves `coverage_gate_status` to `"ready"`, clears `is_draft`, and is
audit-logged (`compliance_flag=True`) as `coverage_override_applied`.

The override does not change the coverage score or status — it only unlocks
the gate, with a permanent, attributed reason.

## Frontend

- `frontend/src/components/GuidedCapturePanel.tsx` — shows the gate banner
  when `ready_for_ai_analysis` is false.
- `frontend/src/components/CoverageOverridePanel.tsx` — the override form,
  rendered in `NewInspectionPage.tsx` when the created inspection's
  `coverage_gate_status === "blocked_pending_override"`.
- A "Save as draft" checkbox in `NewInspectionPage.tsx` sends
  `save_as_draft: true`, independent of org policy.
