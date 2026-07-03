# Explainable Agent Trace

## What it shows

For any real inspection, `GET /api/agents/trace/{inspection_id}` (and the
`/agent-trace` frontend page) shows exactly which agent produced which
decision, in order:

```
Instrument Agent
    ↓
Rigid Scope
    ↓
Anatomy Agent
    ↓
O-ring
    ↓
Contamination Agent
    ↓
Blood
    ↓
Reasoning Agent
    ↓
High retention
    ↓
Recommendation Agent
    ↓
Reprocess
```

This is not a separate explanation system bolted onto the pipeline — it
*is* the pipeline. Every `AgentTraceEntry` (see
`docs/agents/agent-context-schema.md`) is recorded as each agent actually
runs inside `run_pipeline()`, so the trace can never drift from what
really happened; there's no separate "explain this after the fact" code
path that could tell a different story than the real one.

## Trace entry shape

```json
{
  "agent": "Contamination Detection Agent",
  "version": "1.0.0",
  "input_summary": {"detected_issue": "blood"},
  "output_summary": {
    "findings": [{"finding_type": "blood", "zone": "hinge", "severity": "high", ...}],
    "has_contamination": true
  }
}
```

`input_summary` is a small, human-readable digest of what the agent was
given — not the full upstream context (which would be redundant with the
previous entry's `output_summary`). `output_summary` is the agent's full
typed context, serialized.

## Reading a trace end to end

1. **Instrument Intelligence Agent** — resolves what instrument this is.
2. **Anatomy Intelligence Agent** — resolves its zones and what's missing.
3. **Inspection Coverage Agent** — how complete was this inspection's
   image capture.
4. **Contamination Detection Agent** / **Damage Detection Agent** — what
   was actually found (at most one of these two will be non-empty per the
   current schema — see `docs/agents/multi-agent-architecture.md`).
5. **Clinical Reasoning Agent** — the plain-language interpretation and
   the full ontology reasoning chain (reuses
   `docs/knowledge-graph/reasoning-engine.md`'s chain).
6. **Recommendation Agent** — the final packaging-readiness state and why.
7. **Supervisor Agent** — has a human already weighed in on this one?
8. **Continuous Learning Agent** — how much should we trust the current
   knowledge base, given how many real reviews back it up right now?
9. **Enterprise Intelligence Agent** — where does this fit in the bigger
   picture (facility readiness, most common contamination type this
   tenant sees).

## Why this replaces "I detected blood."

Before this pipeline existed, an inspection's output was one field:
`detected_issue = "blood"`. After it, a supervisor (or an auditor, or a
new hire being trained) can expand every step and see *why* the system
landed on its recommendation — which zone, which retention risk, which
clinical rule, which prior reviews inform the current confidence level.
This is the same transparency goal as Phase 21's "Why?" explainability
graph (`docs/knowledge-graph/reasoning-engine.md`), extended across the
*entire* pipeline rather than just the finding-to-recommendation step.

## Honesty about what the trace is not

The trace is not a live multi-agent conversation, a chain-of-thought log
from an LLM, or evidence of autonomous agent negotiation. It is an
ordered, structured record of ten deterministic function calls. That's
precisely why it's trustworthy as an audit artifact — every line in it
corresponds to a real, testable, reviewable piece of code
(`backend/tests/test_agents_pipeline.py`).
