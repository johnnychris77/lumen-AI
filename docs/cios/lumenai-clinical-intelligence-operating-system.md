# LumenAI Clinical Intelligence Operating System (CIOS)

## Objective

Unify every LumenAI module — Instrument Intelligence, Anatomy
Intelligence, Computer Vision, Clinical Knowledge, Clinical Reasoning,
Supervisor Validation, Digital Twin, Enterprise Intelligence — into one
coordinated operating system for Sterile Processing, so LumenAI behaves
like an experienced SPD leadership team working together before an
instrument proceeds to packaging and sterilization, rather than a
collection of disconnected AI features.

## Core principle: one deterministic workflow

Every inspection follows the same operating sequence. No module bypasses
another:

```
Image
    ↓
Instrument Identification
    ↓
Anatomy Recognition
    ↓
Inspection Coverage
    ↓
Baseline Comparison
    ↓
Finding Detection
    ↓
Severity Classification
    ↓
Zone Risk Assessment
    ↓
Clinical Reasoning
    ↓
Clinical Recommendation
    ↓
Supervisor Validation
    ↓
Learning
    ↓
Enterprise Analytics
```

## What CIOS actually is

CIOS is **not a rewrite** of Phases 15–22. It is the coordination layer
that sits on top of the Phase 22 multi-agent pipeline
(`app/agents/orchestrator.py::run_pipeline`) and adds exactly what a real
operating system adds to a set of programs: a shared context, a single
entry point, execution monitoring, formal state, a permanent decision
record, an event bus, and governance.

`app/cios/orchestrator.py::run_cios_pipeline(db, inspection, tenant_id)`
is the **single entry point**. Every consumer — the API, the `/cios-dashboard`
frontend, the Clinical Readiness Certificate generator — calls this one
function. Nothing calls an individual agent directly outside of it.

## The eleven CIOS components

| # | Component | Module | Doc |
|---|---|---|---|
| 1 | Clinical Intelligence Orchestrator | `app/cios/orchestrator.py` | this document |
| 2 | Shared Clinical Context | `app/cios/context.py` | `docs/cios/clinical-context.md` |
| 3 | Intelligence Pipeline Monitor | `app/cios/orchestrator.py::_pipeline_monitor` | this document, §3 below |
| 4 | Inspection State Machine | `app/cios/state_machine.py` | `docs/cios/inspection-state-machine.md` |
| 5 | Clinical Decision Ledger | `app/cios/decision_ledger.py`, `app/models/clinical_decision_ledger.py` | `docs/cios/clinical-decision-ledger.md` |
| 6 | Enterprise Event Bus | `app/cios/event_bus.py`, `app/models/cios_event.py` | `docs/cios/event-bus.md` |
| 7 | Explainable Inspection Timeline | `app/cios/orchestrator.py::_timeline` | `docs/cios/clinical-decision-ledger.md` (shares the ledger's audit framing) |
| 8 | Clinical Readiness Certificate | `app/cios/certificate.py` | this document, §8 below |
| 9 | Enterprise Health Dashboard | `app/cios/dashboard.py`, `/cios-dashboard` | this document, §9 below |
| 10 | Platform Governance | `app/cios/governance.py` | `docs/cios/platform-governance.md` |
| 11 | Clinical Rule Registry | `app/cios/rule_registry.py` | `docs/cios/clinical-rule-registry.md` |

## §3 Intelligence Pipeline Monitor

Every CIOS run returns a `pipeline_monitor` list — one entry per Phase 22
agent, each `Complete`, `Pending`, or `Queued`:

```json
[
  {"agent": "Instrument Agent", "status": "Complete"},
  {"agent": "Anatomy Agent", "status": "Complete"},
  {"agent": "Coverage Agent", "status": "Complete"},
  {"agent": "Contamination Agent", "status": "Complete"},
  {"agent": "Damage Agent", "status": "Complete"},
  {"agent": "Clinical Reasoning Agent", "status": "Complete"},
  {"agent": "Recommendation Agent", "status": "Complete"},
  {"agent": "Supervisor Agent", "status": "Pending"},
  {"agent": "Learning Agent", "status": "Queued"},
  {"agent": "Enterprise Agent", "status": "Queued"}
]
```

The seven deterministic AI agents are always `Complete` once the pipeline
runs (they have no real precondition to wait on). `Supervisor Agent` is
`Complete` only when a real `SupervisorReview` exists — otherwise
`Pending`. `Learning Agent` and `Enterprise Agent` are `Queued` while
Supervisor is `Pending`: this specific inspection hasn't contributed a
learning signal yet, even though the confidence/analytics numbers those
agents report are already computed from *other*, already-reviewed
inspections in the tenant's history.

## §8 Clinical Readiness Certificate

`GET /api/cios/certificate/{inspection_id}` (JSON) and
`GET /api/cios/certificate/{inspection_id}/pdf` generate a printable
**Pre-Sterilization Clinical Readiness Certificate** — explicitly not a
sterilization certificate (`not_a_sterilization_certificate: true`, plus
an explicit disclaimer field), consistent with
`docs/architecture/pre-sterilization-boundary.md`. It includes the
inspection ID, instrument/manufacturer/model, inspection date, clinical
decision, coverage, baseline used, findings, the full clinical reasoning
chain, the recommendation, supervisor approval status, audit IDs (the
inspection ID and every linked Decision Ledger entry ID), governance
version snapshot, and a digital-signature **placeholder** — `signed:
false` with a note that e-signature capture is not yet implemented,
rather than fabricating a signature.

## §9 Enterprise Health Dashboard

`/cios-dashboard` (frontend) / `GET /api/cios/dashboard` (API) —
system health, inspection throughput, average inspection time, coverage
rate, supervisor agreement, AI confidence, model/knowledge-graph version,
digital twin health, most common findings/zones, and the Enterprise Risk
Index (a composite indicator, explicitly labeled as such, not a validated
clinical score). See `app/cios/dashboard.py` for exactly how each figure
is computed — every one is derived from real rows, `None` when there
isn't enough data rather than a fabricated default.

## Success criteria

LumenAI should no longer appear as a collection of AI features. Every
decision the system produces must be traceable (the timeline and trace),
explainable (the reasoning chain), auditable (the Decision Ledger and
event bus), repeatable (the same deterministic pipeline every time),
governed (versioned artifacts referenced on every decision), human-
supervised (Supervisor Agent never fabricates a decision), and
architecture-compliant (every module composes the Phase 15–22 services
that already exist — nothing here introduces a parallel, disconnected
system).
