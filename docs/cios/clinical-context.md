# Shared Clinical Context

`app/cios/context.py::ClinicalContext` — one immutable object every CIOS
module reads and returns an updated copy of.

## Why immutable

`ClinicalContext` is a frozen pydantic model
(`model_config = ConfigDict(frozen=True)`). Attempting `ctx.field = value`
raises a validation error. The only way to "update" a context is
`ctx.with_updates(field=value)`, which returns a **new** `ClinicalContext`
via `model_copy(update=...)` — the original is untouched.

This mirrors a pattern already established throughout the platform:
`AuditLog` rows are never edited, `PilotValidationCase` ground truth is
never rewritten, `ClinicalDecisionLedgerEntry` rows are append-only. A
mutable shared context would be the one place in the system where "what
did the AI actually see" could quietly change underneath an audit trail.
Immutability closes that gap structurally, not just by convention.

## Fields

| Field | Source |
|---|---|
| `inspection_id`, `tenant_id` | The real `Inspection` row |
| `instrument_type`, `manufacturer`, `model`, `instrument_family` | Instrument Intelligence Agent (Phase 22) |
| `anatomy_profile`, `inspection_zones` | Anatomy Intelligence Agent |
| `coverage` | Inspection Coverage Agent |
| `baseline` | `Inspection.baseline_status` / `baseline_source` |
| `findings` | Contamination Detection Agent + Damage Detection Agent, concatenated |
| `severity` | The first finding's severity, if any |
| `risk` | Clinical Reasoning Agent's risk level/score |
| `recommendation` | Recommendation Agent |
| `supervisor_review` | Supervisor Agent |
| `digital_twin` | Instrument Intelligence Agent's `digital_twin_available` flag |
| `knowledge_graph_links` | The Clinical Reasoning Agent's reasoning chain (Phase 21 knowledge graph) |
| `audit` | The governance version snapshot active when this context was built |

## Who builds it

Only `app/cios/orchestrator.py::_build_clinical_context` constructs a
`ClinicalContext` — it assembles one from the Phase 22 agent pipeline's
output after that pipeline has already run. No individual agent
constructs or mutates a `ClinicalContext` directly; agents still use their
own typed contexts (`app/agents/context.py`) internally, exactly as
specified in Phase 22 — `ClinicalContext` is the *envelope* the
orchestrator wraps around all of them for downstream consumers (the
dashboard, the certificate, the timeline) that shouldn't need to know
about ten separate agent-specific shapes.

## Every module receives the same context

Concretely: the Clinical Readiness Certificate generator, the CIOS
dashboard aggregator, and the Explainable Inspection Timeline all read
fields off the *same* `ClinicalContext` object produced by one
`run_cios_pipeline()` call — they never re-derive instrument identity,
anatomy, or findings independently. If two of them ever disagreed about
what instrument this inspection was, that would be a bug in
`_build_clinical_context`, not a data-consistency issue spread across
three separate code paths.
