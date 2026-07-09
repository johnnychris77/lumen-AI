# Clinical Reasoning Graph (Project Cortex, Section 1)

`app/services/knowledge_graph_service.py` (Phase 21, extended in v2.5).

## The chain

```
Instrument -> Manufacturer -> Instrument Family -> Anatomy -> Inspection Zone
  -> Finding -> Severity -> SPD Risk -> Clinical Significance
  -> Corrective Action -> Disposition
```

Not a separate graph database — a deterministic traversal built from
existing structured knowledge (`instrument_anatomy`, `cleaning_knowledge`,
`clinical_mentor.FINDING_EDUCATION`, `instrument_zones`) plus real database
rows (`Inspection`, `InspectionFinding`, `SupervisorReview`). Two chain
endpoints — **Corrective Action** and **Disposition** — were added in v2.5 to
`explain_inspection()`'s per-inspection chain, reusing the same persisted
`recommended_action`/`disposition` fields the rest of the platform already
shows, not a new derivation.

- `reasoning_chain(instrument_type, finding_type, manufacturer="", model="")` —
  generic, severity-unaware chain for the Knowledge Graph Explorer.
- `explain_inspection(db, inspection)` — the real, scored-inspection chain,
  now including `Corrective Action` and `Disposition` nodes.

## Every node is independently queryable (Section 1)

`GET /api/knowledge-graph/node/{node_type}?value=` —
`query_node(db, tenant_id, node_type, value)` normalizes any of the chain's
node names (`Instrument`, `Manufacturer`, `InstrumentFamily`, `AnatomyZone`,
`InspectionZone`, `Finding`, `Severity`, `SPDRisk`, `ClinicalSignificance`,
`CorrectiveAction`, `Disposition`) to the right existing lookup — most
delegate straight to `explore()`'s existing categories; `Severity`,
`SPDRisk`, `ClinicalSignificance`, `CorrectiveAction`, and `Disposition` are
new lookups added for this endpoint, reusing `FINDING_EDUCATION`,
`ZONE_INFO`/`get_cleaning_knowledge`, `SPD_RULE_LIBRARY`, and `_ACTION_TEXT`
respectively — never a second copy of that data.

## What this deliberately does not do

Does not introduce a second node/edge taxonomy alongside `explore()`'s
existing categories — `query_node()` is a thin router in front of the same
underlying data `explore()`/`reasoning_chain()`/`explain_inspection()`
already serve.
