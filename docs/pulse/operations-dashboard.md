# Project Pulse — Notification Center & Command Widgets

LumenAI OS v4.2 — Sections 10 & 12

## Notification Center (Section 10)

`pulse_notification_center_service.py` composes what already exists
rather than building a second delivery layer:

- **Slack / Teams / Email** — `app/notifications/notifier.py::
  dispatch_alert` already has real, working, env-flag-gated dispatch for
  all three; reused as-is.
- **Webhook** — Nexus's `NexusEventSubscription` (`SUBSCRIPTION_TARGET_
  WEBHOOK`, `nexus_event_bus_service._deliver_webhook`) already does
  generic webhook delivery.
- **SMS** — confirmed zero existing SMS code anywhere in this codebase.
  `send_sms` is an explicit, logged stub (`sent: False`, with a clear
  reason) — never a fabricated "sent" result for a channel this
  deployment cannot actually reach.
- **In-app** — the unified feed itself (Genesis's
  `platform_notification_service.unified_notifications`).

### "Rules configurable through Project Forge"

Implemented as Pulse *consuming* Forge's existing rule engine
(`forge_rule_engine.evaluate_all_rules`) rather than Forge depending on
Pulse — dependencies in this branch only ever point from a newer sprint
to an older one, never the reverse, so Forge's own model and action
constants are never modified by this file. `route_notification`
evaluates every approved rule against a context; for each match whose
action `type` is `notify_supervisor` or `escalate` and whose `params`
include a `channel`, it dispatches through that channel.

```
GET  /api/pulse/notifications
POST /api/pulse/notifications/route     — {"context": {...}}
POST /api/pulse/notifications/send      — {"channel": "slack", "title": "...", "message": "..."}
```

## Command Widgets (Section 12)

`PulseWidget` is a seeded catalog of the nine named widgets (Inspection
Counter, Queue Heatmap, Facility Status, AI Health, Knowledge Growth,
Digital Twin Status, Enterprise Alerts, Trend Chart, Forecast Widget),
each recording which real service backs it (`data_source`).
`PulseDashboardLayout` follows the exact per-user personalization idiom
Genesis's `PlatformFavoriteModule`/`PlatformRecentModule` already
established, applied to widget arrangement — a user with no saved
layout gets a real, computed default grid (three columns, one widget
per cell in catalog order), never an empty screen.

```
GET  /api/pulse/widgets
GET  /api/pulse/dashboard-layout?is_mobile=<bool>
POST /api/pulse/dashboard-layout
```

`is_mobile` is a separate saved layout per user (Section 13's
personalization for the mobile view), not a CSS-only distinction.
