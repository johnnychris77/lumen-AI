# Future AI Agent Architecture (Phase 21 §10)

## Objective

Prepare the knowledge graph so a future set of specialized agents can
consume the same ontology without each one re-implementing its own
version of instrument/anatomy/finding knowledge. This document describes
the intended agent boundaries — no agent orchestration code ships in
Phase 21; the knowledge graph service functions are written so each
agent's eventual responsibility maps to one existing function, not a
rewrite.

## Why one shared ontology matters

Every agent below would otherwise be tempted to hold its own copy of
"what zone is high-risk" or "what does blood mean clinically." That's
exactly the disconnected-features failure mode Phase 19.5 exists to
prevent (`docs/architecture/lumenai-clinical-intelligence-architecture.md`).
Instead, every agent is expected to call into the same knowledge graph
service (`app/services/knowledge_graph_service.py`) and the modules it
composes (`instrument_anatomy.py`, `instrument_zones.py`,
`cleaning_knowledge.py`, `clinical_mentor.py`,
`instrument_family_profiles.py`) — never a parallel implementation.

## Planned agents and their ontology touchpoints

| Agent | Responsibility | Reads from |
|---|---|---|
| **Instrument Agent** | Resolves instrument identity (family, manufacturer, model) from capture metadata/UDI/barcode. | `instrument_anatomy.py::resolve_family`, `app/models/instrument_registry.py`, `app/models/baseline_library.py` |
| **Anatomy Agent** | Determines anatomy zones, required views, and coverage for a resolved instrument. | `instrument_anatomy.py::anatomy_profile`, `app/services/inspection_coverage.py` |
| **Inspection Agent** | Runs/coordinates the capture + scoring workflow for one inspection. | `app/services/baseline_comparison_scoring_service.py`, `app/routes/inspections.py` |
| **Clinical Reasoning Agent** | Produces the traceable chain and explanation for a finding. | `knowledge_graph_service.py::reasoning_chain`, `explain_inspection` |
| **Supervisor Agent** | Surfaces the right queue items to the right human at the right time. | `app/services/pre_sterilization_command_center_service.py` (Modules 5/6/9), `app/models/supervisor_review.py` |
| **Executive Agent** | Rolls up readiness, risk, and analytics for leadership consumption. | `pre_sterilization_command_center_service.py::executive_risk_dashboard`, `knowledge_graph_service.py::enterprise_knowledge_analytics` |
| **Knowledge Graph Agent** | Answers ad hoc exploratory queries across the ontology (manufacturer/instrument/model/finding/zone/failure mode/recommendation/supervisor learning). | `knowledge_graph_service.py::explore` |

## Design constraints for future agents

1. **No agent invents its own instrument/zone/finding vocabulary.** All
   must resolve through the functions above so a "hinge" means the same
   thing to the Supervisor Agent as it does to the Clinical Reasoning
   Agent.
2. **No agent auto-disposes an instrument.** Per Design Principle 4
   (`docs/architecture/design-principles.md`), every agent's output is
   advisory; only a Supervisor Review changes an instrument's actual
   disposition.
3. **Every agent action that touches a real record creates an audit
   event**, consistent with the platform-wide requirement (see
   `app/audit.py::log_audit_event`, used throughout Phases 15–21).
4. **An agent's "learning" always routes through the real ground-truth
   path** — `PilotValidationCase` (Phase 18) — not a private feedback
   loop. `learning_confidence()` in `knowledge_graph_service.py` is the
   read-only view any future agent should query to know how much to trust
   the current knowledge base, rather than maintaining its own confidence
   state.
5. **Agents are additive, not a replacement for the deterministic
   knowledge functions.** An agent framework (should one be introduced)
   should orchestrate calls into the existing services — the services
   themselves remain the source of truth, testable independent of any
   agent runtime.

## What ships now vs. later

Phase 21 ships the knowledge graph, reasoning engine, explorer, and
analytics that every one of these agents would need to call into. It does
not ship an agent orchestration framework, agent-to-agent messaging, or
autonomous multi-step agent workflows — those are explicitly future work,
gated on this ontology being stable and validated first.
