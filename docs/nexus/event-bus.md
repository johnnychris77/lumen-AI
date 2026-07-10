# Project Nexus — Event Bus

LumenAI v3.2 — Section 6

## Endpoints

```
POST /api/nexus/events/publish
GET  /api/nexus/events
POST /api/nexus/events/subscriptions
GET  /api/nexus/events/subscriptions
POST /api/nexus/events/subscriptions/{id}/deactivate
```

## The first typed publish/subscribe layer in this codebase

Two mechanisms already exist that look adjacent but aren't pub/sub:

- **`app/audit.py::log_audit_event`** — a direct DB insert into `AuditLog`
  at each call site. No subscribers, no typed catalog.
- **`app/automation_engine.py`** (via `app/event_dispatcher.py::dispatch_event`)
  — a synchronous, per-tenant condition engine: `AutomationRule` rows are
  polled and evaluated against a `trigger_type` + payload on every
  `dispatch_event` call. Closer to a rules engine than a bus — no typed
  event catalog, no subscriber registry, no delivery tracking.

`nexus_event_bus_service.py` adds both without replacing either:

```python
def publish(db, *, tenant_id, event_type, payload, actor="system") -> dict:
    ...  # 1. persist NexusEvent
    ...  # 2. best-effort dispatch_event() — existing AutomationRules still fire
    ...  # 3. deliver to active NexusEventSubscriptions, track delivery count
```

## Seven named event types

`NEXUS_EVENT_TYPES` (`app/models/nexus_integration.py`):
`InspectionCompleted`, `SupervisorApproved`, `RepairRecommended`,
`KnowledgeUpdated`, `BaselinePublished`, `DigitalTwinUpdated`,
`EnterpriseAlertCreated` — exactly the catalog the sprint specifies.
`publish()` rejects any other `event_type` with a 422.

## Subscribers

`NexusEventSubscription` supports two target types:

- **`internal`** — a named internal handler string. Delivery is recorded
  as soon as the event is persisted (the subscriber is expected to poll
  `GET /api/nexus/events` or react to the same DB row another way) —
  there's no in-process callback registry in this iteration.
- **`webhook`** — an HTTP POST to `target`, best-effort
  (`_deliver_webhook`): a failed or unreachable webhook is caught and
  logged as a non-delivery, and never raises back into `publish()` — a
  down subscriber must never block publishing, block the automation-rule
  dispatch, or affect any other subscriber.

Every `NexusEvent` row records `subscriber_delivery_count` — how many
active subscriptions for that event type were actually notified,
independent of whether any `AutomationRule` also fired on the same
trigger.

## Backward compatibility with existing automation rules

`publish()` calls `app/event_dispatcher.py::dispatch_event(db,
trigger_type=event_type, ...)` for every published event, wrapped in a
try/except so a rule-engine exception never rolls back the already-
persisted `NexusEvent`. Any `AutomationRule` already configured against
one of these trigger types (e.g. an existing Slack/email notification
rule) continues to fire exactly as before Nexus existed — Nexus's event
bus is additive on top of the rule engine, not a replacement for it.

## Future integrations subscribe to events

The sprint's explicit intent — "future integrations subscribe to events"
— is served by `POST /api/nexus/events/subscriptions`: any connector (or
an internal LumenAI feature) registers interest in a named event type
without the publisher needing to know who's listening. A connector row
(`connector_id`) is optional on a subscription — a subscription can be a
platform-level feature with no specific external system attached.
