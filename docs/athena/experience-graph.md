# Project Athena — Experience Graph & Institutional Memory Timeline

LumenAI OS v4.8, Sections 3 & 4.

## Experience Graph (Section 3)

`knowledge_graph_service.py`'s `explore()`/`reasoning_chain()` are real
but recomputed-on-read aggregations over `Inspection`/`SupervisorReview`/
static anatomy profiles — there is no persisted node/edge structure
anywhere in this codebase. The Experience Graph is a genuinely new,
persisted graph (`ExperienceGraphNode`/`ExperienceGraphEdge`), but the
Finding → Instrument → Anatomy → Recommendation segment of every chain is
populated by calling `knowledge_graph_service.reasoning_chain()` directly
— never re-derived.

The full chain, per the brief:

```
Person → Experience → Finding → Instrument → Anatomy → Recommendation → Outcome → Evidence → Organization
```

`athena_experience_graph_service.build_experience_chain` creates every
node/edge in one call:

1. **Person** / **Experience** — bare, human-supplied labels (the
   technician/supervisor and what they observed).
2. **Finding** / **Instrument** / **Anatomy** / **Recommendation** —
   populated from `reasoning_chain(instrument_type, finding_type, ...)`'s
   real output, with the node's `details_json` set to the matching chain
   step.
3. **Outcome** / **Evidence** / **Organization** — optional, human-
   supplied labels for the resolution and its supporting evidence.

```
POST /api/athena/experience-graph/chains
GET  /api/athena/experience-graph/person/{person}
GET  /api/athena/experience-graph/nodes/{node_id}/chain
GET  /api/athena/experience-graph/schema
```

Every chain is `human_review_required: true` — nothing here infers a
root cause; it structures what a person already reported.

## Institutional Memory Timeline (Section 4)

`orbit_timeline_service.py` exists but is a different domain entirely —
OR case logistics (Case Scheduled → ... → Procedure Complete). Athena's
timeline is a new composition over six real systems, joined by matching
`finding_type` values (a keyword-level association — there is no explicit
foreign-key chain linking a `ClinicalCase` to its eventual `QualityPolicy`
change anywhere in this codebase, so each step is honestly labeled with
its real source rather than a fabricated direct link):

```
Event (ClinicalCase) → Investigation (RootCauseAssignment) → CAPA (capa_lifecycle_service)
  → Education (CompetencyEvent) → Policy Change (QualityPolicy) → Outcome (CAPA lifecycle status)
  → Verification (CAPA verified_at/verified_by) → Future Similar Cases (similar_case_finder_service)
```

```
GET /api/athena/timeline?finding_type=blood&instrument_type=Kerrison%20Rongeur
```
