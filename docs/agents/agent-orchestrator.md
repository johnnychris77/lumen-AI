# Agent Orchestrator

`app/agents/orchestrator.py::run_pipeline(db, inspection, tenant_id) -> dict`
runs all ten agents in sequence for one real, already-scored `Inspection`
row and returns every agent's output context plus the explainable trace.

Exposed at:
- `GET /api/agents/run/{inspection_id}` — the full result
- `GET /api/agents/trace/{inspection_id}` — just the trace + final
  recommendation (a thinner view for the Explainable Agent Trace UI)

## Execution order

```
1. Instrument Intelligence Agent   (db, tenant_id, instrument_type, manufacturer)
2. Anatomy Intelligence Agent      (InstrumentContext, inspected_zones)
3. Inspection Coverage Agent       (instrument_type, AnatomyContext)
4. Contamination Detection Agent   (instrument_type, detected_issue, confidence, risk_score)
5. Damage Detection Agent          (detected_issue, risk_score)
6. Clinical Reasoning Agent        (InstrumentContext, AnatomyContext, CoverageContext,
                                     ContaminationContext, DamageContext, risk_score)
7. Recommendation Agent            (Inspection row, ClinicalReasoningContext)
8. Supervisor Agent                (db, inspection_id)
9. Continuous Learning Agent       (db, tenant_id)
10. Enterprise Intelligence Agent  (db, tenant_id, facility)
```

Steps 4 and 5 both run off the same inspection's single persisted
`detected_issue` — see the known limitation in
`docs/agents/multi-agent-architecture.md`. Steps 1–7 are effectively
per-inspection; steps 8–10 blend one inspection-scoped question ("has
*this* one been reviewed?") with tenant-wide aggregates (learning
confidence, enterprise rollups) — this mirrors how a real SPD supervisor
would actually reason: "is this instrument OK, *and* how are we doing
overall."

## What the orchestrator does and does not do

**Does:**
- Decode the inspection's `inspected_zones_json` once, upfront, and pass
  the decoded list (or `None`, meaning "not tagged") into the Anatomy
  Agent.
- Instantiate each agent once at module import time (`_AGENTS` dict) —
  agents are stateless, so there's no reason to construct new instances
  per call.
- Record one `AgentTraceEntry`-shaped dict per agent, in order, building
  the Explainable Agent Trace.
- Return `human_review_required: true` on the overall result, in addition
  to whatever each individual context already carries.

**Does not:**
- Retry a failed agent — if an agent's underlying service call raises, the
  whole pipeline run fails loudly (a 500 from the API), rather than
  silently producing a partial or fabricated result.
- Cache results across calls — every `run_pipeline()` call recomputes
  everything live from the current database state, so a trace always
  reflects the instrument's current status, not a stale snapshot.
- Write anything to the database. The orchestrator is read-only; the only
  things that change a real record are the existing supervisor-review and
  QA-review endpoints, which the Supervisor Agent then reports on.

## Adding a new pipeline step

1. Implement the agent in `app/agents/`, following the existing agents'
   shape: `NAME`, `VERSION`, `CAPABILITIES`, `DEPENDS_ON` class attributes
   and a `run()` method that takes typed context objects (plus the narrow
   exceptions documented in `docs/agents/agent-context-schema.md`) and
   returns a new typed context.
2. Add the new context type to `app/agents/context.py`.
3. Add the agent to `PIPELINE_ORDER` and `_WRAPPED_MODULES` in
   `app/agents/registry.py`.
4. Wire the call into `run_pipeline()` in the right position, and append
   its `_trace_entry()` call.
5. Add its output to the `run_pipeline()` return dict.

No route or frontend change is required beyond that — the registry and
trace endpoints read `PIPELINE_ORDER`/the trace list generically.
