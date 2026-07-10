# Clinical Anatomy Model — AI Reasoning Upgrade

The v2.0 "Definition of Done": LumenAI should no longer analyze a generic
image — it should reason through

```
Instrument -> Specific Anatomy -> Specific Zone -> Specific Clinical Risk
-> Specific SPD Recommendation
```

and every recommendation should reference the anatomy zone involved and
explain why that location is clinically important.

## Where this already lived, and what v2.0 adds

`app/services/knowledge_graph_service.reasoning_chain()` already implements
the explainability half of this chain (Finding → Anatomy Zone → Why this
zone matters → Typical contamination behavior → Clinical significance →
Recommended SPD action) for the Knowledge Graph Explorer. v2.0's job was to
make sure the **real scoring engine** — not just the explorer — reasons the
same way, and that "typical contamination behavior" is genuinely
zone-specific rather than one shared list.

### Zone-Based AI Context, threaded into the real reasoning engine

`baseline_comparison_scoring_service.analyze_inspection()` is the
deterministic-placeholder AI reasoning engine every uploaded inspection
runs through. As of v2.0, every entry in its `predicted_findings` list
carries:

```python
finding["instrument_family"] = resolve_family(instrument_type)
finding["expected_findings_for_zone"] = typical_findings_for_legacy_zone(finding["instrument_zone"])
```

on top of the fields it already carried (`instrument_zone`, `zone_risk`,
`zone_reason`, `recommended_manual_check`, `zone_confidence`,
`assignment_method`, `recommended_action`). A caller reading one predicted
finding can now answer, without a second lookup: which instrument family
this is, which anatomy zone the finding was assigned to, why that zone
matters, what's typically found there, and what to do about it — the full
chain, per finding.

### Why a Kerrison serration and a rigid-scope o-ring reason differently

Before v2.0, `finding["expected_findings_for_zone"]` would have been
identical for every zone (one shared generic list). Now:

- A **Kerrison jaw/serration** (`cutting_working_surface`) expects blood,
  bone, tissue, debris (contamination) and corrosion, pitting, dulling,
  nicked edge (condition).
- A **rigid-scope o-ring** (`lumen_scope`) expects blood, organic residue,
  debris (contamination) and discoloration, crack, damaged seal, pitting
  (condition) — cracks and seal damage are clinically meaningful for a
  scope seal in a way they simply aren't for a jaw.

See `zone-intelligence.md` for the full category table and
`instrument-anatomy-registry.md` for how this rolls into the rest of the
anatomy hierarchy.

## Learning Dataset v2

`app/services/learning_dataset_v2.py`, exposed at
`GET /api/anatomy/learning-dataset` (admin/spd_manager only). Joins real
stored rows — `SupervisorReview`, `Inspection`, `InspectionImageTag` — into
the exact row shape the v2.0 spec asks for: `instrument_family`,
`manufacturer`, `anatomy_zone`, `zone_risk` (via `zone_risk_for_name()`),
`inspection_view`, `finding`, `supervisor_correction` (agreement +
instrument-family/zone corrections), and `final_outcome`. No new table was
added — every row traces back to a real, already-persisted supervisor
review; this is an assembly view, not a second copy of the data.

## What was intentionally left unchanged

`analyze_inspection()`'s public signature (`instrument_type`,
`instrument_barcode`, `instrument_udi`, `keydot_id`, `declared_findings`,
`inspected_zones`, …) was not extended with new `manufacturer`/`model`
parameters — those are already available at the point of anatomy
resolution via `anatomy_profile(instrument_type, manufacturer, model)` and
the existing baseline-resolution priority (manufacturer → vendor →
hospital) that already threads manufacturer identity through scoring.
Forcing a parallel manufacturer/model parameter into the 1,368-line core
scoring function's signature — used by every inspection in the
platform — was judged a disproportionate blast radius for a v2.0 sprint
scoped as a reasoning upgrade, not a scoring-engine rewrite. Manufacturer/
model context remains available per-image via `InspectionImageTag` and via
the dedicated Anatomy Zone Engine / Dynamic Inspection Guidance endpoints.
