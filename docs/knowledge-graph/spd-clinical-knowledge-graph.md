# SPD Clinical Knowledge Graph

## Objective

Transform LumenAI from a system that only reports computer-vision output
into one that reasons using structured SPD clinical knowledge. Every AI
recommendation should be traceable through the same ontology chain that
`docs/architecture/lumenai-clinical-ontology.md` already establishes
platform-wide:

```
Instrument -> Manufacturer -> Instrument Family -> Model -> Anatomy ->
Inspection Zone -> Retention Risk -> Cleaning Method -> Typical
Contamination -> Typical Damage -> Clinical Meaning -> Recommended Action
-> Supervisor Validation -> Learning
```

## Implementation approach

This is **not** backed by a separate graph database (Neo4j, etc.). The
graph is represented as queryable nodes/edges computed on demand from:

- **Existing structured knowledge modules** — no duplication, only
  composition:
  - `app/services/instrument_anatomy.py` — Instrument → Family → Anatomy →
    Zone
  - `app/services/instrument_zones.py` — Zone → Retention Risk, per-zone
    `ZONE_INFO`
  - `app/services/cleaning_knowledge.py` (new, Phase 21) — Zone →
    Cleaning Method / Brush Type / Flushing / Ultrasonic / Visual /
    Manual Verification
  - `app/services/clinical_mentor.py`'s `FINDING_EDUCATION` — Finding →
    Clinical Meaning
  - `app/services/instrument_family_profiles.py` (new, Phase 21) —
    Instrument Family → typical contamination/damage/repair/priorities
  - `app/services/baseline_comparison_scoring_service.py`'s `_ACTION_TEXT`
    — Finding/Severity → Recommended Action
- **Real database rows** — `Inspection`, `SupervisorReview`,
  `PilotValidationCase`, `BaselineLibraryEntry`, `InstrumentKnowledge` —
  for anything that needs live data rather than static knowledge
  (Manufacturer, Model, Supervisor Decision, Training Dataset).

Every graph query is deterministic and grounded in real code/data. Nothing
in this module is a trained model or a black box.

## Node types

`Instrument`, `Manufacturer`, `InstrumentFamily`, `Model`, `AnatomyZone`,
`InspectionZone`, `Finding`, `Severity`, `SPDRisk`, `CleaningMethod`,
`BrushType`, `IFU`, `RepairRecommendation`, `ReplacementRecommendation`,
`SupervisorDecision`, `ClinicalRecommendation`, `TrainingDataset`.

`GET /api/knowledge-graph/schema` returns this list plus the relationship
types below and the ontology chain, programmatically — the taxonomy is
defined once in `app/services/knowledge_graph_service.py::graph_schema()`.

## Relationships

- `Instrument HAS Anatomy`
- `Anatomy HAS Zone`
- `Zone HAS Retention Risk`
- `Zone HAS Cleaning Method`
- `Zone HAS Common Findings`
- `Finding HAS Clinical Meaning`
- `Finding HAS Severity`
- `Finding REQUIRES Action`
- `Supervisor VALIDATES Finding`
- `Inspection CREATES Learning Signal`

Each relationship corresponds to a real function call in the codebase —
e.g. `Zone HAS Cleaning Method` is
`app/services/cleaning_knowledge.py::get_cleaning_knowledge(zone)`, and
`Supervisor VALIDATES Finding` is the existing
`POST /inspections/{id}/supervisor-review` → `PilotValidationCase` link
from Phase 18.

## Where this fits with prior phases

| Phase | Contributes |
|---|---|
| 15 | Instrument anatomy, zone taxonomy, instrument knowledge library |
| 14 | Per-finding clinical education (`FINDING_EDUCATION`) |
| 18 | Ground-truth labels (`PilotValidationCase`) — the "Learning" node |
| 19.5 | The platform-wide ontology this graph specializes |
| 20 | Readiness classification reused for repair-reason analytics |
| 21 | This document — the graph representation, reasoning engine, and explorer that tie the above together |

See `docs/knowledge-graph/reasoning-engine.md` for how the graph is
traversed to produce a recommendation, and
`docs/knowledge-graph/instrument-intelligence.md` for the ten instrument
family profiles.
