# Project Pulse — Operational Replay

LumenAI OS v4.2 — Section 11

## Genuinely new — but built entirely from existing event sources

Confirmed before writing this module: Sentinel's Clinical Scenario
Engine (v2.5) replays a single inspection's what-if scenarios, and
Forge's Simulator (v4.1) replays one workflow against one historical
inspection — neither replays a *time range* of activity across many
inspections, alerts, and decisions at once. `pulse_replay_service.py`
is the first to do that, but it introduces no new event-of-record
table: it composes four sources that already durably record real
events —

| Timeline entry kind | Source |
|---|---|
| `audit` | This platform's existing `AuditLog` (every `_audit(...)` call across every sprint) |
| `event` | Nexus's `NexusEvent` (this sprint's own Live Event Stream, Section 2) |
| `supervisor_decision` | `SupervisorReview` — real agreement/override records |
| `workflow_execution` | Forge's `WorkflowExecution` (non-simulation rows only) |
| `alert` | This sprint's own `PulseAlert` |

— merged into one timeline, sorted by timestamp. Naive/aware datetime
normalization (`_as_naive`) is applied before comparison, the same
pattern established in `insight_forecast_math.py`/`nexus_credential_
service.py` for exactly this class of bug.

## Replay scopes

- **Shift** — `replay_shift(shift_start, shift_hours=8)` — a fixed
  window from a start time.
- **Day** — `replay_day(day_start)` — a 24-hour window.
- **Incident** — `replay_incident(alert_id, window_hours=4)` — centered
  on one `PulseAlert`'s `created_at`, ±`window_hours`; returns `None` if
  the alert doesn't exist (never a fabricated empty timeline for an
  unknown incident).
- **Workflow** — already covered by Forge's own
  `GET /api/forge/workflow-execution/{id}` (decision path + execution
  log); Pulse does not duplicate this, it only adds the broader
  time-range replays above it.

## Endpoints

```
GET /api/pulse/replay/shift?shift_start=<iso>&shift_hours=<n>
GET /api/pulse/replay/day?day_start=<iso>
GET /api/pulse/replay/incident/{alert_id}?window_hours=<n>
```

Every replay response includes `event_count` and the full ordered
`timeline` — nothing is summarized away, since a leadership replay's
whole purpose is seeing exactly what happened, in order.
