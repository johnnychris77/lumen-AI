# Project Pulse — Live Event Stream

LumenAI OS v4.2 — Section 2

## Reuses Nexus's existing event bus — no second bus

`pulse_event_service.py` is a thin wrapper over
`nexus_event_bus_service.publish`/`list_events` (Nexus, v3.2) and
`NEXUS_EVENT_TYPES` (`app/models/nexus_integration.py`) — the same typed
pub/sub layer Genesis and Beacon already extended rather than replaced.

## The ten named event types, mapped

| Sprint's event type | `NEXUS_EVENT_TYPES` constant | Status |
|---|---|---|
| Inspection Started | `EVENT_INSPECTION_STARTED` | New this sprint |
| Image Uploaded | `EVENT_IMAGE_UPLOADED` | New this sprint |
| AI Analysis Completed | `EVENT_AI_ANALYSIS_COMPLETED` | New this sprint |
| Supervisor Review | `EVENT_SUPERVISOR_APPROVED` | Already existed (Nexus v3.2) |
| Knowledge Added | `EVENT_KNOWLEDGE_UPDATED` | Already existed |
| Digital Twin Updated | `EVENT_DIGITAL_TWIN_UPDATED` | Already existed |
| Repair Recommended | `EVENT_REPAIR_RECOMMENDED` | Already existed |
| Enterprise Alert | `EVENT_ENTERPRISE_ALERT_CREATED` | Already existed |
| Workflow Executed | `EVENT_WORKFLOW_EXECUTED` | New this sprint — `forge_execution_service.execute_workflow` now publishes this event (best-effort, non-simulation runs only) on completion |
| Integration Sync | `EVENT_INTEGRATION_SYNC` | New this sprint |

Only five of the ten needed to be added — the other five were already
covered by Nexus's existing vocabulary before Pulse.

## Contextual fields

`publish_pulse_event(db, tenant_id, event_type, *, facility, department,
user_role, instrument, severity, source, actor, extra)` ensures every
published event's payload carries the seven fields Section 2 names
(timestamp is `NexusEvent.created_at` itself; organization is
`tenant_id`) — the frontend never has to guess which payload keys are
present, since the wrapper always sets them (empty string if not
supplied, never omitted).

## Endpoint

```
GET /api/pulse/events?event_type=<optional>&limit=<n>
```

`live_event_stream` decodes each event's `payload_json` into a structured
`payload` dict before returning it — `list_events` itself returns the
raw row shape (payload still JSON-encoded), so this is a genuine, small
value-add over the underlying Nexus function.
