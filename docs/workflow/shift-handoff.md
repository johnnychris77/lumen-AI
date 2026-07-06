# Shift Handoff & Daily Operations

## Daily Operations Dashboard (Deliverable 8)

`GET /api/workflow/daily-dashboard`

A same-day rollup: inspections created/completed today, pending count,
high-risk findings, average inspection time, supervisor/repair backlog, and
how many inspections are ready for packaging right now. Built entirely from
the Smart Inspection Queue and SLA Monitoring services — no separate
computation.

## Shift Handoff Report (Deliverable 9)

`GET /api/workflow/shift-handoff` (admin/spd_manager only)

Generates a real-time snapshot for the next shift:

- **Outstanding inspections** — the full pending queue.
- **Critical instruments** — high-risk queue items.
- **Pending supervisor reviews** — queue items awaiting a supervisor
  decision.
- **Repair holds** — queue items currently in the `Repair` workflow state.
- **Escalations** — every inspection that meets at least one escalation
  rule, with the specific reason(s).
- **OR priorities** — queue items tied to an emergency/trauma/first-case
  procedure.

The report is generated on demand from live data — there is no separate
"handoff snapshot" storage to go stale between shifts.

## Notification Framework (Deliverable 10)

`GET /api/workflow/notifications`, `POST /api/workflow/notifications/generate`,
`POST /api/workflow/notifications/{id}/read`

An in-app, per-role notification queue (`WorkflowNotification`) — distinct
from the existing Slack/Teams/email `AlertEvent` dispatcher
(`app/notifications/notifier.py`), which is for external critical-finding
alerts unrelated to per-inspection workflow tracking.

Notification types generated from real queue/escalation state:

| Type | Trigger | Recipient |
|---|---|---|
| `inspection_assigned` | A technician is assigned | That technician |
| `supervisor_review_required` | Inspection enters Supervisor Review | spd_manager |
| `critical_finding` | Inspection is in the high-risk queue | spd_manager |
| `repair_recommendation` | Inspection is in the repair queue | spd_manager |
| `inspection_overdue` | Waiting > 8 hours | spd_manager |
| `coverage_incomplete` | Coverage < 75% | operator |

Generation is idempotent per inspection + notification type — re-running
`POST /api/workflow/notifications/generate` never duplicates an
already-emitted notification.

## Operational Analytics (Deliverable 11)

`GET /api/workflow/analytics?days=30` (admin/spd_manager only)

Inspection throughput, per-technician productivity (completed-inspection
counts), queue aging (average/max minutes waiting), average turnaround,
high-risk workload, and workload balance (min/max/spread of open
assignments across technicians) — all derived from the queue, SLA, and
workload services above.
