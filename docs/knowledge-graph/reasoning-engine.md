# Clinical Reasoning Engine

## What changes for the user

Before Phase 21, an AI output could read like:

> "I detected blood."

After Phase 21, the same detection is explained through the knowledge
graph:

> "I detected probable blood in the Kerrison jaw serrations. Serrations
> are a high-retention anatomy zone where blood and tissue commonly
> persist after inadequate manual cleaning. Based on SPD best practices
> and the instrument profile, recleaning, repeat inspection, and
> supervisor verification are recommended before the instrument proceeds
> to packaging."

(The exact zone named in the sentence depends on the instrument's real,
deterministic zone assignment — see the note on zone assignment below.)

## Two reasoning entry points

### 1. `reasoning_chain()` — generic, severity-unaware

`app/services/knowledge_graph_service.py::reasoning_chain(instrument_type,
finding_type, manufacturer="", model="")`, exposed at
`GET /api/knowledge-graph/reasoning-chain`. Used by the Knowledge Graph
Explorer to demonstrate "if this instrument shows this finding, here's how
LumenAI would reason about it" — without a real scored inspection behind
it. The recommended action is a generic categorization (contamination →
reprocess-class guidance; unrepairable structural → remove-from-service;
other structural → supervisor-review) since no real severity score exists
yet for a hypothetical query.

### 2. `explain_inspection()` — real, severity-aware

`app/services/knowledge_graph_service.py::explain_inspection(db, inspection)`,
exposed at `GET /api/knowledge-graph/explain/{inspection_id}`. Used for a
specific, already-scored inspection. This reads the inspection's *actual*
persisted `recommended_action` (the real scoring engine's deterministic
sentence — see
`docs/command-center/readiness-score-model.md`) rather than re-deriving a
generic one, so the explanation always matches what the instrument was
actually told to do.

## The reasoning chain, step by step

Both entry points walk the same ontology:

1. **Instrument** — the raw `instrument_type` string.
2. **Manufacturer** — if known.
3. **Instrument Family** — resolved via
   `app/services/instrument_anatomy.py::resolve_family`.
4. **Model** — if known.
5. **Anatomy Zone / Inspection Zone** — resolved via
   `app/services/instrument_zones.py::zone_fields`, the same deterministic
   zone-assignment engine used by Phase 18 pilot validation and the Phase
   20 command center. This is honestly labeled `pilot_zone_assignment` —
   instrument-type-derived, not pixel-level CV localization (see
   `docs/architecture/future-ai-roadmap.md` Stages 7–8, not yet started).
6. **Retention Risk** — the zone's risk level (`ZONE_INFO`).
7. **Cleaning Method** — `app/services/cleaning_knowledge.py`.
8. **Typical Contamination / Typical Damage** — the zone's
   `contamination_risks` / `condition_risks` from the anatomy profile.
9. **Clinical Meaning** — `FINDING_EDUCATION`'s `clinical_significance` /
   `why_it_matters` for the finding.
10. **Recommended Action** — mapped to one of the five frozen decision
    engine outcomes (`_ACTION_TEXT` in
    `baseline_comparison_scoring_service.py`; see
    `docs/architecture/lumenai-clinical-intelligence-architecture.md`
    Layer 7).
11. **Supervisor Validation** — always present, always required; routes to
    the Supervisor Review Queue (Phase 20 Module 6).
12. **Learning** — a confirmed or corrected supervisor review becomes a
    Phase 18 `PilotValidationCase` ground-truth label.

## Explainability Graph ("Why?")

The narrower "Why?" expansion (Phase 21 §6,
`GET /api/knowledge-graph/explain/{inspection_id}`) surfaces exactly five
nodes for a real inspection:

```
Finding -> Zone -> Clinical Significance -> SPD Rule -> Recommendation
```

This is the drill-down a supervisor clicks into from a specific inspection
record — narrower than the full reasoning chain, focused on "why did the
AI say this" rather than the full knowledge-graph traversal.

## Honesty constraints

- The narrative is built entirely from real function outputs
  (`zone_fields`, `FINDING_EDUCATION`, `_ACTION_TEXT`) — no hardcoded
  per-instrument sentences.
- `reasoning_chain()` never claims a severity-driven outcome it hasn't
  computed; it uses the same conservative outcome mapping documented
  above, and always recommends supervisor validation regardless.
- `explain_inspection()` never re-derives a recommendation that
  contradicts what was actually persisted on the inspection — it reads
  the real `recommended_action`, so the explanation and the actual
  disposition can never drift apart.
