# Agent Registry

`app/agents/registry.py` — a static registry of every agent in the
pipeline. `GET /api/agents/registry` returns it; `GET /api/agents/health`
returns the rollup.

## Fields per entry

| Field | Meaning |
|---|---|
| `name` | The agent's display name (e.g. "Instrument Intelligence Agent"). |
| `version` | Semantic version of the agent's logic (`1.0.0` for all ten at Phase 22 launch). |
| `capabilities` | What the agent can do — a short list of its `run()` responsibilities. |
| `depends_on` | Which agent(s) must run first — the pipeline's dependency graph, not just its linear order (most agents depend on exactly the agent before them; some, like Clinical Reasoning, depend on multiple prior agents). |
| `pipeline_position` | 1–10, the agent's position in `PIPELINE_ORDER`. |
| `status` | `"active"` for every agent currently in `PIPELINE_ORDER`. A future agent could be registered as `"disabled"` without being removed from the codebase. |
| `health` | See below. |

## Health checks are honest, not fabricated

Every agent here is deterministic in-process Python — there is no
external service, no network call, no model server to go down. So
"health" does not mean uptime or latency (which would be fabricated
numbers with nothing real behind them). Instead, `_health()` in
`registry.py` does the one thing that's actually true to check: it
imports the real module the agent wraps (e.g. the Instrument Intelligence
Agent's health check imports `app.services.instrument_anatomy`) and
reports `"ok"` if that import succeeds, `"degraded"` if it doesn't. This
is a real, if modest, signal — a broken import in a wrapped service would
surface immediately as `"degraded"` rather than being silently masked.

## Example response

```json
{
  "agents": [
    {
      "name": "Instrument Intelligence Agent",
      "version": "1.0.0",
      "capabilities": ["resolve_instrument_family", "load_anatomy_profile", "check_digital_twin_availability"],
      "depends_on": [],
      "pipeline_position": 1,
      "status": "active",
      "health": "ok"
    }
  ]
}
```

## Extending the registry

To add an eleventh agent: implement it in `app/agents/`, add it to
`PIPELINE_ORDER` and `_WRAPPED_MODULES` in `registry.py`, and wire it into
`orchestrator.py`'s sequence. The registry endpoint and the frontend
Agent Trace viewer (`/agent-trace`) both read `PIPELINE_ORDER` directly —
no separate registration step is needed beyond that.
