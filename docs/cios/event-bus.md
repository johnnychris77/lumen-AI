# Enterprise Event Bus

`app/cios/event_bus.py` + `app/models/cios_event.py::CIOSEvent` — a
synchronous, in-process event bus that persists real events as the CIOS
orchestrator processes an inspection, reusable by future integrations
(webhooks, notification routing, downstream analytics) without those
integrations needing to re-derive when something clinically significant
happened.

## Event types

| Event | Emitted when |
|---|---|
| `InspectionStarted` | Every CIOS pipeline run, unconditionally. |
| `BaselineLoaded` | `Inspection.baseline_status == "approved_baseline_found"`. |
| `CoverageIncomplete` | Coverage quality is `incomplete`, `insufficient`, or `not_assessed`. |
| `BloodDetected` | The Contamination Detection Agent reports a `blood` finding. |
| `CorrosionDetected` | The Damage Detection Agent reports a `corrosion` finding. |
| `RecommendationGenerated` | Every run, unconditionally — carries the readiness state. |
| `SupervisorApproved` | A real `SupervisorReview` exists, agreement is `agree`/`partially_agree`, and there's no override. |
| `InstrumentRemovedFromService` | The Recommendation Agent's readiness state is `REMOVED_FROM_SERVICE`. |
| `KnowledgeUpdated` | Reserved for a future release where a supervisor correction triggers an explicit knowledge-base update (not yet wired — see Known Limitations below). |
| `ModelFeedbackCaptured` | A Phase 18 `PilotValidationCase` (training label) was created for this inspection. |

## Honesty constraint

**No event fires unless the condition it names is actually true in the
current context.** `BloodDetected` is not emitted just because the
pipeline ran on a "blood-capable" instrument family — it only fires when
the Contamination Detection Agent's real output contains a `blood`
finding for *this* inspection. Same for every other conditional event.

## Known limitation: `KnowledgeUpdated`

This event type is defined in `EVENT_TYPES` for forward-compatibility with
the event schema, but nothing currently emits it — there is no live
process today that mutates a persisted knowledge-base artifact in
response to a supervisor correction (Phase 21's `learning_confidence()`
recomputes fresh from real reviews on every call; it doesn't write back to
`InstrumentKnowledge` or the anatomy/zone taxonomy). Wiring
`KnowledgeUpdated` up is future work, tracked here rather than faked with
a fabricated emission.

## Storage and querying

Every event is a real row in `cios_events`
(`tenant_id`, `inspection_id`, `event_type`, `payload_json`, `created_at`).
`GET /api/cios/events?inspection_id=<id>` returns the real event history
for one inspection; omit `inspection_id` for the tenant's recent event
stream. This is intentionally a simple relational table, not a message
queue — LumenAI doesn't need at-least-once delivery semantics for an
audit-oriented event log; it needs a queryable, permanent record.

## Future integrations

A webhook dispatcher, a Slack/email notifier for `InstrumentRemovedFromService`
or `BloodDetected`, or a downstream analytics pipeline could all subscribe
to `cios_events` (via polling the table today; a real pub/sub layer is
future work) without touching the orchestrator itself — the event bus is
the deliberate seam for that.
