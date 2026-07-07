# Platform Governance

`app/cios/governance.py` — the seven versions every inspection references.

## The versions

| Version | Current value | Tracks |
|---|---|---|
| `architecture_version` | `19.5` | `docs/architecture/` — the frozen reference architecture (Phase 19.5) |
| `ontology_version` | `1.0` | `docs/architecture/lumenai-clinical-ontology.md`'s Instrument→...→Learning chain |
| `knowledge_graph_version` | `21.0` | `docs/knowledge-graph/` — node/relationship taxonomy (Phase 21) |
| `model_version` | `baseline-comparison-scoring-pilot-1` | The active scoring engine (`baseline_comparison_scoring_service.py`) |
| `dataset_version` | `pilot-v1` | The default Phase 18 ground-truth dataset version |
| `clinical_rule_version` | `1.0` | `app/cios/rule_registry.py` |
| `inspection_pipeline_version` | `22.0` | The Phase 22 multi-agent pipeline (`app/agents/registry.py`) |

`GET /api/cios/governance` returns this snapshot; `governance_snapshot()`
is the single function every other CIOS module calls to get it — no
module hardcodes a version string independently.

## Why these are code constants, not a database table

These versions describe **what the codebase currently is**, not
per-tenant configuration — every tenant on a given deployment runs the
same architecture, ontology, and pipeline version. Bumping a version here
is a deliberate code change (a PR that also updates the corresponding doc
or model registry entry), not a runtime toggle.

## Why every inspection/ledger entry snapshots, rather than references live

`ClinicalDecisionLedgerEntry` (see `docs/cios/clinical-decision-ledger.md`)
stores a **copy** of the governance versions active when it was created,
not a foreign key to "the current version." This is deliberate: if
`inspection_pipeline_version` is bumped to `23.0` next month, an entry
recorded under `22.0` must keep saying `22.0` — that's what actually ran
when the decision was made. An audit record that silently updated to
reflect today's version would be lying about its own history.

## Relationship to the Model Registry (Phase 17)

`model_version` here is a human-readable label for the *active* scoring
approach, distinct from `app/models/model_registry.py::ModelRegistryEntry`,
which tracks individual trained model *candidates* moving through
experimental → pilot → validated → deprecated. When a real trained model
is eventually promoted to `validated` and put into production (Phase 17's
model lifecycle), `governance.py::MODEL_VERSION` should be updated to
reference that registry entry's `model_version` — this is the deliberate
integration point flagged as a next step in
`docs/architecture/future-ai-roadmap.md`.

## Extending

Adding a new versioned artifact (e.g. a future `certificate_template_version`):
add the constant to `governance.py`, add it to `governance_snapshot()`,
and add a column to `ClinicalDecisionLedgerEntry` if it should be
snapshotted per-decision. The dashboard, certificate, and ledger all read
`governance_snapshot()` — no other code needs to change.
